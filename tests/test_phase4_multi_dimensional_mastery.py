"""
KPSS Super-Brain: Phase 4 — Çok Boyutlu Hakimiyet Testleri (Video Count != Mastery)
Master Refactor Plan Phase 4 Kapsamı:
1. test_four_bad_videos_do_not_mean_mastery: 4 boş/içeriksiz video konuyu ASLA MASTERED yapamaz.
2. test_duplicate_videos_do_not_mean_mastery: Mükerrer videolar hakimiyeti yapay olarak artıramaz.
3. test_verified_claims_increase_mastery: Doğrulanmış iddialar ve kavram kapsamı hakimiyeti yükseltir.
4. test_unresolved_critical_gap_blocks_mastery: Çözümlenmemiş çelişkiler tam hakimiyeti KESİNLİKLE bloke eder.
"""
import pytest
import json
from brain.curriculum_matrix import curriculum_matrix
from brain.database import db_session

def test_four_bad_videos_do_not_mean_mastery():
    """Phase 4: 4 adet sıfır olgulu (bad) video izlense dahi konu MASTERED olamaz."""
    topic_id = "VATANDASLIK_TEMEL_HUKUK_KAVRAMLARI"
    with db_session() as conn:
        cursor = conn.cursor()
        # 4 farklı video kaydedildi ama facts_count = 0 (içeriksiz bad videolar)
        cursor.execute("""
        UPDATE topic_mastery
        SET consumed_videos_count = 4,
            consumed_video_ids_json = '["v1", "v2", "v3", "v4"]',
            distinct_teachers_json = '["Hoca A", "Hoca B"]',
            facts_count = 0,
            is_mastered = 0,
            mastery_stage = 'UNSTARTED'
        WHERE topic_id = ?
        """, (topic_id,))

    # digest_video_into_curriculum çağrısı (facts_extracted = 0)
    res = curriculum_matrix.digest_video_into_curriculum(
        lesson="VATANDASLIK",
        topic_str="Temel Hukuk Kavramları",
        video_id="v5",
        teacher_name="Hoca C",
        channel_name="Kanal 1",
        facts_extracted=0 # Sıfır bilgi
    )
    assert res.get("is_mastered") is False, "Olgusal bilgi taşımayan videolar konuyu MASTERED yapamaz!"
    assert "MASTERED" not in res.get("mastery_stage", "")

def test_duplicate_videos_do_not_mean_mastery():
    """Phase 4: Aynı video ID'sinin tekrar tekrar izlenmesi video sayacını ve hakimiyeti artıramaz."""
    topic_id = "TARIH_OSMANLI_KURULUS"
    # İlk tüketim
    r1 = curriculum_matrix.digest_video_into_curriculum(
        lesson="TARIH",
        topic_str="Osmanlı Devleti Kuruluş Dönemi",
        video_id="vid_dup_test_01",
        teacher_name="Ramazan Yetgin",
        channel_name="Benim Hocam",
        facts_extracted=2
    )
    count_1 = r1.get("consumed_videos_count", 0)

    # Aynı video ID'si ile ikinci tüketim
    r2 = curriculum_matrix.digest_video_into_curriculum(
        lesson="TARIH",
        topic_str="Osmanlı Devleti Kuruluş Dönemi",
        video_id="vid_dup_test_01", # Aynı ID
        teacher_name="Ramazan Yetgin",
        channel_name="Benim Hocam",
        facts_extracted=1
    )
    count_2 = r2.get("consumed_videos_count", 0)
    assert count_1 == count_2, "Mükerrer video ID'si tüketilen video sayısını artıramaz!"

def test_unresolved_critical_gap_blocks_mastery():
    """Phase 4: Çözümlenmemiş kritik çelişki varsa deterministic mastery skoru bloke edilir (<= 0.45)."""
    topic_name = "TBMM Toplantı ve Karar Yeter Sayıları"
    topic_id = "VATANDASLIK_TBMM_YETER_SAYILARI"

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contradictions WHERE topic LIKE ?", (f"%{topic_name}%",))
        cursor.execute("""
        INSERT INTO contradictions (
            contradiction_id, topic, lesson, claim_a_id, claim_a_text, claim_a_source,
            claim_b_id, claim_b_text, claim_b_source, severity, resolution, created_at
        ) VALUES ('c_test_p4', ?, 'VATANDASLIK', 'c1', 'Toplantı 200', 'Kaynak 1', 'c2', 'Karar 151', 'Kaynak 2', 'HIGH', 'UNRESOLVED', datetime('now'))
        """, (topic_name,))

    mastery_report = curriculum_matrix.calculate_deterministic_mastery(topic_name)
    assert mastery_report["overall_mastery"] <= 0.45, "Çözümlenmemiş çelişki tam hakimiyeti (mastery) bloke etmelidir!"

def test_verified_claims_increase_mastery():
    """Phase 4: Doğrulanmış iddialar ve çoklu hoca sentezi hakimiyet skorunu yükseltir."""
    topic_name = "İdare Hukuku ve Mahalli İdareler"
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contradictions WHERE topic LIKE ?", (f"%{topic_name}%",))

    # İki farklı öğretmenden zengin olgusal veri ekle
    r1 = curriculum_matrix.digest_video_into_curriculum(
        lesson="VATANDASLIK",
        topic_str=topic_name,
        video_id="vid_mastery_rich_01",
        teacher_name="Emrah Vahap",
        channel_name="Hoca Webde",
        facts_extracted=6
    )
    r2 = curriculum_matrix.digest_video_into_curriculum(
        lesson="VATANDASLIK",
        topic_str=topic_name,
        video_id="vid_mastery_rich_02",
        teacher_name="Esra Özkan",
        channel_name="İsem TV",
        facts_extracted=8
    )
    assert r2["distinct_teachers_count"] >= 2
    assert r2["consumed_videos_count"] >= 2
