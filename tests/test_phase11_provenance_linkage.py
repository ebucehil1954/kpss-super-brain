"""
KPSS Super-Brain: Phase 11 — Uçtan Uca Kanıt Zinciri Testleri (Provenance Linkage)
Master Refactor Plan Phase 11 Kapsamı:
1. test_full_provenance_chain_succeeds: Eksiksiz kanıt zinciri başarıyla doğrulanır ve kaydedilir.
2. test_missing_segment_fails_provenance: Zaman damgası/segment eksik olan video kanıtı reddedilir.
3. test_missing_source_fails_provenance: Kök source_id eksik olan kanıt zinciri kopuk sayılır.
4. test_unlinked_claim_cannot_be_verified: Hiçbir kanıtı olmayan iddia kanonik belleğe kabul edilmez.
"""
import pytest
from brain.models import AtomicClaim, EvidenceRef, SourceType, VerificationStatus
from brain.provenance import provenance_validator
from brain.knowledge_store import knowledge_store

def test_full_provenance_chain_succeeds():
    """Phase 11: Tam ve eksiksiz kanıt zincirine sahip iddia başarıyla doğrulanır."""
    ev = EvidenceRef(
        source_id="vid_tbmm_ders_01",
        source_type=SourceType.YOUTUBE_TRANSCRIPT,
        video_id="vid_tbmm_ders_01",
        segment_id="seg_0042",
        timestamp_str="12:45-13:10",
        snippet="TBMM seçimleri beş yılda bir Cumhurbaşkanı seçimi ile birlikte yapılır."
    )
    claim = AtomicClaim(
        claim_id="clm_prov_full",
        text="TBMM ve Cumhurbaşkanlığı seçimleri 5 yılda bir aynı gün yapılır.",
        lesson="VATANDASLIK",
        topic="Seçim İlkeleri",
        evidence_refs=[ev],
        verification_status=VerificationStatus.VERIFIED
    )

    is_valid, reason = provenance_validator.validate_provenance_chain(claim)
    assert is_valid is True
    assert reason == "PROVENANCE_OK"

    # Kanonik belleğe de başarıyla kabul edilmelidir
    res = knowledge_store.commit_verified_claim(claim, verification_status="VERIFIED")
    assert res is not None
    assert res["action"] in ("created", "reinforced")

def test_missing_segment_fails_provenance():
    """Phase 11: Video kaynağında zaman damgası / segment_id yoksa kanıt zinciri kopuk sayılır."""
    ev_no_seg = EvidenceRef(
        source_id="vid_tbmm_ders_01",
        source_type=SourceType.YOUTUBE_TRANSCRIPT,
        video_id="vid_tbmm_ders_01",
        segment_id=None,
        timestamp_str=None, # Segment yok!
        snippet="TBMM seçimleri beş yılda bir yapılır."
    )
    claim = AtomicClaim(
        claim_id="clm_prov_no_seg",
        text="TBMM seçimleri beş yılda bir yapılır.",
        lesson="VATANDASLIK",
        topic="Seçim İlkeleri",
        evidence_refs=[ev_no_seg]
    )

    is_valid, reason = provenance_validator.validate_provenance_chain(claim)
    assert is_valid is False
    assert "PROVENANCE_BROKEN" in reason
    assert "segment_id eksik" in reason

def test_missing_source_fails_provenance():
    """Phase 11: Kök source_id eksik veya boş olan referans kanıt zincirini bozar."""
    ev_no_src = EvidenceRef(
        source_id="", # Boş source_id!
        source_type=SourceType.OFFICIAL_LEGISLATION,
        snippet="1982 Anayasası Madde 77"
    )
    claim = AtomicClaim(
        claim_id="clm_prov_no_src",
        text="Seçim dönemi 5 yıldır.",
        lesson="VATANDASLIK",
        topic="Seçim İlkeleri",
        evidence_refs=[ev_no_src]
    )

    is_valid, reason = provenance_validator.validate_provenance_chain(claim)
    assert is_valid is False
    assert "source_id eksik" in reason

def test_unlinked_claim_cannot_be_verified():
    """Phase 11: Hiçbir kanıt referansı bulunmayan başıboş iddia asla kanonik belleğe kaydedilemez."""
    claim_unlinked = AtomicClaim(
        claim_id="clm_unlinked",
        text="Kanıtsız iddia metni.",
        lesson="VATANDASLIK",
        topic="Genel",
        evidence_refs=[] # Sıfır kanıt
    )

    is_valid, reason = provenance_validator.validate_provenance_chain(claim_unlinked)
    assert is_valid is False
    assert "kanıt referansı (EvidenceRef) bulunamadı" in reason

    # Doğrudan commit denendiğinde de None döner
    res = knowledge_store.commit_verified_claim(claim_unlinked, verification_status="VERIFIED")
    assert res is None
