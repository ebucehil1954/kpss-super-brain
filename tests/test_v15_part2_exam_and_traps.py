"""
Unit and Integration Tests for Document / Exam Intelligence V1.5 - Part 2
Tests all invariants across Phases 6 to 10:
- Question boundary and verbatim option preservation (A-E)
- Official answer key supremacy & LLM_DISAGREEMENT tracking
- Missing answer key handling as UNKNOWN
- Abstract question pattern taxonomy
- Distractor trap evidence linking
- Rebuildable exam statistics engine
- Exam & question provenance integrity
"""
import pytest
from brain.database import db_session, initialize_database
from ingestion.document_manager import DocumentManager
from ingestion.exam_parser import ExamParser
from cognition.question_solver import QuestionSolver
from cognition.pattern_classifier import PatternClassifier
from cognition.trap_detector import TrapDetector
from cognition.exam_statistics_engine import ExamStatisticsEngine


@pytest.fixture
def clean_exam_env(tmp_path):
    """Provides an isolated environment for exam testing."""
    initialize_database()
    doc_mgr = DocumentManager(storage_dir=str(tmp_path / "docs"))
    
    # Create sample parent document for foreign key integrity
    doc = doc_mgr.ingest_document(
        content_bytes=b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
        filename="kpss_2023_lisans_gygk.pdf",
        lesson="TARIH"
    )
    return doc_mgr, doc


SAMPLE_EXAM_PAGE_TEXT = """
1. Amasya Genelgesi'nde yer alan "Milletin bağımsızlığını yine milletin azim ve kararı kurtaracaktır." kararı ile aşağıdakilerden hangisi ilk kez vurgulanmıştır?
A) Manda ve himaye fikri
B) Milli egemenlik ilkesi
C) Temsil Heyeti'nin kurulması
D) Misak-ı Milli sınırları
E) Kuvayımilliye birliklerinin kaldırılması

2. Osmanlı Devleti'nde 17. yüzyılda çıkan Celali İsyanları ile ilgili olarak;
I. Anadolu'da can ve mal güvenliğinin bozulması,
II. Tarımsal üretimin düşmesi ve vergilerin toplanamaması,
III. Rejimi ve hanedanı değiştirmeye yönelik olmaları
yargılarından hangileri savunulamaz?
A) Yalnız I
B) Yalnız II
C) Yalnız III
D) I ve II
E) II ve III
"""


# ==========================================
# 1. TEST: QUESTION PRESERVES OPTIONS (Phase 6)
# ==========================================
def test_question_preserves_options(clean_exam_env):
    """Verify that all 5 options (A, B, C, D, E) are extracted with exact text and correct option keys."""
    _, doc = clean_exam_env
    parser = ExamParser()
    
    exam = parser.create_or_get_exam(
        exam_id="exam_kpss_2023_gygk",
        exam_name="2023 KPSS Lisans Genel Kültür",
        exam_code="KPSS_LISANS",
        year=2023,
        document_id=doc.document_id
    )
    
    questions = parser.parse_page_questions(
        page_text=SAMPLE_EXAM_PAGE_TEXT,
        exam_id=exam.exam_id,
        document_id=doc.document_id,
        page_number=1,
        default_lesson="TARIH"
    )
    
    assert len(questions) == 2
    
    q1 = questions[0]
    assert q1.question_number_in_exam == 1
    assert q1.extraction_status == "COMPLETE"
    assert len(q1.options) == 5
    
    option_map = {opt.option_key: opt.option_text for opt in q1.options}
    assert "Milli egemenlik ilkesi" in option_map["B"]
    assert "Manda ve himaye fikri" in option_map["A"]
    assert "Misak-ı Milli sınırları" in option_map["D"]


# ==========================================
# 2. TEST: ANSWER KEY DISAGREEMENT RECORDED (Rule 7 & Phase 7)
# ==========================================
def test_answer_key_disagreement_is_recorded(clean_exam_env):
    """When LLM answer contradicts official key, LLM_DISAGREEMENT is flagged and official key remains authoritative."""
    _, doc = clean_exam_env
    solver = QuestionSolver()
    
    # Bind official answer key: Question 1 -> 'B'
    solver.bind_official_answer_key(
        exam_id="exam_kpss_2023_gygk",
        answer_keys={1: "B", 2: "C"},
        source_document_id=doc.document_id
    )
    
    # 1. Matching case
    match_resolution = solver.reconcile_answer(
        official_key="B",
        llm_answer="B",
        llm_reasoning="Amasya Genelgesi maddesi doğrudan millet egemenliğini ifade eder."
    )
    assert match_resolution.final_answer == "B"
    assert match_resolution.disagreement_flag is False
    
    # 2. Disagreeing case (LLM wrongly suggests 'A')
    disagree_resolution = solver.reconcile_answer(
        official_key="B",
        llm_answer="A",
        llm_reasoning="Model manda ve himaye fikrinin tartışıldığını öne sürdü."
    )
    # Official key MUST win
    assert disagree_resolution.final_answer == "B"
    assert disagree_resolution.disagreement_flag is True
    assert disagree_resolution.disagreement_details["status"] == "LLM_DISAGREEMENT"
    assert disagree_resolution.disagreement_details["llm_suggested"] == "A"


# ==========================================
# 3. TEST: MISSING ANSWER KEY DEFAULTS TO UNKNOWN (Rule 4 & Phase 7)
# ==========================================
def test_missing_answer_key_defaults_to_unknown():
    """If an exam has no answer key attached, question status remains UNKNOWN without guessing."""
    solver = QuestionSolver()
    
    res = solver.reconcile_answer(
        official_key=None,
        llm_answer="C",
        llm_reasoning="LLM çözümü."
    )
    assert res.final_answer == "UNKNOWN"
    assert res.disagreement_flag is False
    
    res_str = solver.reconcile_answer(
        official_key="UNKNOWN",
        llm_answer="D"
    )
    assert res_str.final_answer == "UNKNOWN"


# ==========================================
# 4. TEST: QUESTION PATTERN IS ABSTRACT (Phase 8)
# ==========================================
def test_question_pattern_is_abstract(clean_exam_env):
    """Verify that classified patterns are reusable taxonomy archetypes and do not copy question body text."""
    _, doc = clean_exam_env
    parser = ExamParser()
    classifier = PatternClassifier()
    
    exam = parser.create_or_get_exam(
        exam_id="exam_pat_test",
        exam_name="Pattern Test Exam",
        exam_code="KPSS_LISANS",
        year=2023,
        document_id=doc.document_id
    )
    
    questions = parser.parse_page_questions(
        page_text=SAMPLE_EXAM_PAGE_TEXT,
        exam_id=exam.exam_id,
        document_id=doc.document_id,
        page_number=1
    )
    
    q2 = questions[1]  # Celali İsyanları (öncüllü ve savunulamaz)
    assert q2.is_negative is True
    assert len(q2.premises) == 3
    
    linked_patterns = classifier.link_question_to_patterns(
        question_id=q2.question_id,
        stem_text=q2.stem_text,
        premises=q2.premises,
        is_negative=q2.is_negative
    )
    
    assert "STATEMENT_ANALYSIS" in linked_patterns or "NEGATIVE_SELECTION" in linked_patterns
    
    # Check that database pattern record is an abstract structural model
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM v15_question_patterns WHERE pattern_code = 'NEGATIVE_SELECTION'")
        row = dict(cursor.fetchone())
        # Must not contain question specific text like 'Celali' or 'Amasya'
        assert "Celali" not in row["description"]
        assert "Amasya" not in row["description"]
        assert len(row["structural_indicators_json"]) > 0


# ==========================================
# 5. TEST: TRAP REQUIRES EVIDENCE (Phase 9)
# ==========================================
def test_trap_requires_evidence():
    """A trap entry must reference at least one concrete exam question distractor and a valid cognitive explanation."""
    detector = TrapDetector()
    
    # Valid registration
    trap = detector.register_trap(
        topic_id="MILLI_MUCADELE_HAZIRLIK",
        target_concept="AMASYA_GENELGESI",
        distractor_concept="ERZURUM_KONGRESI",
        trap_type="CONCEPT_SWAP",
        why_attractive="Öğrenciler milli egemenlik ilkesinin ilk kez Amasya'da mı Erzurum'da mı yer aldığını sıklıkla karıştırır.",
        supporting_question_id="q_exam_kpss_2023_gygk_1",
        confidence=0.90
    )
    assert trap.trap_id is not None
    assert "q_exam_kpss_2023_gygk_1" in trap.supporting_questions
    
    # Registration without supporting question must fail
    with pytest.raises(ValueError):
        detector.register_trap(
            topic_id="MILLI_MUCADELE_HAZIRLIK",
            target_concept="A",
            distractor_concept="B",
            trap_type="CONCEPT_SWAP",
            why_attractive="Açıklama metni.",
            supporting_question_id=""
        )


# ==========================================
# 6. TEST: STATISTICS ARE REBUILDABLE (Phase 10)
# ==========================================
def test_statistics_are_rebuildable(clean_exam_env):
    """Purging and recomputing v15_exam_statistics produces deterministic, exact aggregate numbers."""
    _, doc = clean_exam_env
    parser = ExamParser()
    classifier = PatternClassifier()
    stats_engine = ExamStatisticsEngine()
    
    exam = parser.create_or_get_exam(
        exam_id="exam_stats_test",
        exam_name="Stats Test Exam",
        exam_code="KPSS_LISANS",
        year=2023,
        document_id=doc.document_id
    )
    
    questions = parser.parse_page_questions(
        page_text=SAMPLE_EXAM_PAGE_TEXT,
        exam_id=exam.exam_id,
        document_id=doc.document_id,
        page_number=1,
        default_lesson="TARIH"
    )
    
    for q in questions:
        classifier.link_question_to_patterns(q.question_id, q.stem_text, q.premises, q.is_negative)
    
    # 1. First computation
    res1 = stats_engine.recompute_all_statistics()
    assert res1["status"] == "SUCCESS"
    assert res1["metrics_recomputed"] > 0
    
    summary1 = stats_engine.get_topic_frequency_summary()
    assert len(summary1) > 0
    
    # 2. Second computation (must produce identical count)
    res2 = stats_engine.recompute_all_statistics()
    summary2 = stats_engine.get_topic_frequency_summary()
    
    assert res1["metrics_recomputed"] == res2["metrics_recomputed"]
    assert summary1 == summary2


# ==========================================
# 7. TEST: EXAM PROVENANCE INTEGRITY (Rule 3 & Phase 6)
# ==========================================
def test_exam_provenance_integrity(clean_exam_env):
    """Every question strictly references its parent exam_id, document_id, and 1-indexed page_number."""
    _, doc = clean_exam_env
    parser = ExamParser()
    
    exam = parser.create_or_get_exam(
        exam_id="exam_prov_test",
        exam_name="Provenance Test Exam",
        exam_code="KPSS_LISANS",
        year=2024,
        document_id=doc.document_id
    )
    
    questions = parser.parse_page_questions(
        page_text=SAMPLE_EXAM_PAGE_TEXT,
        exam_id=exam.exam_id,
        document_id=doc.document_id,
        page_number=4,
        default_lesson="TARIH"
    )
    
    for q in questions:
        assert q.document_id == doc.document_id
        assert q.exam_id == exam.exam_id
        assert q.page_number == 4


# ==========================================
# 8. TEST: MULTI-PAGE EXAM DOCUMENT INGESTION (Phase 6 & Integration)
# ==========================================
def test_parse_exam_document_integration(clean_exam_env):
    """Verify that parse_exam_document extracts questions across all document pages and auto-links patterns."""
    _, doc = clean_exam_env
    parser = ExamParser()

    # Seed pages in v15_document_pages
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO v15_document_pages (page_id, document_id, page_number, raw_text, cleaned_text, char_count, is_ocr, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, '2026-01-01T00:00:00')
        """, (f"dp_{doc.document_id}_1", doc.document_id, 1, SAMPLE_EXAM_PAGE_TEXT, SAMPLE_EXAM_PAGE_TEXT, len(SAMPLE_EXAM_PAGE_TEXT)))

    questions = parser.parse_exam_document(
        document_id=doc.document_id,
        exam_id="exam_multipage_test",
        exam_name="2023 KPSS Test Book",
        exam_code="KPSS_LISANS",
        year=2023,
        auto_link_patterns=True
    )

    assert len(questions) == 2
    assert questions[0].question_number_in_exam == 1
    assert questions[1].question_number_in_exam == 2
    assert len(questions[0].options) == 5

    # Check pattern linkage in DB
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT p.pattern_code FROM v15_question_pattern_links l
        JOIN v15_question_patterns p ON l.pattern_id = p.pattern_id
        WHERE l.question_id = ?
        """, (questions[1].question_id,))
        linked = [r[0] for r in cursor.fetchall()]
        assert len(linked) > 0


# ==========================================
# 9. TEST: DISTRACTOR OPTION TRAP TAGGING & STAT SUMMARIES (Phase 9 & 10)
# ==========================================
def test_distractor_option_trap_tagging_and_stats(clean_exam_env):
    """Verify tagging specific question options as traps and retrieving rich statistical summaries."""
    _, doc = clean_exam_env
    parser = ExamParser()
    detector = TrapDetector()
    stats_engine = ExamStatisticsEngine()

    exam = parser.create_or_get_exam(
        exam_id="exam_trap_tag_test",
        exam_name="Trap Tag Exam",
        exam_code="KPSS_LISANS",
        year=2023,
        document_id=doc.document_id
    )

    questions = parser.parse_page_questions(
        page_text=SAMPLE_EXAM_PAGE_TEXT,
        exam_id=exam.exam_id,
        document_id=doc.document_id,
        page_number=1
    )

    q1 = questions[0]
    # Tag Option A as SIMILAR_TERM_CONFUSION
    tagged = detector.tag_option_as_trap(
        question_id=q1.question_id,
        option_key="A",
        trap_type="SIMILAR_TERM_CONFUSION"
    )
    assert tagged is True

    # Register trap model
    trap = detector.register_trap(
        topic_id="MILLI_MUCADELE",
        target_concept="EGEMENLIK",
        distractor_concept="MANDA_HIMAYE",
        trap_type="SIMILAR_TERM_CONFUSION",
        why_attractive="Manda ve himaye fikri sıklıkla egemenlik kavramıyla karıştırılır.",
        supporting_question_id=q1.question_id
    )
    assert trap.trap_id is not None

    all_traps = detector.list_all_traps()
    assert len(all_traps) > 0

    # Verify option table updated
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_trap, trap_type FROM v15_question_options WHERE question_id = ? AND option_key = 'A'", (q1.question_id,))
        row = cursor.fetchone()
        assert row["is_trap"] == 1
        assert row["trap_type"] == "SIMILAR_TERM_CONFUSION"

    # Recompute statistics and check summaries
    stats_res = stats_engine.recompute_all_statistics()
    assert stats_res["status"] == "SUCCESS"

    trap_summary = stats_engine.get_trap_frequency_summary()
    assert any(item["trap_type"] == "SIMILAR_TERM_CONFUSION" for item in trap_summary)

    year_summary = stats_engine.get_year_distribution_summary()
    assert len(year_summary) > 0

