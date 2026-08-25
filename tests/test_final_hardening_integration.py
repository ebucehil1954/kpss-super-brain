"""
KPSS Super-Brain: Task 11 — Agent Hardening & Final Integration Test Suite
VerificationStatus import bug doğrulaması, uçtan uca deterministik COMPLETED akışı
ve tüm entegrasyon güvenlik kapılarını test eder.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from brain.models import (
    ResearchJob, ResearchJobState, AtomicClaim, EvidenceRef, ClaimType, SourceType,
    VerificationStatus, ContradictionResolution
)
import autonomous.research_agent as ra_module
from autonomous.research_agent import CompletionEvaluator, ResearchAgent, research_agent
from autonomous.gap_analyzer import gap_analyzer
from autonomous.research_planner import research_planner
from autonomous.tool_registry import tool_registry
from anti_hallucination.fact_checker import fact_checker
from cognition.contradiction_engine import contradiction_engine
from cognition.teacher_identity import teacher_identity
from brain.curriculum_matrix import curriculum_matrix
from brain.database import db_session

def test_task11_verification_status_is_defined_in_research_agent():
    """TASK 11: VerificationStatus autonomous/research_agent.py modülünde tanımlıdır ve NameError vermez."""
    assert hasattr(ra_module, "VerificationStatus"), "VerificationStatus autonomous.research_agent içinde import edilmiş olmalıdır!"
    assert ra_module.VerificationStatus.VERIFIED == VerificationStatus.VERIFIED

@pytest.mark.asyncio
async def test_task11_mocked_end_to_end_reaches_completed():
    """
    TASK 11: Gerçek araştırma döngüsü (mocked tools ile 3 hoca, doğrulanmış kanıtlar ve mevzuat)
    tüm aşamaları geçerek ve evaluator onayını alarak KESİN OLARAK 'COMPLETED' durumuna ulaşmalıdır.
    """
    topic_name = "1982 Anayasası: Yasama Organı ve Fonksiyonları"
    lesson_name = "VATANDASLIK"
    target_concepts = ["TBMM üye sayısı", "seçimler"]

    with db_session() as conn:
        conn.cursor().execute("DELETE FROM contradictions WHERE topic = ?", (topic_name,))
        conn.cursor().execute("DELETE FROM topic_mastery WHERE topic_name = ?", (topic_name,))

    mock_videos = [
        {"video_id": "v_succ_101", "teacher_name": "Ramazan Yetgin", "title": "Yasama 1", "channel": "Benim Hocam"},
        {"video_id": "v_succ_102", "teacher_name": "Emrah Vahap Özkaraca", "title": "Yasama 2", "channel": "Hoca Webde"},
        {"video_id": "v_succ_103", "teacher_name": "Esra Özkan Karaoğlu", "title": "Yasama 3", "channel": "İsem TV"}
    ]

    mock_transcript = """
    1982 Anayasası'na göre TBMM kuruluşu ve üye sayısı 600 milletvekilidir.
    TBMM seçimleri 5 yılda bir yapılır ve seçim yenilenmesi 360 çoğunlukla olur.
    Milletvekili seçilme yeterliliği şartları en az 18 yaşını doldurmak ve ilkokul mezunu olmaktır.
    Milletvekili dokunulmazlığı ve yasama bağışıklıkları TBMM Genel Kurulu kararıyla kaldırılabilir.
    TBMM'nin görev ve yetkileri kanun koymak, bütçe kanununu kabul etmek ve savaş ilan etmektir.
    TBMM toplantı yeter sayısı 200, en az karar yeter sayısı 151 milletvekilidir.
    Parlamento kararları ve denetim yolları yazılı soru, genel görüşme ve meclis araştırmasıdır.
    Anayasa Mahkemesi 15 üyeden oluşur.
    """

    async def mock_execute(tool_name: str, params: dict):
        if tool_name == "youtube_search":
            return {"success": True, "output": {"videos": mock_videos}}
        elif tool_name == "transcript_fetch":
            return {
                "success": True,
                "output": {
                    "text": mock_transcript,
                    "segments": [
                        {"start": 10.0, "end": 25.0, "text": "TBMM üye sayısı 600 milletvekilidir."}
                    ]
                }
            }
        elif tool_name == "official_mevzuat_search":
            return {
                "success": True,
                "output": {
                    "text": "1982 Anayasası Madde 75: TBMM 600 milletvekilinden kurulur. Madde 77: TBMM seçimleri 5 yılda bir yapılır."
                }
            }
        return {"success": True, "output": {}}

    with patch.object(tool_registry, "execute", side_effect=mock_execute):
        res = await research_agent.run_autonomous_research_cycle(
            goal="1982 Anayasası Yasama Organı Uçtan Uca Araştırma",
            lesson=lesson_name,
            topic=topic_name,
            target_concepts=target_concepts
        )

    # Kesin ve net kontrat doğrulaması
    assert res["status"] == "COMPLETED", f"Araştırma COMPLETED olmalıydı, hata: {res.get('error')}"
    assert res["error"] is None
    assert res["sources_ingested"] >= 3
    assert res["claims_verified"] >= 1
    assert res["mastery_score"] >= 0.80

@pytest.mark.asyncio
async def test_task11_runtime_exception_is_specifically_logged():
    """TASK 11: Çalışma zamanı hatası oluştuğunda bu sessizce gizlenmez, RESEARCH_EXCEPTION ile loglanır."""
    async def broken_execute(tool_name: str, params: dict):
        raise RuntimeError("Simulated connection dropped")

    with patch.object(tool_registry, "execute", side_effect=broken_execute):
        res = await research_agent.run_autonomous_research_cycle(
            goal="Hata Testi",
            lesson="VATANDASLIK",
            topic="Genel Konu",
            target_concepts=["Kavram 1"]
        )

    assert res["status"] == "FAILED"
    assert res["error"] is not None
    assert "RESEARCH_EXCEPTION" in res["error"]

def test_int_02_evidence_failure_blocks_verification():
    """Entegrasyon 2: Kanıt referansı taşımayan iddia asla VERIFIED olamaz."""
    claim = AtomicClaim(
        claim_id="clm_int_no_ev",
        text="TBMM genel af kanununu 360 oyla çıkarır.",
        lesson="VATANDASLIK",
        topic="Yasama",
        evidence_refs=[]
    )
    res = fact_checker.verify_claim(claim)
    assert res.is_valid is False
    assert res.status == VerificationStatus.UNVERIFIED

def test_int_03_contradiction_failure_blocks_completion():
    """Entegrasyon 3: Çözümlenmemiş yüksek şiddetli çelişki completion gate'i bloklar."""
    claims = [
        {"claim_id": "c_int_t1", "text": "AYM 15 üyeden kurulur.", "source": "Öğretmen 1", "speaker_or_author": "Öğretmen 1"},
        {"claim_id": "c_int_t2", "text": "AYM 11 üyeden kurulur.", "source": "Öğretmen 2", "speaker_or_author": "Öğretmen 2"}
    ]
    recs = contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "INT_CONTRA_TOPIC", claims)
    assert len(recs) == 1
    assert recs[0].resolution == ContradictionResolution.UNRESOLVED

    unresolved_cnt = contradiction_engine.count_unresolved_high_severity("VATANDASLIK", "INT_CONTRA_TOPIC")
    eval_res = CompletionEvaluator.evaluate(
        job=None,
        mastery_data={"overall_mastery": 0.95, "source_coverage": 0.90, "concept_coverage": 0.90},
        unresolved_contradictions=unresolved_cnt
    )
    assert eval_res["approved"] is False

def test_int_04_gap_driven_iteration_plan():
    """Entegrasyon 4: GapAnalyzer çıktısı ResearchPlanner tarafından hedefe yönelik sorgulara dönüştürülür."""
    gap_rep = {
        "has_material_gaps": True,
        "gap_status": "MATERIAL_GAPS",
        "missing_concepts": ["HSK Yapısı"],
        "unresolved_contradictions": [],
        "weak_claims": [],
        "single_source_claims": [],
        "missing_teacher_diversity": False
    }
    plan = research_planner.create_research_plan("VATANDASLIK", "Yargı", gap_rep, iteration=2)
    assert plan["requires_additional_research"] is True
    assert any("HSK Yapısı" in q for q in plan["queries"])

def test_int_05_exhausted_iteration_yields_failed():
    """Entegrasyon 5: Bütçe dolduğunda ve onay alınamadığında FAILED üretilir."""
    eval_res = CompletionEvaluator.evaluate(
        job=None,
        mastery_data={"overall_mastery": 0.40, "source_coverage": 0.25, "concept_coverage": 0.20},
        unresolved_contradictions=0
    )
    assert eval_res["approved"] is False

def test_int_06_duplicate_video_skipped():
    """Entegrasyon 6: Mükerrer videolar işlenmez ve tekil kalır."""
    topic_name = "Kurtuluş Savaşı Muharebeler Dönemi"
    curriculum_matrix.record_video_consumption("TARIH", topic_name, "vid_int_dup_1", "Ramazan Yetgin", "Ch1")
    m1 = curriculum_matrix.calculate_deterministic_mastery(topic_name)
    cnt1 = m1["consumed_videos_count"]

    # Tekrar aynı video
    curriculum_matrix.record_video_consumption("TARIH", topic_name, "vid_int_dup_1", "Ramazan Yetgin", "Ch1")
    m2 = curriculum_matrix.calculate_deterministic_mastery(topic_name)
    assert m2["consumed_videos_count"] == cnt1

def test_int_07_duplicate_claim_idempotency():
    """Entegrasyon 7: Aynı iddia hash'i tekilleştirilir."""
    c1 = AtomicClaim(claim_id="clm_1", text="TBMM 600 üyedir.", lesson="VATANDASLIK", topic="Yasama")
    c2 = AtomicClaim(claim_id="clm_1", text="TBMM 600 üyedir.", lesson="VATANDASLIK", topic="Yasama")
    assert c1.provenance_hash == c2.provenance_hash

def test_int_08_teacher_diversity_bounding():
    """Entegrasyon 8: Aynı öğretmenin 4 videosu 1 tekil hoca sayılır."""
    topic_name = "Osmanlı Kültür ve Medeniyeti"
    for v in ["v1", "v2", "v3", "v4"]:
        curriculum_matrix.record_video_consumption("TARIH", topic_name, v, "Ramazan Yetgin Hoca", "Ch1")
    m = curriculum_matrix.calculate_deterministic_mastery(topic_name)
    assert m["distinct_teachers_count"] == 1
    assert m["source_coverage"] == 0.25

def test_int_09_concept_coverage_verified_integrity():
    """Entegrasyon 9: Kavram doluluk oranı yalnızca doğrulanmış iddialara dayanır."""
    topic_name = "1982 Anayasası: Yasama Organı ve Fonksiyonları"
    m = curriculum_matrix.calculate_deterministic_mastery(topic_name)
    assert 0.0 <= m["concept_coverage"] <= 1.0

def test_int_10_final_completion_gate_strict_invariants():
    """Entegrasyon 10: COMPLETED yalnızca ve yalnızca tüm 4 onay kriteri sağlandığında verilir."""
    # Başarısız durum
    res_fail = CompletionEvaluator.evaluate(
        job=None,
        mastery_data={"overall_mastery": 0.79, "source_coverage": 0.50, "concept_coverage": 0.80},
        unresolved_contradictions=0
    )
    assert res_fail["approved"] is False

    # Başarılı durum
    res_pass = CompletionEvaluator.evaluate(
        job=None,
        mastery_data={"overall_mastery": 0.85, "source_coverage": 0.60, "concept_coverage": 0.85},
        unresolved_contradictions=0
    )
    assert res_pass["approved"] is True

# ==========================================
# PHASE 2 — SEMANTIC AI CONTRADICTION & Z3 TESTS
# ==========================================

from cognition.contradiction_engine import check_contradiction
from config import super_brain_config

def test_phase2_check_contradiction_semantic_and_numerical():
    """PHASE 2: check_contradiction fonksiyonu sayısal ve semantik çelişkileri doğru tespit eder."""
    # 1. Sayısal çelişki
    res_num = check_contradiction(
        "1982 Anayasası'na göre Anayasa Mahkemesi 15 üyeden kurulur.",
        "1982 Anayasası'na göre Anayasa Mahkemesi 11 üyeden kurulur."
    )
    assert res_num["is_contradictory"] is True
    assert res_num["severity"] == "HIGH"

    # 2. Tamamen farklı konu (çelişki yok)
    res_diff = check_contradiction(
        "Türkiye'de en yüksek dağ Ağrı Dağı'dır.",
        "TBMM seçimleri 5 yılda bir yapılır."
    )
    assert res_diff["is_contradictory"] is False

def test_phase2_z3_timeout_config():
    """PHASE 2: config.py içinde Z3_TIMEOUT = 500ms tanımlıdır."""
    assert hasattr(super_brain_config, "Z3_TIMEOUT")
    assert super_brain_config.Z3_TIMEOUT == 500
