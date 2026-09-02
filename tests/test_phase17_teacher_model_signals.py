"""
KPSS Super-Brain: Phase 17 — Öğretmen Pedagojik ve Retorik Sinyallerinin Ayrıştırılması Testleri
Master Refactor Plan Phase 17 Kapsamı:
1. test_mnemonic_is_not_stored_as_canonical_fact: Mnemonik ezber şifreleri FACT olarak değil MNEMONIC olarak saklanır.
2. test_exam_trap_is_typed_correctly: Sınav çeldiricisi/tuzakları TRAP türünde saklanır.
3. test_teacher_tone_does_not_alter_factual_payload: Hoca retoriği ve hitapları olgusal çekirdeği kirletemez.
"""
import pytest
from brain.models import AtomicClaim, EvidenceRef, ClaimType, SourceType, VerificationStatus
from brain.knowledge_store import knowledge_store
from cognition.teacher_learner import teacher_learner

def test_mnemonic_is_not_stored_as_canonical_fact():
    """Phase 17: Mnemonik veya akrostiş asla objektif kanun maddesi (FACT) olarak saklanamaz."""
    ev = EvidenceRef(
        source_id="src_hoca_mnem_01",
        source_type=SourceType.YOUTUBE_TRANSCRIPT,
        video_id="vid_mnem_01",
        segment_id="seg_01",
        timestamp_str="05:10",
        snippet="Hocanızdan şifre: HAVUÇ formülü ile ilk anayasa ilkelerini aklında tut."
    )
    mnemonic_claim = AtomicClaim(
        claim_id="clm_mnem_test",
        text="Şifremiz HAVUÇ: Hürriyet, Adalet, Vatan, Ulus, Çoğulculuk.",
        lesson="VATANDASLIK",
        topic="Anayasa Temel İlkeler",
        claim_type=ClaimType.MNEMONIC,
        evidence_refs=[ev],
        verification_status=VerificationStatus.VERIFIED
    )

    res = knowledge_store.commit_verified_claim(mnemonic_claim, verification_status="VERIFIED")
    assert res is not None

    # Doğrudan veritabanındaki record_type kontrolü
    results = knowledge_store.search("HAVUÇ")
    assert len(results) > 0
    assert results[0]["record_type"] == "MNEMONIC", "Mnemonik şifreler FACT değil MNEMONIC olarak depolanmalıdır!"

def test_exam_trap_is_typed_correctly():
    """Phase 17: Soru tuzakları ve çeldirici uyarıları TRAP olarak saklanır."""
    ev = EvidenceRef(
        source_id="src_trap_01",
        source_type=SourceType.YOUTUBE_TRANSCRIPT,
        video_id="vid_trap_01",
        segment_id="seg_02",
        timestamp_str="14:20",
        snippet="Aman dikkat edin: TBMM Başkanı oy kullanamaz, bu ÖSYM'nin en büyük tuzağıdır."
    )
    trap_claim = AtomicClaim(
        claim_id="clm_trap_test",
        text="ÖSYM Tuzağı: TBMM Başkanı oy kullanamaz ama başkanvekilleri yönettikleri oturum hariç oy kullanabilir.",
        lesson="VATANDASLIK",
        topic="TBMM Başkanlığı",
        claim_type=ClaimType.TRAP,
        evidence_refs=[ev],
        verification_status=VerificationStatus.VERIFIED
    )

    res = knowledge_store.commit_verified_claim(trap_claim, verification_status="VERIFIED")
    assert res is not None
    results = knowledge_store.search("TBMM Başkanı oy")
    assert len(results) > 0
    assert results[0]["record_type"] == "TRAP"

def test_teacher_tone_does_not_alter_factual_payload():
    """Phase 17: Hoca hitapları ve duygusal tonlamalar metinden arındırılır, olgusal çekirdek korunur."""
    raw_teacher_statement = "Arkadaşlar buraya dikkat: TBMM seçimleri beş yılda bir yapılır."
    cleaned = teacher_learner.strip_teacher_rhetoric(raw_teacher_statement)
    assert cleaned == "TBMM seçimleri beş yılda bir yapılır."

    raw_2 = "ÖSYM bunu çok sever! Cumhurbaşkanı kararnamesi kanuna aykırı olamaz."
    cleaned_2 = teacher_learner.strip_teacher_rhetoric(raw_2)
    assert cleaned_2 == "Cumhurbaşkanı kararnamesi kanuna aykırı olamaz."
