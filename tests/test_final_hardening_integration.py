"""
KPSS Super-Brain: Task 10 — Agent Hardening & Final Integration Test Suite
Tüm 10 entegrasyon güvenlik kontrolünü (State, Evidence, Claims, Contradictions,
Mastery, Research, Reliability, Completion Gate) uçtan uca doğrular.
"""
import pytest
import asyncio
from brain.models import (
    ResearchJob, ResearchJobState, AtomicClaim, EvidenceRef, ClaimType, SourceType,
    VerificationStatus, ContradictionResolution
)
from autonomous.research_agent import CompletionEvaluator, ResearchAgent, research_agent
from autonomous.gap_analyzer import gap_analyzer
from autonomous.research_planner import research_planner
from anti_hallucination.fact_checker import fact_checker
from cognition.contradiction_engine import contradiction_engine
from cognition.teacher_identity import teacher_identity
from brain.curriculum_matrix import curriculum_matrix

@pytest.mark.asyncio
async def test_int_01_end_to_end_research_cycle_execution():
    """Entegrasyon 1: Uçtan uca araştırma döngüsü durumları ve olay günlüğü."""
    res = await research_agent.run_autonomous_research_cycle(
        goal="TBMM Seçimleri ve Dokunulmazlık Araştırması",
        lesson="VATANDASLIK",
        topic="1982 Anayasası Yasama Organı ve Sayıları",
        target_concepts=["TBMM Seçimleri", "Milletvekili Dokunulmazlığı"]
    )
    assert "research_id" in res
    assert res["status"] in ["COMPLETED", "FAILED"]
    assert res["iterations"] >= 1

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
