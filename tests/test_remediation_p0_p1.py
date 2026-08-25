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
    import uuid
    uniq_q = f"supheli_kpss_notu_{uuid.uuid4().hex[:8]}"
    # Güven skoru 0.50 olan geçici kayıt ekle
    knowledge_store.add_record(
        text=f"Doğrulanmamış şüpheli not {uniq_q}",
        record_type="FACT",
        lesson="VATANDASLIK",
        topic="GENEL",
        confidence=0.50
    )
    # Arama yapıldığında confidence >= 0.85 filtresi nedeniyle bu kayıt gelmemelidir
    results = knowledge_store.search(uniq_q, lesson="VATANDASLIK")
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

# ==========================================
# TASK 03 — ATOMIC CLAIM LIFECYCLE TESTS
# ==========================================

def test_task03_lifecycle_pending_initial_state():
    """TASK 03 Lifecycle: Yeni üretilen/çıkarılan iddia PENDING durumunda başlar (Extraction != Verification)."""
    claim = AtomicClaim(
        claim_id="c_lifecycle_pending",
        text="Cumhurbaşkanı 5 yıllığına seçilir.",
        lesson="VATANDASLIK",
        topic="Yürütme",
        evidence_refs=[
            EvidenceRef(
                source_id="src_yt_sample",
                source_type=SourceType.YOUTUBE_TRANSCRIPT,
                snippet="Cumhurbaşkanı 5 yıllığına seçilir."
            )
        ]
    )
    assert claim.verification_status == VerificationStatus.PENDING

def test_task03_lifecycle_unverified_on_missing_evidence():
    """TASK 03 Lifecycle: Kanıtı eksik/geçersiz iddia doğrulamada UNVERIFIED alır."""
    claim = AtomicClaim(
        claim_id="c_lifecycle_unver",
        text="TBMM genel af kararını 360 oyla alır.",
        lesson="VATANDASLIK",
        topic="Yasama",
        evidence_refs=[]  # Kanıt yok
    )
    res = fact_checker.verify_claim(claim)
    assert res.status == VerificationStatus.UNVERIFIED
    assert res.is_valid is False

def test_task03_lifecycle_rejected_on_rule_or_blacklist_failure():
    """TASK 03 Lifecycle: Mülga kanun/kural ihlali içeren iddia doğrulamada REJECTED alır."""
    claim = AtomicClaim(
        claim_id="c_lifecycle_rej",
        text="Başbakan ve Bakanlar Kurulu kanun tasarısı hazırlar.",
        lesson="VATANDASLIK",
        topic="Yasama",
        evidence_refs=[
            EvidenceRef(
                source_id="src_yt_old",
                source_type=SourceType.YOUTUBE_TRANSCRIPT,
                snippet="Başbakan kanun tasarısı hazırlar."
            )
        ]
    )
    res = fact_checker.verify_claim(claim)
    assert res.status == VerificationStatus.REJECTED
    assert res.is_valid is False

def test_task03_lifecycle_verified_on_full_success():
    """TASK 03 Lifecycle: Kanıtı tam ve tüm anti-halüsinasyon/Z3 katmanlarından geçen iddia VERIFIED olur."""
    claim = AtomicClaim(
        claim_id="c_lifecycle_ver",
        text="1982 Anayasası Madde 146 uyarınca Anayasa Mahkemesi 15 üyeden oluşur.",
        lesson="VATANDASLIK",
        topic="Yargı",
        evidence_refs=[
            EvidenceRef(
                source_id="src_official_anayasa",
                source_type=SourceType.OFFICIAL_LEGISLATION,
                snippet="Anayasa Mahkemesi onbeş üyeden kurulur.",
                url="https://www.mevzuat.gov.tr"
            )
        ]
    )
    res = fact_checker.verify_claim(claim)
    assert res.status == VerificationStatus.VERIFIED
    assert res.is_valid is True

# ==========================================
# TASK 04 — CONTRADICTION RESOLUTION INTEGRITY TESTS
# ==========================================

def test_task04_teacher_vs_teacher_remains_unresolved():
    """TASK 04: İki bağımsız öğretmen çeliştiğinde konsensüs yoksa durum UNRESOLVED kalır."""
    claims = [
        {"claim_id": "c_t1", "text": "1982 Anayasası'na göre AYM 15 üyeden kurulur.", "source": "Öğretmen Ali", "speaker_or_author": "Öğretmen Ali"},
        {"claim_id": "c_t2", "text": "1982 Anayasası'na göre AYM 11 üyeden kurulur.", "source": "Öğretmen Veli", "speaker_or_author": "Öğretmen Veli"}
    ]
    recs = contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "YARGI", claims)
    assert len(recs) == 1
    assert recs[0].resolution == ContradictionResolution.UNRESOLVED
    assert recs[0].winning_claim_id is None

def test_task04_official_vs_teacher_official_wins():
    """TASK 04: Resmî mevzuat ile öğretmen çeliştiğinde OFFICIAL_SOURCE_WINS uygulanır."""
    claims = [
        {"claim_id": "c_off_1", "text": "1982 Anayasası Madde 146: AYM 15 üyeden oluşur.", "source": "Resmî Gazete 1982 Anayasası", "evidence_refs": [{"source_id": "src_mevzuat", "source_type": "OFFICIAL_LEGISLATION", "snippet": "15 üye"}]},
        {"claim_id": "c_tea_1", "text": "AYM 11 üyeden oluşur.", "source": "Hoca Ders Notu"}
    ]
    recs = contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "YARGI", claims)
    assert len(recs) == 1
    assert recs[0].resolution == ContradictionResolution.OFFICIAL_SOURCE_WINS
    assert recs[0].winning_claim_id == "c_off_1"

def test_task04_multi_source_consensus_resolution():
    """TASK 04: 3 bağımsız öğretmen aynı iddiayı savunup 1 öğretmen çelişiyorsa MULTI_SOURCE_CONSENSUS ile çoğunluk kazanır."""
    claims = [
        {"claim_id": "c_hoca_1", "text": "TBMM 600 milletvekilidir.", "source": "Hoca 1", "speaker_or_author": "Hoca 1"},
        {"claim_id": "c_hoca_2", "text": "TBMM 600 milletvekilidir.", "source": "Hoca 2", "speaker_or_author": "Hoca 2"},
        {"claim_id": "c_hoca_3", "text": "TBMM 600 milletvekilidir.", "source": "Hoca 3", "speaker_or_author": "Hoca 3"},
        {"claim_id": "c_hoca_4", "text": "TBMM 550 milletvekilidir.", "source": "Hoca 4", "speaker_or_author": "Hoca 4"}
    ]
    recs = contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "YASAMA", claims)
    assert len(recs) >= 1
    # 600 mv savunan 3 hocanın iddiası konsensüs ile kazanmalıdır
    consensus_recs = [r for r in recs if r.resolution == ContradictionResolution.MULTI_SOURCE_CONSENSUS]
    assert len(consensus_recs) >= 1
    assert consensus_recs[0].winning_claim_id in ["c_hoca_1", "c_hoca_2", "c_hoca_3"]

def test_task04_duplicate_contradiction_is_idempotent():
    """TASK 04: Aynı çelişki tekrar tespit edildiğinde veritabanında mükerrer kayıt üretilmez (idempotent)."""
    claims = [
        {"claim_id": "c_idemp_1", "text": "AYM 15 üyeden oluşur.", "source": "Öğretmen X", "speaker_or_author": "Öğretmen X"},
        {"claim_id": "c_idemp_2", "text": "AYM 11 üyeden oluşur.", "source": "Öğretmen Y", "speaker_or_author": "Öğretmen Y"}
    ]
    recs1 = contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "YARGI_TEST", claims)
    recs2 = contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "YARGI_TEST", claims)
    assert recs1[0].contradiction_id == recs2[0].contradiction_id
    
    unresolved_cnt = contradiction_engine.count_unresolved_high_severity("VATANDASLIK", "YARGI_TEST")
    assert unresolved_cnt == 1  # 2 defa çağrılsa da tek 1 kayıt vardır

# ==========================================
# TASK 05 — DETERMINISTIC MASTERY TESTS
# ==========================================

def test_task05_zero_evidence_yields_low_mastery():
    """TASK 05: Hiçbir doğrulanmış iddia veya tüketilmiş video yoksa mastery skoru 0.0 veya çok düşüktür (keyfi 0.90/0.50 fallback yok)."""
    m = curriculum_matrix.calculate_deterministic_mastery("TOPIC_NON_EXISTENT_XYZ")
    assert m["overall_mastery"] == 0.0

def test_task05_one_teacher_four_videos_not_four_teacher_coverage():
    """TASK 05: 1 öğretmenden 4 video tüketildiğinde source_coverage 1.0 değil, 1/4 = 0.25 olur."""
    # Ramazan Yetgin'den 4 farklı video tüketildiğini kaydedelim
    for vid in ["v_ry_1", "v_ry_2", "v_ry_3", "v_ry_4"]:
        curriculum_matrix.record_video_consumption(
            lesson="TARIH",
            topic="İlk Türk Devletleri",
            video_id=vid,
            teacher_name="Ramazan Yetgin",
            channel_name="Benim Hocam"
        )
    m = curriculum_matrix.calculate_deterministic_mastery("İlk Türk Devletleri")
    assert m["distinct_teachers_count"] == 1
    assert m["source_coverage"] == 0.25  # 1/4

def test_task05_duplicate_videos_do_not_increase_coverage():
    """TASK 05: Aynı video ID'si tekrar kaydedildiğinde consumed_videos_count ve coverage artmaz."""
    m_before = curriculum_matrix.calculate_deterministic_mastery("İlk Türk Devletleri")
    cnt_before = m_before["consumed_videos_count"]
    
    # Aynı v_ry_1 videosunu tekrar kaydet
    curriculum_matrix.record_video_consumption(
        lesson="TARIH",
        topic="İlk Türk Devletleri",
        video_id="v_ry_1",
        teacher_name="Ramazan Yetgin",
        channel_name="Benim Hocam"
    )
    m_after = curriculum_matrix.calculate_deterministic_mastery("İlk Türk Devletleri")
    assert m_after["consumed_videos_count"] == cnt_before

def test_task05_unresolved_contradiction_lowers_agreement():
    """TASK 05: Çözümlenmemiş çelişki varsa cross_teacher_agreement 0.95'ten 0.40'a düşer."""
    topic_name = "1982 Anayasası Yargı Organı"
    claims = [
        {"claim_id": "c_agr_1", "text": "1982 Anayasası'na göre AYM 15 üyeden oluşur.", "source": "Hoca 1", "speaker_or_author": "Hoca 1"},
        {"claim_id": "c_agr_2", "text": "1982 Anayasası'na göre AYM 11 üyeden oluşur.", "source": "Hoca 2", "speaker_or_author": "Hoca 2"}
    ]
    contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", topic_name, claims)
    
    # Topic kaydı oluşturup mastery hesapla
    curriculum_matrix.record_video_consumption("VATANDASLIK", topic_name, "v_ag_1", "Hoca 1", "Ch1")
    curriculum_matrix.record_video_consumption("VATANDASLIK", topic_name, "v_ag_2", "Hoca 2", "Ch2")
    m = curriculum_matrix.calculate_deterministic_mastery(topic_name)
    assert m["cross_teacher_agreement"] == 0.40

# ==========================================
# TASK 06 — REAL GAP ANALYSIS TESTS
# ==========================================

from autonomous.gap_analyzer import gap_analyzer

def test_task06_concept_coverage_zero_yields_material_gaps():
    """TASK 06: Doğrulanmış hiçbir kavram yoksa GapAnalyzer MATERIAL_GAPS ve eksik kavramları döner."""
    res = gap_analyzer.analyze_gaps(
        lesson="VATANDASLIK",
        topic="Yasama",
        target_concepts=["TBMM Seçimleri", "Milletvekili Dokunulmazlığı"],
        claims=[],  # İddia yok
        teachers=[]
    )
    assert res["gap_status"] == "MATERIAL_GAPS"
    assert res["has_material_gaps"] is True
    assert "TBMM Seçimleri" in res["missing_concepts"]
    assert len(res["recommended_queries"]) >= 1

def test_task06_unresolved_contradiction_yields_gap():
    """TASK 06: Çözümlenmemiş çelişki varlığı GapAnalyzer tarafından MATERIAL_GAPS olarak işaretlenir."""
    claims = [
        {"claim_id": "c_cg1", "text": "AYM 15 üyedir.", "source": "Hoca 1", "speaker_or_author": "Hoca 1"},
        {"claim_id": "c_cg2", "text": "AYM 11 üyedir.", "source": "Hoca 2", "speaker_or_author": "Hoca 2"}
    ]
    contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "GAP_TEST_TOPIC", claims)
    
    res = gap_analyzer.analyze_gaps(
        lesson="VATANDASLIK",
        topic="GAP_TEST_TOPIC",
        target_concepts=[],
        claims=claims,
        teachers=["Hoca 1", "Hoca 2"]
    )
    assert res["gap_status"] == "MATERIAL_GAPS"
    assert len(res["unresolved_contradictions"]) >= 1

def test_task06_all_critical_concepts_verified_no_gaps():
    """TASK 06: Tüm kavramlar doğrulanmış ve en az 2 bağımsız öğretmen varsa NO_MATERIAL_GAPS döner."""
    claims = [
        {
            "claim_id": "c_ok1",
            "text": "1982 Anayasası'na göre TBMM seçimleri 5 yılda bir yapılır.",
            "verification_status": VerificationStatus.VERIFIED,
            "speaker_or_author": "Öğretmen Ali",
            "source": "Ali Hoca Notları",
            "evidence_refs": [{"source_id": "src_1", "snippet": "TBMM seçimleri 5 yılda bir yapılır ve yenilenir."}]
        },
        {
            "claim_id": "c_ok2",
            "text": "Milletvekili dokunulmazlığı TBMM Genel Kurulu tarafından kaldırılabilir.",
            "verification_status": VerificationStatus.VERIFIED,
            "speaker_or_author": "Öğretmen Veli",
            "source": "Veli Hoca Notları",
            "evidence_refs": [{"source_id": "src_2", "snippet": "Milletvekili dokunulmazlığı TBMM kararı ile kaldırılabilir."}]
        }
    ]
    res = gap_analyzer.analyze_gaps(
        lesson="VATANDASLIK_GAP_CLEAR",
        topic="Yasama_Clear",
        target_concepts=["TBMM Seçimleri", "Milletvekili Dokunulmazlığı"],
        claims=claims,
        teachers=["Öğretmen Ali", "Öğretmen Veli"]
    )
    assert res["gap_status"] == "NO_MATERIAL_GAPS"
    assert res["has_material_gaps"] is False
    assert len(res["missing_concepts"]) == 0

def test_task06_single_source_critical_claim_yields_gap():
    """TASK 06: Kritik bir iddia yalnızca 1 gayriresmî hocaya dayanıyorsa single_source_claims içinde listelenir ve gap üretir."""
    claims = [
        {
            "claim_id": "c_single_1",
            "text": "Lale Devri'nde ilk geçici elçilik Paris'e açılmıştır.",
            "verification_status": VerificationStatus.VERIFIED,
            "speaker_or_author": "Tek Hoca",
            "source": "Özel Ders Videosu",
            "evidence_refs": [{"source_id": "src_single", "snippet": "Lale devrinde ilk geçici elçilik 28 Çelebi Mehmet ile Paris'e açılmıştır."}]
        }
    ]
    res = gap_analyzer.analyze_gaps(
        lesson="TARIH",
        topic="Lale Devri",
        target_concepts=["Lale Devri"],
        claims=claims,
        teachers=["Tek Hoca"]
    )
    assert res["gap_status"] == "MATERIAL_GAPS"
    assert len(res["single_source_claims"]) >= 1

def test_task06_gap_output_is_deterministic():
    """TASK 06: GapAnalyzer aynı veri seti için her zaman birebir aynı deterministik çıktı ve öneri sorgularını üretir."""
    concepts = ["İskitler", "Kavimler Göçü"]
    res1 = gap_analyzer.analyze_gaps("TARIH", "İslamiyet Öncesi", concepts, [], [])
    res2 = gap_analyzer.analyze_gaps("TARIH", "İslamiyet Öncesi", concepts, [], [])
    assert res1["missing_concepts"] == res2["missing_concepts"]
    assert res1["recommended_queries"] == res2["recommended_queries"]
    assert res1["gap_status"] == res2["gap_status"]
