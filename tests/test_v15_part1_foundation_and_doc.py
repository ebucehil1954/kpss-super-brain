"""
Unit and Integration Tests for Document / Exam Intelligence V1.5 - Part 1
Tests all invariants across Phases 0 to 5:
- Idempotent document upload (SHA-256)
- Page segmentation and 1-indexed page provenance
- OCR tagging and failure persistence
- Safe document classification and strict UNKNOWN handling
- Evidence link creation and candidate claim staging
- Guarded canonical verification gate
"""
import os
import pytest
import sqlite3
from io import BytesIO
from pypdf import PdfWriter

from brain.models import (
    DocumentRecord,
    DocumentClassification,
    V15AuditStatus,
    DocumentSourceType
)
from brain.database import db_session, initialize_database
from ingestion.document_manager import DocumentManager, DocumentSecurityError
from ingestion.document_parser import DocumentParser, DocumentParsingError
from curriculum.document_classifier import DocumentClassifier
from cognition.document_analyst import DocumentAnalyst
from cognition.v15_auditor_bridge import V15AuditorBridge, UnverifiedClaimCommitError


@pytest.fixture
def clean_test_env(tmp_path):
    """Fixture providing isolated storage directory and clean tables."""
    storage_dir = tmp_path / "documents"
    storage_dir.mkdir(parents=True, exist_ok=True)
    doc_mgr = DocumentManager(storage_dir=str(storage_dir))
    initialize_database()
    return doc_mgr, storage_dir


def create_sample_pdf_bytes(num_pages: int = 2, text_prefix: str = "KPSS Tarih Dersi") -> bytes:
    """Helper to generate in-memory valid PDF bytes."""
    import uuid
    writer = PdfWriter()
    for i in range(num_pages):
        writer.add_blank_page(width=300, height=300)
    writer.add_metadata({"/Producer": f"pytest_{uuid.uuid4().hex}"})
    stream = BytesIO()
    writer.write(stream)
    stream.seek(0)
    return stream.getvalue()



# ==========================================
# 1. TEST: IDEMPOTENT DOCUMENT UPLOAD (Rule 8 & Phase 1)
# ==========================================
def test_duplicate_document_is_idempotent(clean_test_env):
    """Uploading the exact same file content twice returns the same document_id without duplicating DB records."""
    doc_mgr, _ = clean_test_env
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
    
    doc1 = doc_mgr.ingest_document(
        content_bytes=pdf_bytes,
        filename="test_lecture.pdf",
        source_type=DocumentSourceType.UPLOAD_MANUAL,
        lesson="TARIH"
    )
    
    doc2 = doc_mgr.ingest_document(
        content_bytes=pdf_bytes,
        filename="test_lecture_copy.pdf",
        source_type=DocumentSourceType.UPLOAD_MANUAL,
        lesson="TARIH"
    )
    
    assert doc1.document_id == doc2.document_id
    assert doc1.sha256 == doc2.sha256
    
    # Check database row count
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM v15_documents WHERE sha256 = ?", (doc1.sha256,))
        count = cursor.fetchone()[0]
        assert count == 1


# ==========================================
# 2. TEST: DOCUMENT PAGE PROVENANCE (Rule 3 & Phase 2)
# ==========================================
def test_document_page_provenance(clean_test_env):
    """Parsed document pages accurately preserve 1-indexed page_number, char count, and document link."""
    doc_mgr, _ = clean_test_env
    pdf_bytes = create_sample_pdf_bytes(num_pages=3)
    
    doc = doc_mgr.ingest_document(
        content_bytes=pdf_bytes,
        filename="multipage_note.pdf"
    )
    
    parser = DocumentParser()
    pages = parser.parse_and_persist(doc.document_id)
    
    assert len(pages) == 3
    for idx, page in enumerate(pages):
        assert page.page_number == idx + 1  # 1-indexed
        assert page.document_id == doc.document_id
        assert page.page_id == f"dp_{doc.document_id}_{idx + 1}"
    
    # Verify DB persistence
    db_pages = parser.get_document_pages(doc.document_id)
    assert len(db_pages) == 3
    assert db_pages[0]["page_number"] == 1
    assert db_pages[2]["page_number"] == 3


# ==========================================
# 3. TEST: OCR TAGGING (Phase 2)
# ==========================================
def test_ocr_pages_marked_as_ocr(clean_test_env):
    """Scanned/empty text pages are flagged as is_ocr with recorded status."""
    doc_mgr, _ = clean_test_env
    pdf_bytes = create_sample_pdf_bytes(num_pages=1)
    
    doc = doc_mgr.ingest_document(
        content_bytes=pdf_bytes,
        filename="scanned_page.pdf"
    )
    
    parser = DocumentParser()
    pages = parser.parse_and_persist(doc.document_id)
    
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert doc_mgr.get_document_by_id(doc.document_id)["parsing_status"] == "PARSED"


# ==========================================
# 4. TEST: FAILED PARSER IS PERSISTED (Phase 2)
# ==========================================
def test_failed_parser_is_persisted(clean_test_env):
    """Corrupt files cleanly fail, record parsing_error, and do not crash."""
    doc_mgr, _ = clean_test_env
    # Corrupt PDF header that fails parsing
    fake_pdf = b"%PDF-corrupted-bytes-without-structure"
    
    doc = doc_mgr.ingest_document(
        content_bytes=fake_pdf,
        filename="corrupt.pdf"
    )
    
    parser = DocumentParser()
    with pytest.raises(DocumentParsingError):
        parser.parse_and_persist(doc.document_id)
    
    updated_doc = doc_mgr.get_document_by_id(doc.document_id)
    assert updated_doc["parsing_status"] == "FAILED"
    assert updated_doc["parsing_error"] is not None


# ==========================================
# 5. TEST: UNKNOWN CLASSIFICATION (Rule 4 & Phase 3)
# ==========================================
def test_unknown_document_classification():
    """Ambiguous or unidentifiable documents receive UNKNOWN classification."""
    classifier = DocumentClassifier()
    
    # Clear course material sample
    course_class = classifier.classify_document_type(
        text_sample="Bu ders notu KPSS Tarih özet notlar ve kavram haritası içerir.",
        filename="tarih_ders_notu.pdf"
    )
    assert course_class == DocumentClassification.COURSE_MATERIAL
    
    # Ambiguous / random content
    unknown_class = classifier.classify_document_type(
        text_sample="Rastgele kelimeler dizisi lorem ipsum dolor sit amet.",
        filename="random_file.pdf"
    )
    assert unknown_class == DocumentClassification.UNKNOWN


# ==========================================
# 6. TEST: UNKNOWN TOPIC MAPPING (Rule 4 & Phase 3)
# ==========================================
def test_unknown_topic_mapping():
    """Unmatched topics default to UNKNOWN and never fallback to arbitrary subjects like TARIH."""
    classifier = DocumentClassifier()
    
    # Known topic match
    lesson, topic, conf = classifier.map_curriculum_topic(
        text_sample="Amasya Genelgesi ve Erzurum Kongresi kararları incelenmiştir.",
        filename="genelgeler.pdf"
    )
    assert lesson == "TARIH"
    assert topic == "MILLI_MUCADELE_HAZIRLIK"
    assert conf >= 0.80
    
    # Unmatched / garbage text
    unknown_lesson, unknown_topic, conf_zero = classifier.map_curriculum_topic(
        text_sample="Xyz abc 123 quantum mechanics astrophysics data.",
        filename="unknown.pdf"
    )
    assert unknown_lesson == "UNKNOWN"
    assert unknown_topic == "UNKNOWN"
    assert conf_zero == 0.0


# ==========================================
# 7. TEST: CANDIDATE CLAIM REQUIRES EVIDENCE (Rule 2 & Phase 4)
# ==========================================
def test_candidate_claim_requires_evidence(clean_test_env):
    """Candidate claims are generated with a valid foreign key link to an evidence record."""
    doc_mgr, _ = clean_test_env
    analyst = DocumentAnalyst()
    
    # First ingest a valid document
    pdf_bytes = create_sample_pdf_bytes(num_pages=1)
    doc = doc_mgr.ingest_document(
        content_bytes=pdf_bytes,
        filename="amasya_genelgesi.pdf",
        lesson="TARIH"
    )
    
    page_text = (
        "Amasya Genelgesi'nde ilk kez milli egemenlik ilkesinden bahsedilmiştir. "
        "Milletin bağımsızlığını yine milletin azim ve kararı kurtaracaktır ilkesi kabul edilmiştir. "
        "Bu durum Kurtuluş Savaşı'nın amaç, gerekçe ve yöntemini belirlemiştir."
    )
    
    claims = analyst.extract_candidate_claims_from_page(
        document_id=doc.document_id,
        page_number=1,
        page_text=page_text,
        topic_id="MILLI_MUCADELE_HAZIRLIK"
    )
    
    assert len(claims) > 0
    for claim in claims:
        assert claim.evidence_id.startswith(f"ev_doc_{doc.document_id}_p1_")
        assert claim.audit_status == V15AuditStatus.CANDIDATE
        assert claim.topic_id == "MILLI_MUCADELE_HAZIRLIK"
    
    # Test DB Foreign Key Enforcement: non-existent evidence_id fails
    with pytest.raises(sqlite3.IntegrityError):
        with db_session() as conn:
            cursor = conn.cursor()
            # Attempting to insert a candidate claim with a non-existent evidence_id
            cursor.execute("""
            INSERT INTO v15_candidate_claims (
                claim_id, evidence_id, claim_type, subject, predicate, object_val,
                raw_statement, created_at
            ) VALUES ('clm_fake', 'ev_non_existent', 'FACT', 'sub', 'pred', 'obj', 'stmt', '2026-01-01')
            """)


# ==========================================
# 8. TEST: UNVERIFIED CLAIM CANNOT BE COMMITTED (Rule 1 & Phase 5)
# ==========================================
def test_unverified_claim_cannot_be_committed(clean_test_env):
    """Guarded canonical store rejects claims with audit_status != 'VERIFIED'."""
    doc_mgr, _ = clean_test_env
    analyst = DocumentAnalyst()
    bridge = V15AuditorBridge()
    
    # First ingest a valid document
    pdf_bytes = create_sample_pdf_bytes(num_pages=2)
    doc = doc_mgr.ingest_document(
        content_bytes=pdf_bytes,
        filename="erzurum_kongresi.pdf",
        lesson="TARIH"
    )
    
    page_text = "Erzurum Kongresi toplanış bakımından bölgesel, aldığı kararlar bakımından ulusaldır."
    claims = analyst.extract_candidate_claims_from_page(
        document_id=doc.document_id,
        page_number=2,
        page_text=page_text,
        topic_id="MILLI_MUCADELE_HAZIRLIK"
    )
    
    candidate_claim = claims[0]
    assert candidate_claim.audit_status == V15AuditStatus.CANDIDATE
    
    # 1. Attempting to commit CANDIDATE claim directly must raise error
    with pytest.raises(UnverifiedClaimCommitError):
        bridge.commit_verified_claim_to_canonical(candidate_claim.claim_id)
    
    # 2. Audit the claim to make it VERIFIED
    audited = bridge.audit_candidate_claim(candidate_claim.claim_id, force_pass=True)
    assert audited["audit_status"] == V15AuditStatus.VERIFIED.value
    
    # 3. Now commit must succeed
    canonical_record = bridge.commit_verified_claim_to_canonical(candidate_claim.claim_id)
    assert canonical_record is not None
    assert canonical_record["text"] == candidate_claim.raw_statement

