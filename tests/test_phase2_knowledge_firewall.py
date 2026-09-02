"""
KPSS Super-Brain: Phase 2 — Knowledge Firewall Test Suite
Master Refactor Plan Phase 2 Kapsamı:
1. test_pending_claim_not_committed: PENDING durumundaki iddia asla kanonik bilgiye giremez.
2. test_unverified_claim_not_committed: UNVERIFIED durumundaki iddia asla kanonik bilgiye giremez.
3. test_verified_claim_committed: Yalnızca VERIFIED / SUPPORTED iddialar ambarına mühürlenir.
4. test_rejected_claim_not_committed: REJECTED iddia kanonik bilgi yapılamaz.
5. test_disputed_claim_not_committed: DISPUTED iddia kanonik bilgi yapılamaz.
6. test_commit_requires_provenance: Provenance veya kanıt taşımayan iddia doğrudan reddedilir.
"""
import pytest
from brain.models import AtomicClaim, EvidenceRef, ClaimType, SourceType, VerificationStatus
from brain.knowledge_store import knowledge_store
from brain.database import db_session

def test_pending_claim_not_committed():
    """Phase 2: PENDING iddia firewall tarafından engellenmelidir."""
    claim = {
        "text": "TBMM seçimleri 4 yılda bir yapılır.",
        "lesson": "VATANDASLIK",
        "topic": "Yasama",
        "verification_status": "PENDING",
        "provenance_hash": "prov_hash_pending_123",
        "evidence_refs": [{"source_id": "src_1"}]
    }
    res = knowledge_store.commit_verified_claim(claim)
    assert res is None, "PENDING iddia kanonik belleğe kaydedilmemeli!"

def test_unverified_claim_not_committed():
    """Phase 2: UNVERIFIED iddia firewall tarafından engellenmelidir."""
    claim = {
        "text": "İki meclisli sistem 1982 Anayasası'nda da vardır.",
        "lesson": "VATANDASLIK",
        "topic": "Anayasa Tarihi",
        "verification_status": "UNVERIFIED",
        "provenance_hash": "prov_hash_unver_123",
        "evidence_refs": [{"source_id": "src_2"}]
    }
    res = knowledge_store.commit_verified_claim(claim)
    assert res is None, "UNVERIFIED iddia kanonik belleğe kaydedilmemeli!"

def test_rejected_claim_not_committed():
    """Phase 2: REJECTED iddia asla kanonik bilgi olamaz."""
    claim = {
        "text": "Kaime Fatih Sultan Mehmet döneminde basılmıştır.",
        "lesson": "TARIH",
        "topic": "Osmanlı Kültür Medeniyet",
        "verification_status": "REJECTED",
        "provenance_hash": "prov_hash_rej_123",
        "evidence_refs": [{"source_id": "src_3"}]
    }
    res = knowledge_store.commit_verified_claim(claim)
    assert res is None, "REJECTED iddia kanonik belleğe kaydedilmemeli!"

def test_disputed_claim_not_committed():
    """Phase 2: DISPUTED iddia asla kanonik bilgi olamaz."""
    claim = {
        "text": "Toplantı yeter sayısı 151'dir.",
        "lesson": "VATANDASLIK",
        "topic": "TBMM",
        "verification_status": "DISPUTED",
        "provenance_hash": "prov_hash_disp_123",
        "evidence_refs": [{"source_id": "src_4"}]
    }
    res = knowledge_store.commit_verified_claim(claim)
    assert res is None, "DISPUTED iddia kanonik belleğe kaydedilmemeli!"

def test_commit_requires_provenance():
    """Phase 2: Provenance veya kanıt referansı bulunmayan iddia reddedilir."""
    claim_no_prov = {
        "text": "TBMM 600 milletvekilinden oluşur.",
        "lesson": "VATANDASLIK",
        "topic": "TBMM",
        "verification_status": "VERIFIED",
        # Hiçbir provenance_hash veya evidence_refs yok!
    }
    res = knowledge_store.commit_verified_claim(claim_no_prov)
    assert res is None, "Provenance taşımayan iddia kabul edilmemelidir!"

def test_verified_claim_committed():
    """Phase 2: Yalnızca doğrulanmış ve kanıtlı iddia kanonik belleğe kabul edilir."""
    evidence = EvidenceRef(
        source_id="src_mevzuat_82",
        source_type=SourceType.OFFICIAL_LEGISLATION,
        snippet="Madde 75: Türkiye Büyük Millet Meclisi altıyüz milletvekilinden kurulur.",
        speaker_or_author="1982 T.C. Anayasası"
    )
    claim = AtomicClaim(
        claim_id="claim_firewall_pass_001",
        text="1982 Anayasası Madde 75 uyarınca TBMM 600 milletvekilinden oluşur.",
        lesson="VATANDASLIK",
        topic="Yasama Organı",
        claim_type=ClaimType.FACT,
        evidence_refs=[evidence],
        confidence=0.99,
        verification_status=VerificationStatus.VERIFIED
    )

    res = knowledge_store.commit_verified_claim(claim)
    assert res is not None, "VERIFIED ve provenance sahibi iddia ambarına kaydedilmeliydi!"
    assert res.get("record_id") is not None

    # Bilgi ambarında doğrulanmış kaydın varlığını sorgula
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_records WHERE record_id = ?", (res["record_id"],))
        row = cursor.fetchone()
        assert row is not None
        assert "verified_claim" in row["tags_json"]
