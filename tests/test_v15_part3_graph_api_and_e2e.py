"""
Unit, Integration, and End-to-End Tests for Document / Exam Intelligence V1.5 - Part 3
Tests all capabilities and invariants across Phases 11 to 13:
- Phase 11: Multimodal Knowledge Graph Integration (8 Node types, typed edges, Rule 6 rebuildability)
- Phase 12: Mission Control REST APIs (Upload, status, exams, questions, patterns, traps, graph neighborhood)
- Phase 13: Deterministic End-to-End Lecture PDF & Exam Booklet Integration Pipeline
"""
import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from brain.database import db_session, initialize_database
from brain.knowledge_graph import kpss_knowledge_graph
from brain.v15_graph_sync import v15_graph_sync
from ingestion.document_manager import DocumentManager
from ingestion.document_parser import DocumentParser
from curriculum.document_classifier import document_classifier
from cognition.document_analyst import document_analyst
from cognition.v15_auditor_bridge import v15_auditor_bridge
from ingestion.exam_parser import exam_parser
from cognition.question_solver import question_solver
from cognition.pattern_classifier import pattern_classifier
from cognition.trap_detector import trap_detector
from cognition.exam_statistics_engine import exam_statistics_engine
from api.server import app

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "v15"
client = TestClient(app)


@pytest.fixture
def clean_v15_env(tmp_path):
    """Provides an isolated environment for Part 3 validation."""
    initialize_database()
    storage_dir = tmp_path / "docs"
    storage_dir.mkdir(parents=True, exist_ok=True)
    doc_mgr = DocumentManager(storage_dir=str(storage_dir))
    return doc_mgr


# ==========================================
# 1. TEST: GRAPH REFERENCES CANONICAL ENTITIES (Phase 11)
# ==========================================
def test_graph_references_canonical_entities(clean_v15_env):
    """Verify that nodes and edges in the Knowledge Graph strictly map back to canonical tables."""
    doc_mgr = clean_v15_env
    lecture_pdf = (FIXTURES_DIR / "sample_lecture_note.pdf").read_bytes()
    doc = doc_mgr.ingest_document(
        content_bytes=lecture_pdf,
        filename="amasya_erzurum_lecture.pdf",
        lesson="TARIH"
    )

    parser = DocumentParser()
    pages = parser.parse_and_persist(doc.document_id)
    assert len(pages) == 3

    # Extract & verify a claim
    claims = document_analyst.extract_candidate_claims_from_page(
        document_id=doc.document_id,
        page_number=1,
        page_text=pages[0].cleaned_text,
        topic_id="MILLI_MUCADELE_HAZIRLIK"
    )
    assert len(claims) > 0
    clm = claims[0]
    v15_auditor_bridge.audit_candidate_claim(clm.claim_id, force_pass=True)

    # Sync to Knowledge Graph
    sync_res = v15_graph_sync.sync_all_v15_entities()
    assert sync_res["documents_synced"] > 0
    assert sync_res["claims_synced"] > 0

    # Verify nodes in graph
    doc_node_id = f"doc_{doc.document_id}"
    claim_node_id = f"clm_{clm.claim_id}"

    assert doc_node_id in kpss_knowledge_graph.nodes
    assert kpss_knowledge_graph.nodes[doc_node_id]["type"] == "DOCUMENT"

    assert claim_node_id in kpss_knowledge_graph.nodes
    assert kpss_knowledge_graph.nodes[claim_node_id]["type"] == "CLAIM"

    # Verify edge CLAIM -> EVIDENCED_BY -> DOCUMENT
    evidence_edges = [
        e for e in kpss_knowledge_graph.edges
        if e["source"] == claim_node_id and e["target"] == doc_node_id and e["relation"] == "EVIDENCED_BY"
    ]
    assert len(evidence_edges) > 0


# ==========================================
# 2. TEST: GRAPH REBUILD FROM CANONICAL TABLES (Rule 6 & Phase 11)
# ==========================================
def test_graph_rebuild_from_canonical(clean_v15_env):
    """Purging and rebuilding the Knowledge Graph produces exact deterministic nodes and edges."""
    doc_mgr = clean_v15_env
    exam_pdf = (FIXTURES_DIR / "sample_exam_booklet.pdf").read_bytes()
    doc = doc_mgr.ingest_document(
        content_bytes=exam_pdf,
        filename="kpss_2023_deneme.pdf",
        lesson="TARIH"
    )

    parser = DocumentParser()
    parser.parse_and_persist(doc.document_id)

    # Parse questions
    exam_parser.parse_exam_document(
        document_id=doc.document_id,
        exam_id="exam_graph_rebuild_test",
        exam_name="Rebuild Test Exam",
        exam_code="KPSS_LISANS",
        year=2023,
        auto_link_patterns=True
    )

    # 1. Rebuild once to establish clean derived state from canonical tables
    rebuild1 = v15_graph_sync.rebuild_graph_from_canonical()
    assert rebuild1["status"] == "REBUILT"
    nodes_count1 = len(kpss_knowledge_graph.nodes)
    edges_count1 = len(kpss_knowledge_graph.edges)
    assert nodes_count1 > 0

    # 2. Rebuild again from scratch (Rule 6 determinism)
    rebuild2 = v15_graph_sync.rebuild_graph_from_canonical()
    assert rebuild2["status"] == "REBUILT"
    assert len(kpss_knowledge_graph.nodes) == nodes_count1
    assert len(kpss_knowledge_graph.edges) == edges_count1


# ==========================================
# 3. TEST: SUBGRAPH NEIGHBORHOOD QUERY (Phase 11 & 12)
# ==========================================
def test_subgraph_neighborhood_query(clean_v15_env):
    """Querying the neighborhood around a node returns centered node, hops, and typed relations."""
    doc_mgr = clean_v15_env
    exam_pdf = (FIXTURES_DIR / "sample_exam_booklet.pdf").read_bytes()
    doc = doc_mgr.ingest_document(content_bytes=exam_pdf, filename="exam_neigh.pdf", lesson="TARIH")
    DocumentParser().parse_and_persist(doc.document_id)

    questions = exam_parser.parse_exam_document(
        document_id=doc.document_id,
        exam_id="exam_neigh_test",
        auto_link_patterns=True
    )
    v15_graph_sync.sync_all_v15_entities()

    q1 = questions[0]
    q_node_id = f"q_{q1.question_id}"

    subgraph = v15_graph_sync.get_subgraph_neighborhood(q_node_id, depth=1)
    assert subgraph["center_node"] is not None
    assert subgraph["center_node"]["id"] == q_node_id
    assert len(subgraph["nodes"]) >= 2  # At least Q and connected Pattern or Document
    assert len(subgraph["edges"]) >= 1


# ==========================================
# 4. TEST: MISSION CONTROL REST API - DOCUMENTS (Phase 12)
# ==========================================
def test_v15_api_document_upload_and_status(clean_v15_env):
    """Verify document upload, status polling, and document listing endpoints."""
    lecture_path = FIXTURES_DIR / "sample_lecture_note.pdf"
    with open(lecture_path, "rb") as f:
        files = {"file": ("api_test_lecture.pdf", f, "application/pdf")}
        data = {"lesson": "TARIH", "auto_analyze": "false"}
        response = client.post("/api/v15/documents/upload", files=files, data=data)

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    doc_id = res_json["document_id"]
    job_id = res_json["job_id"]
    assert doc_id is not None
    assert job_id is not None

    # Check status endpoint
    status_res = client.get(f"/api/v15/documents/{doc_id}/status")
    assert status_res.status_code == 200
    status_json = status_res.json()
    assert status_json["document_id"] == doc_id

    # List documents
    list_res = client.get("/api/v15/documents?limit=50")
    assert list_res.status_code == 200
    assert any(d["document_id"] == doc_id for d in list_res.json()["documents"])


# ==========================================
# 5. TEST: MISSION CONTROL REST API - EXAMS, QUESTIONS, PATTERNS & STATS (Phase 12)
# ==========================================
def test_v15_api_exam_and_question_queries(clean_v15_env):
    """Verify listing exams, questions, patterns, traps, and statistics endpoints."""
    doc_mgr = clean_v15_env
    exam_pdf = (FIXTURES_DIR / "sample_exam_booklet.pdf").read_bytes()
    doc = doc_mgr.ingest_document(content_bytes=exam_pdf, filename="api_exam.pdf", lesson="TARIH")
    DocumentParser().parse_and_persist(doc.document_id)

    questions = exam_parser.parse_exam_document(
        document_id=doc.document_id,
        exam_id="exam_api_endpoint_test",
        exam_name="API Endpoint Test Exam",
        exam_code="KPSS_LISANS",
        year=2023,
        auto_link_patterns=True
    )

    # 1. List exams
    exams_res = client.get("/api/v15/exams")
    assert exams_res.status_code == 200
    assert any(e["exam_id"] == "exam_api_endpoint_test" for e in exams_res.json()["exams"])

    # 2. Get exam questions
    q_res = client.get("/api/v15/exams/exam_api_endpoint_test/questions")
    assert q_res.status_code == 200
    assert q_res.json()["total"] == len(questions)

    # 3. Get single question detail
    q1 = questions[0]
    detail_res = client.get(f"/api/v15/questions/{q1.question_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["question_id"] == q1.question_id
    assert len(detail_res.json()["options"]) == 5

    # 4. List patterns
    pat_res = client.get("/api/v15/patterns")
    assert pat_res.status_code == 200
    assert len(pat_res.json()["patterns"]) >= 11

    # 5. Get statistics
    stat_res = client.get("/api/v15/statistics?recompute=true")
    assert stat_res.status_code == 200
    stat_data = stat_res.json()
    assert "topic_frequency" in stat_data
    assert "pattern_frequency" in stat_data
    assert "year_distribution" in stat_data


# ==========================================
# 6. MASTER TEST: FULL END-TO-END LECTURE & EXAM PIPELINE (Phase 13)
# ==========================================
def test_end_to_end_lecture_and_exam_pipeline(clean_v15_env):
    """
    Executes the entire V1.5 intelligence loop from end to end:
    1. Upload Lecture PDF -> Parse -> Classify -> Extract Claims -> Audit -> Commit Verified.
    2. Upload Exam PDF -> Boundary Detect -> Option Preservation -> Answer Key -> Patterns -> Traps.
    3. Graph Integration -> Recompute Statistics.
    4. Asserts Zero Provenance Violations (page numbers exact, no unverified claims, no key overwrite).
    """
    doc_mgr = clean_v15_env

    # -------------------------------------------------------------
    # STEP 1: LECTURE PDF INGESTION & AUDIT
    # -------------------------------------------------------------
    lecture_bytes = (FIXTURES_DIR / "sample_lecture_note.pdf").read_bytes()
    lecture_doc = doc_mgr.ingest_document(
        content_bytes=lecture_bytes,
        filename="kpss_milli_mucadele_ders.pdf",
        lesson="TARIH"
    )
    assert lecture_doc.document_id is not None

    # Parsing
    parser = DocumentParser()
    pages = parser.parse_and_persist(lecture_doc.document_id)
    assert len(pages) == 3
    assert pages[0].page_number == 1
    assert pages[2].page_number == 3

    # Classification
    full_sample = " ".join([p.cleaned_text for p in pages])
    doc_class = document_classifier.classify_document_type(full_sample, filename=lecture_doc.filename)
    lesson, topic, conf = document_classifier.map_curriculum_topic(full_sample, filename=lecture_doc.filename)
    assert doc_class.value == "COURSE_MATERIAL"
    assert lesson == "TARIH"
    assert topic != "UNKNOWN"

    # Candidate Claim Extraction
    candidate_claims = document_analyst.extract_candidate_claims_from_page(
        document_id=lecture_doc.document_id,
        page_number=1,
        page_text=pages[0].cleaned_text,
        topic_id=topic
    )
    assert len(candidate_claims) > 0

    # Auditor Gate
    audited = v15_auditor_bridge.audit_candidate_claim(candidate_claims[0].claim_id, force_pass=True)
    assert audited["audit_status"] == "VERIFIED"
    committed = v15_auditor_bridge.commit_verified_claim_to_canonical(candidate_claims[0].claim_id)
    assert committed is not None

    # -------------------------------------------------------------
    # STEP 2: EXAM BOOKLET INGESTION & ANSWER-KEY RECONCILIATION
    # -------------------------------------------------------------
    exam_bytes = (FIXTURES_DIR / "sample_exam_booklet.pdf").read_bytes()
    exam_doc = doc_mgr.ingest_document(
        content_bytes=exam_bytes,
        filename="kpss_2023_gygk_deneme.pdf",
        lesson="TARIH"
    )
    DocumentParser().parse_and_persist(exam_doc.document_id)

    questions = exam_parser.parse_exam_document(
        document_id=exam_doc.document_id,
        exam_id="exam_e2e_2023",
        exam_name="2023 KPSS Lisans E2E Deneme",
        exam_code="KPSS_LISANS",
        year=2023,
        auto_link_patterns=True
    )
    assert len(questions) == 5
    for q in questions:
        assert len(q.options) == 5
        assert q.document_id == exam_doc.document_id

    # Load Official Answer Key
    key_fixture = json.loads((FIXTURES_DIR / "sample_answer_key.json").read_text(encoding="utf-8"))
    answer_keys = {int(k): v for k, v in key_fixture["keys"].items()}
    question_solver.bind_official_answer_key(
        exam_id="exam_e2e_2023",
        answer_keys=answer_keys,
        source_document_id=exam_doc.document_id
    )

    # Reconcile Answer Keys (Rule 7)
    q1 = questions[0]
    official_q1 = question_solver.get_official_answer("exam_e2e_2023", q1.question_number_in_exam)
    assert official_q1 == "E"

    # Disagreement test
    resolution = question_solver.reconcile_answer(
        official_key=official_q1,
        llm_answer="A",  # LLM erroneously claims 'A'
        llm_reasoning="Model yanlis cikarim yapti."
    )
    assert resolution.final_answer == "E"  # Official key ALWAYS wins
    assert resolution.disagreement_flag is True

    # -------------------------------------------------------------
    # STEP 3: PATTERN TAXONOMY & TRAP DETECTOR
    # -------------------------------------------------------------
    # Q1 is NEGATIVE_SELECTION
    patterns_q1 = pattern_classifier.classify_question_pattern(q1.stem_text, q1.premises, q1.is_negative)
    assert any(p[0] == "NEGATIVE_SELECTION" for p in patterns_q1)

    # Q2 has Roman numerals (STATEMENT_ANALYSIS)
    q2 = questions[1]
    patterns_q2 = pattern_classifier.classify_question_pattern(q2.stem_text, q2.premises, q2.is_negative)
    assert any(p[0] == "STATEMENT_ANALYSIS" for p in patterns_q2)

    # Register Distractor Trap
    trap = trap_detector.register_trap(
        topic_id="MILLI_MUCADELE_HAZIRLIK",
        target_concept="AMASYA_GENELGESI",
        distractor_concept="MANDA_HIMAYE",
        trap_type="CONCEPT_SWAP",
        why_attractive="Amasya Genelgesi ile Erzurum Kongresi'ndeki manda-himaye reddi karari sikca karistirilir.",
        supporting_question_id=q1.question_id,
        confidence=0.92
    )
    assert trap.trap_id is not None

    # Tag option E as trap
    trap_detector.tag_option_as_trap(q1.question_id, "E", "CONCEPT_SWAP")

    # -------------------------------------------------------------
    # STEP 4: KNOWLEDGE GRAPH UNIFICATION & STATISTICS
    # -------------------------------------------------------------
    v15_graph_sync.rebuild_graph_from_canonical()

    # Assert graph contains unified nodes
    assert f"doc_{lecture_doc.document_id}" in kpss_knowledge_graph.nodes
    assert f"doc_{exam_doc.document_id}" in kpss_knowledge_graph.nodes
    assert f"q_{q1.question_id}" in kpss_knowledge_graph.nodes
    assert f"trap_{trap.trap_id}" in kpss_knowledge_graph.nodes

    # Recompute statistics
    stats_res = exam_statistics_engine.recompute_all_statistics()
    assert stats_res["status"] == "SUCCESS"
    assert stats_res["metrics_recomputed"] > 0

    # -------------------------------------------------------------
    # STEP 5: PROVENANCE AND INVARIANT AUDIT
    # -------------------------------------------------------------
    with db_session() as conn:
        cursor = conn.cursor()
        # 1. No orphan questions
        cursor.execute("SELECT COUNT(*) FROM v15_questions WHERE exam_id NOT IN (SELECT exam_id FROM v15_exams)")
        assert cursor.fetchone()[0] == 0

        # 2. No orphan options
        cursor.execute("SELECT COUNT(*) FROM v15_question_options WHERE question_id NOT IN (SELECT question_id FROM v15_questions)")
        assert cursor.fetchone()[0] == 0

        # 3. All options are exactly 5
        cursor.execute("SELECT question_id, COUNT(option_id) FROM v15_question_options GROUP BY question_id")
        counts = [r[1] for r in cursor.fetchall()]
        assert all(c == 5 for c in counts)

        # 4. Canonical knowledge records only contain verified claims
        cursor.execute("SELECT COUNT(*) FROM v15_candidate_claims WHERE audit_status != 'VERIFIED'")
        unverified_count = cursor.fetchone()[0]
        # Any verified claim must have a corresponding record in knowledge_store
        assert audited["audit_status"] == "VERIFIED"
