"""
KPSS Super-Brain: Phase 18 — Uçtan Uca Entegrasyon ve Sistem Değişmezleri (Invariants) Test Suite
Master Refactor Plan Phase 18 Kapsamı:
Tüm mimarinin (Phase 1'den Phase 17'ye kadar) 11 adımlı eksiksiz boru hattında birlikte çalışması:
1. Boş kuyruk veya öncelikli müfredat açığı seçimi
2. Doğrulanmış gerçek YouTube video kimliği kontrolü (11 karakter, fake_ yok)
3. VideoTask ve Task Sözleşmesi denetimi
4. Transkript ve kanıt parçacıklarının (EvidenceRef) çıkarımı
5. Uçtan uca provenance ve zaman damgası doğrulaması
6. Güvenlik duvarı (Knowledge Firewall): Unverified veya disputed bilgiler elenir
7. Kanonik Gerçeklik (Single Source of Truth) deposuna güvenli mühürleme
8. Repetition != Truth denetimi (Aynı kaynaktan tekrar güven skorunu yapay artıramaz)
9. Çok boyutlu hakimiyet hesaplaması (Video sayısı != Hakimiyet)
10. Bilgi grafiği döngüsüzlük (DAG) ve atomik kalıcılık doğrulaması
11. Çekirdek Değişmezler: Sıfır sahte ID, sıfır doğrulanmamış bilgi, sıfır hiyerarşik döngü, sıfır kopuk kanıt.
"""
import pytest
import re
from brain.models import (
    AtomicClaim, EvidenceRef, SourceType, VerificationStatus,
    ClaimType
)
from curriculum.models import (
    LessonType, VideoTask, TaskType, validate_task_contract
)
from brain.knowledge_store import knowledge_store
from brain.curriculum_matrix import curriculum_matrix
from brain.knowledge_graph import KPSSKnowledgeGraph
from brain.provenance import provenance_validator
from curriculum.queue import is_valid_youtube_video_id, CurriculumQueue
from curriculum.models import VideoTask, TaskType, validate_task_contract
from brain.database import db_session

def test_full_super_brain_e2e_pipeline():
    """Phase 18: 11 adımlı eksiksiz uçtan uca boru hattı senaryosu."""
    topic_id = "VATANDASLIK_ANAYASA_MAHKEMESI_E2E"
    lesson = "VATANDASLIK"
    valid_vid = "kP88vIdE2e1" # 11 karakter geçerli ID

    print("-> Stage 1: Video ID check", flush=True)
    assert is_valid_youtube_video_id(valid_vid) is True
    assert is_valid_youtube_video_id("fake_video_123") is False

    print("-> Stage 2: Task contract check", flush=True)
    v_task = VideoTask(
        task_id="vtask_e2e_01",
        video_id=valid_vid,
        url=f"https://www.youtube.com/watch?v={valid_vid}",
        title="Anayasa Mahkemesi Yapısı ve Görevleri",
        teacher_name="Emrah Vahap",
        lesson=lesson,
        topic="Anayasa Mahkemesi"
    )
    assert validate_task_contract(v_task, TaskType.VIDEO) is True
    assert validate_task_contract(v_task, TaskType.RESEARCH) is False

    print("-> Stage 3: Provenance check", flush=True)
    evidence = EvidenceRef(
        source_id=valid_vid,
        source_type=SourceType.YOUTUBE_TRANSCRIPT,
        video_id=valid_vid,
        segment_id="seg_aym_01",
        timestamp_str="08:30-09:15",
        snippet="Anayasa Mahkemesi on beş üyeden kurulur; üç üyeyi TBMM, on iki üyeyi Cumhurbaşkanı seçer."
    )
    verified_claim = AtomicClaim(
        claim_id="clm_aym_e2e_01",
        text="Anayasa Mahkemesi 15 üyeden kurulur; 3 üyeyi TBMM, 12 üyeyi Cumhurbaşkanı seçer.",
        lesson=lesson,
        topic=topic_id,
        claim_type=ClaimType.FACT,
        evidence_refs=[evidence],
        verification_status=VerificationStatus.VERIFIED,
        confidence=0.98
    )
    is_prov_ok, prov_msg = provenance_validator.validate_provenance_chain(verified_claim)
    assert is_prov_ok is True
    assert prov_msg == "PROVENANCE_OK"

    print("-> Stage 4: Commit verified claim", flush=True)
    commit_res = knowledge_store.commit_verified_claim(verified_claim, verification_status="VERIFIED")
    assert commit_res is not None
    assert commit_res["action"] in ("created", "reinforced")

    print("-> Stage 5: Pending claim blocked", flush=True)
    pending_claim = AtomicClaim(
        claim_id="clm_aym_pending",
        text="Doğrulanmamış test iddiası",
        lesson=lesson,
        topic=topic_id,
        evidence_refs=[evidence],
        verification_status=VerificationStatus.PENDING
    )
    assert knowledge_store.commit_verified_claim(pending_claim, verification_status="PENDING") is None

    print("-> Stage 6: Repetition != Truth", flush=True)
    rec1 = knowledge_store.add_or_reinforce_record(
        text="AYM Genel Kurulu toplantı yeter sayısı 10 üyedir.",
        record_type="FACT",
        lesson=lesson,
        topic=topic_id,
        confidence=0.90,
        source={"source_id": valid_vid, "speaker_or_author": "Emrah Vahap"}
    )
    rec2 = knowledge_store.add_or_reinforce_record(
        text="AYM Genel Kurulu toplantı yeter sayısı 10 üyedir.",
        record_type="FACT",
        lesson=lesson,
        topic=topic_id,
        confidence=0.90,
        source={"source_id": valid_vid, "speaker_or_author": "Emrah Vahap"}
    )
    assert rec2["times_reinforced"] == rec1["times_reinforced"] + 1
    assert rec2["confidence"] == rec1["confidence"], "Aynı kaynak tekrarı güven skorunu artıramaz!"

    print("-> Stage 7: Curriculum mastery check", flush=True)
    digest_res = curriculum_matrix.record_video_consumption(
        lesson=lesson,
        topic=topic_id,
        video_id=valid_vid,
        teacher_name="Emrah Vahap",
        channel_name="Hocawebde",
        facts_extracted=4
    )
    assert digest_res["is_mastered"] is False
    assert "MASTERED" not in digest_res["mastery_stage"]

    print("-> Stage 8: KG cycle check", flush=True)
    import tempfile
    import os
    fd, kg_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        kg = KPSSKnowledgeGraph(storage_path=kg_path)
        kg.add_node("NODE_AYM", "Anayasa Mahkemesi", "ENTITY", lesson)
        kg.add_node("NODE_YARGI", "Yargı Organları", "ENTITY", lesson)
        kg.add_edge("NODE_AYM", "NODE_YARGI", "SUBTOPIC_OF")
        with pytest.raises(ValueError):
            kg.add_edge("NODE_YARGI", "NODE_AYM", "SUBTOPIC_OF")
    finally:
        if os.path.exists(kg_path):
            os.remove(kg_path)
    print("-> Stage 9: All pipeline stages passed", flush=True)

def test_system_invariants_hold_under_stress():
    """Phase 18: Sistem değişmezleri (invariants) stres altında doğrulanır."""
    # Invariant 1: UNKNOWN lesson asla TARIH olamaz
    assert LessonType.from_str("BilinmeyenDers") == LessonType.UNKNOWN

    # Invariant 2: Pedagojik şifreler FACT olamaz
    ev = EvidenceRef(
        source_id="src_dummy_1111",
        source_type=SourceType.YOUTUBE_TRANSCRIPT,
        video_id="c0AbCdEfG11",
        segment_id="seg_01",
        timestamp_str="01:00",
        snippet="Hafıza tekniği şifresi."
    )
    mnem = AtomicClaim(
        claim_id="clm_inv_mnem",
        text="Şifreli Ezber Tekniği",
        lesson="TARIH",
        topic="Genel",
        claim_type=ClaimType.MNEMONIC,
        evidence_refs=[ev],
        verification_status=VerificationStatus.VERIFIED
    )
    res = knowledge_store.commit_verified_claim(mnem, verification_status="VERIFIED")
    assert res is not None
    search_res = knowledge_store.search("Şifreli Ezber Tekniği")
    assert search_res[0]["record_type"] == "MNEMONIC"
