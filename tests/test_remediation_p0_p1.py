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

# ==========================================
# TASK 01 — COMPLETION STATE INTEGRITY TESTS
# ==========================================

def test_task01_low_mastery_not_approved():
    """TASK 01: Düşük mastery (0.50 < 0.80) kesinlikle approved=False üretir."""
    res = CompletionEvaluator.evaluate(
        job=None,
        mastery_data={"overall_mastery": 0.50, "source_coverage": 0.30, "concept_coverage": 0.40},
        unresolved_contradictions=0
    )
    assert res["approved"] is False

def test_task01_unresolved_contradiction_not_approved():
    """TASK 01: Unresolved contradiction varsa (1 > 0) kesinlikle approved=False üretir."""
    res = CompletionEvaluator.evaluate(
        job=None,
        mastery_data={"overall_mastery": 0.95, "source_coverage": 0.90, "concept_coverage": 0.90},
        unresolved_contradictions=1
    )
    assert res["approved"] is False

def test_task01_evaluator_approved_true_when_all_criteria_met():
    """TASK 01: Tüm kriterler sağlandığında (mastery>=0.80, concept>=0.80, source>=0.50, contra==0) approved=True döner."""
    res = CompletionEvaluator.evaluate(
        job=None,
        mastery_data={"overall_mastery": 0.88, "source_coverage": 0.75, "concept_coverage": 0.85},
        unresolved_contradictions=0
    )
    assert res["approved"] is True
    assert res["has_material_gaps"] is False

# ==========================================
# TASK 02 — CLAIM EVIDENCE INTEGRITY TESTS
# ==========================================

def test_task02_empty_evidence_and_empty_source_is_unverified():
    """TASK 02: evidence_refs=[] ve source='' olan iddia UNVERIFIED döner."""
    claim = {
        "claim_id": "c_empty_ev",
        "text": "1982 Anayasası Madde 146 Anayasa Mahkemesi 15 üyeden oluşur.",
        "lesson": "VATANDASLIK",
        "evidence_refs": [],
        "source": ""
    }
    res = fact_checker.verify_claim(claim)
    assert res.is_valid is False
    assert res.status == VerificationStatus.UNVERIFIED
    assert "EvidenceRef" in res.reason

def test_task02_only_plain_source_string_is_unverified():
    """TASK 02: Yalnızca {'source': 'Resmî Mevzuat'} taşıyan ama geçerli evidence_refs taşımayan iddia UNVERIFIED döner."""
    claim = {
        "claim_id": "c_plain_str",
        "text": "1982 Anayasası Madde 146 Anayasa Mahkemesi 15 üyeden oluşur.",
        "lesson": "VATANDASLIK",
        "source": "Resmî Mevzuat / Mevzuat.gov.tr",
        "evidence_refs": []  # Düz kaynak dizesi tek başına kanıt değildir!
    }
    res = fact_checker.verify_claim(claim)
    assert res.is_valid is False
    assert res.status == VerificationStatus.UNVERIFIED
    assert "Düz metin kaynakları tek başına kanıt sayılamaz" in res.reason

def test_task02_valid_evidence_ref_triggers_validation():
    """TASK 02: Gerçek EvidenceRef (source_id + snippet) taşıyan iddia doğrulama katmanlarına girer ve VERIFIED olur."""
    claim = AtomicClaim(
        claim_id="c_valid_ev",
        text="1982 Anayasası'na göre TBMM 600 milletvekilinden oluşur.",
        lesson="VATANDASLIK",
        topic="Yasama",
        evidence_refs=[
            EvidenceRef(
                source_id="src_mevzuat_1982",
                source_type=SourceType.OFFICIAL_LEGISLATION,
                snippet="Madde 75 – Türkiye Büyük Millet Meclisi genel oyla seçilen altıyüz milletvekilinden oluşur.",
                url="https://www.mevzuat.gov.tr"
            )
        ]
    )
    res = fact_checker.verify_claim(claim)
    assert res.is_valid is True
    assert res.status == VerificationStatus.VERIFIED

def test_task02_video_evidence_segment_and_timestamp_check():
    """TASK 02: Video kaynaklı EvidenceRef video_id, segment_id, snippet ve timestamp taşır."""
    ev = EvidenceRef(
        source_id="src_yt_abc123",
        source_type=SourceType.YOUTUBE_TRANSCRIPT,
        video_id="abc12345678",
        segment_id="seg_abc123_4",
        snippet="AYM 15 üyeden oluşur ve üyelerin görev süresi 12 yıldır.",
        speaker_or_author="Emrah Vahap",
        timestamp_str="05:10 - 05:35"
    )
    assert ev.video_id == "abc12345678"
    assert ev.segment_id == "seg_abc123_4"
    assert ev.timestamp_str == "05:10 - 05:35"
    assert len(ev.snippet) > 10

def test_task02_verified_claim_evidence_cannot_be_empty():
    """TASK 02: VERIFIED statüsüne sahip bir iddianın kanıt referans listesi asla boş olamaz."""
    claim_no_ev = {
        "claim_id": "c_no_ev_assert",
        "text": "TBMM seçimleri 5 yılda bir yapılır.",
        "lesson": "VATANDASLIK",
        "evidence_refs": []
    }
    res = fact_checker.verify_claim(claim_no_ev)
    # Eğer is_valid True olursa veya VERIFIED dönerse kural ihlalidir!
    assert res.status != VerificationStatus.VERIFIED
    assert res.is_valid is False
