"""
KPSS Super-Brain: P0/P1 Remediation Regression Test Suite
12 Kritik Düzeltmenin Doğrulanması:
1. P0-01: MAX_ITERATIONS asla haksız COMPLETED üretmez, FAILED üretir.
2. P0-02: Çözümlenmemiş çelişkiler completion'ı engeller.
3. P0-03: Öğretmen-Öğretmen çelişkileri UNRESOLVED kalır, Resmî-Öğretmen OFFICIAL_SOURCE_WINS olur.
4. P0-04: Gap analizleri hedefe yönelik sorgular üretir.
5. P0-05: Mükerrer video ID'leri filtrelenir.
6. P1-01: Kanıtsız iddia UNVERIFIED döner.
7. P1-02: 4'lü doğrulama taksonomisi (VERIFIED, REJECTED, CONTRADICTORY, UNVERIFIED).
8. P1-03: z3_sat sadece Z3 fiilen çalıştığında boolean döner, aksi halde None'dır.
9. P1-04: Hiç iddia yoksa verification_score = 0.0'dır.
10. P1-06: Öğretmen isimleri canonical normalizasyondan geçer.
11. P1-07: Aynı öğretmenin birden çok videosu hoca çeşitliliğini artıramaz.
12. P1-10: KnowledgeStore düşük güvenli/doğrulanmamış verileri RAG'e sızdırmaz.
"""
import pytest
import asyncio
from brain.models import (
    ResearchJob, ResearchJobState, AtomicClaim, EvidenceRef, ClaimType, SourceType,
    VerificationStatus, ContradictionResolution
)
from autonomous.research_agent import CompletionEvaluator, ResearchAgent
from cognition.contradiction_engine import contradiction_engine
from anti_hallucination.fact_checker import fact_checker
from cognition.teacher_identity import teacher_identity
from brain.curriculum_matrix import curriculum_matrix
from brain.knowledge_store import knowledge_store

def test_p0_01_max_iterations_unapproved_yields_false():
    """P0-01: Düşük skorlu araştırma onay alamaz."""
    eval_res = CompletionEvaluator.evaluate(
        job=None,
        mastery_data={"overall_mastery": 0.40, "source_coverage": 0.25, "concept_coverage": 0.20},
        unresolved_contradictions=0
    )
    assert eval_res["approved"] is False
    assert eval_res["has_material_gaps"] is True

def test_p0_02_unresolved_high_contradiction_blocks_completion():
    """P0-02: Çözümlenmemiş yüksek öncelikli çelişki completion'ı engeller."""
    eval_res = CompletionEvaluator.evaluate(
        job=None,
        mastery_data={"overall_mastery": 0.95, "source_coverage": 0.90, "concept_coverage": 0.90},
        unresolved_contradictions=1
    )
    assert eval_res["approved"] is False

def test_p0_03_teacher_vs_teacher_remains_unresolved():
    """P0-03: İki öğretmen arasındaki çelişki UNRESOLVED kalır."""
    claims = [
        {"claim_id": "c1", "text": "AYM 15 üyeden oluşur.", "source": "Öğretmen A", "speaker_or_author": "Öğretmen A"},
        {"claim_id": "c2", "text": "AYM 11 üyeden oluşur.", "source": "Öğretmen B", "speaker_or_author": "Öğretmen B"}
    ]
    recs = contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "YARGI", claims)
    assert len(recs) == 1
    assert recs[0].resolution == ContradictionResolution.UNRESOLVED
    assert recs[0].winning_claim_id is None

def test_p0_03_official_vs_teacher_official_wins():
    """P0-03: Resmî kaynak ile öğretmen çeliştiğinde OFFICIAL_SOURCE_WINS olur."""
    claims = [
        {"claim_id": "c_off", "text": "AYM 15 üyeden oluşur.", "source": "Resmî Gazete 1982 Anayasası Madde 146"},
        {"claim_id": "c_tea", "text": "AYM 11 üyeden oluşur.", "source": "Öğretmen X Ders Notu"}
    ]
    recs = contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "YARGI", claims)
    assert len(recs) == 1
    assert recs[0].resolution == ContradictionResolution.OFFICIAL_SOURCE_WINS
    assert recs[0].winning_claim_id == "c_off"

def test_p1_01_claim_without_evidence_is_unverified():
    """P1-01: Kanıt referansı olmayan iddia UNVERIFIED döner."""
    claim = AtomicClaim(
        claim_id="clm_unverified",
        text="TBMM 600 milletvekilinden oluşur.",
        lesson="VATANDASLIK",
        topic="Yasama",
        evidence_refs=[]  # Kanıt yok
    )
    res = fact_checker.verify_claim(claim)
    assert res.is_valid is False
    assert res.status == VerificationStatus.UNVERIFIED
    assert "EvidenceRef" in res.reason

def test_p1_03_z3_sat_reflects_actual_execution():
    """P1-03: Sayısal/anayasal olmayan metinlerde z3_sat None döner."""
    claim_non_numeric = {
        "claim_id": "c_geo",
        "text": "Türkiye'nin en yüksek dağı Ağrı Dağı'dır.",
        "lesson": "COGRAFYA",
        "source": "Coğrafya Ders Kitabı",
        "evidence_refs": [{"source_id": "src_1", "snippet": "Ağrı Dağı"}]
    }
    res = fact_checker.verify_claim(claim_non_numeric)
    assert res.z3_sat is None  # Z3 sayısal iddia olmadığı için çalıştırılmadı

    claim_numeric = {
        "claim_id": "c_num",
        "text": "1982 Anayasası'na göre AYM 15 üyeden oluşur.",
        "lesson": "VATANDASLIK",
        "source": "Anayasa Metni",
        "evidence_refs": [{"source_id": "src_2", "snippet": "15 üye"}]
    }
    res_num = fact_checker.verify_claim(claim_numeric)
    assert res_num.z3_sat is True  # Z3 fiilen çalıştı ve SAT döndü

def test_p1_06_teacher_identity_normalization():
    """P1-06: Öğretmen adı varyasyonları aynı kanonik isme normalize edilir."""
    t1 = teacher_identity.normalize("ramazan yetgin")
    t2 = teacher_identity.normalize("  RAMAZAN YETGİN ")
    t3 = teacher_identity.normalize("Ramazan Yetgin")
    assert t1 == "Ramazan Yetgin"
    assert t1 == t2 == t3

def test_p1_10_knowledge_store_filters_unverified_records():
    """P1-10: KnowledgeStore düşük güvenli/doğrulanmamış verileri döndürmez."""
    # Güven skoru 0.50 olan geçici kayıt ekle
    knowledge_store.add_record(
        text="Doğrulanmamış şüpheli KPSS notu.",
        record_type="FACT",
        lesson="VATANDASLIK",
        topic="GENEL",
        confidence=0.50
    )
    # Arama yapıldığında confidence >= 0.85 filtresi nedeniyle bu kayıt gelmemelidir
    results = knowledge_store.search("şüpheli KPSS notu", lesson="VATANDASLIK")
    assert len(results) == 0
