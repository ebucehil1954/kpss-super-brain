"""
KPSS Super-Brain: Resmi Müfredat Konu Hakimiyet Matrisi ve Manus Keşif Testleri
"""
import pytest
import os
import sys

# Test klasöründen üst modüllere erişim
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from brain.database import initialize_database, db_session
from brain.curriculum_matrix import curriculum_matrix
from cognition.cross_teacher_analyzer import cross_teacher_analyzer
from senses.youtube_crawler_agent import youtube_crawler_agent
from cognition.self_tester import self_tester

def setup_module():
    """Test modülü öncesi veritabanını ilklendirir."""
    initialize_database()
    curriculum_matrix.initialize_mastery_matrix()

def test_official_curriculum_completeness():
    """Resmi ÖSYM müfredatının 5 ana dersi ve tüm kritik konuları kapsadığını test eder."""
    report = curriculum_matrix.get_curriculum_mastery_report()
    assert report["total_official_topics"] >= 35, "Resmi müfredat en az 35 ana konuyu içermelidir."
    
    lessons = report["by_lesson"]
    assert "TARIH" in lessons, "Tarih dersi eksik"
    assert "COGRAFYA" in lessons, "Coğrafya dersi eksik"
    assert "VATANDASLIK" in lessons, "Vatandaşlık dersi eksik"
    assert "TURKCE" in lessons, "Türkçe dersi eksik"
    assert "MATEMATIK" in lessons, "Matematik dersi eksik"

def test_video_consumption_rule_3_4_videos():
    """Bir konunun ancak en az 3-4 video tüketildiğinde uzman seviyesine ulaştığını test eder."""
    lesson = "VATANDASLIK"
    topic = "1982 Anayasası Yasama Organı ve Sayıları"

    # Test öncesi ilgili konuyu sıfırla
    matched_id = curriculum_matrix._find_matching_topic_id(lesson, topic)
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE topic_mastery 
        SET consumed_videos_count = 0, distinct_teachers_json = '[]', consumed_video_ids_json = '[]', is_mastered = 0, mastery_stage = 'UNSTARTED'
        WHERE topic_id = ?
        """, (matched_id,))

    # 1. Video: Ramazan Yetgin / Emrah Hoca
    res1 = curriculum_matrix.record_video_consumption(
        lesson=lesson, topic=topic, video_id="vid_test_001",
        teacher_name="Emrah Vahap Özkaraca", channel_name="İndeks Akademi",
        facts_extracted=5, traps_extracted=2
    )
    assert res1["consumed_videos_count"] >= 1
    assert not res1["is_mastered"], "1 video ile konu tamamlanmış sayılamaz!"

    # 2. Video: Erdal Kesekler
    res2 = curriculum_matrix.record_video_consumption(
        lesson=lesson, topic=topic, video_id="vid_test_002",
        teacher_name="Erdal Kesekler", channel_name="Benim Hocam",
        facts_extracted=4, traps_extracted=1
    )
    assert res2["consumed_videos_count"] >= 2
    assert not res2["is_mastered"], "2 video ile konu tamamlanmış sayılamaz!"

    # 3. Video: Esra Özkan
    res3 = curriculum_matrix.record_video_consumption(
        lesson=lesson, topic=topic, video_id="vid_test_003",
        teacher_name="Esra Özkan Karaoğlu", channel_name="İsem TV",
        facts_extracted=6, traps_extracted=3
    )
    assert res3["consumed_videos_count"] >= 3

    # 4. Video: Ali Koç
    res4 = curriculum_matrix.record_video_consumption(
        lesson=lesson, topic=topic, video_id="vid_test_004",
        teacher_name="Ali Koç", channel_name="Hoca Webde",
        facts_extracted=5, traps_extracted=2
    )
    assert res4["consumed_videos_count"] >= 4
    assert res4["distinct_teachers_count"] >= 3
    assert res4["is_mastered"], "4 farklı hoca videosu tüketildiğinde konu UZMAN seviyesine ulaşmalıdır!"

def test_cross_teacher_master_synthesis():
    """Çoklu hoca videolarından ortak olgular ve sınav tuzakları sentezinin yapıldığını test eder."""
    synth = cross_teacher_analyzer.synthesize_master_topic_profile(
        lesson="VATANDASLIK",
        topic="1982 Anayasası Yasama Organı ve Sayıları"
    )
    assert synth is not None
    assert synth["teachers_count"] >= 2
    assert "Emrah Vahap Özkaraca" in synth["teachers"]
    assert len(synth["master_summary"]) > 20

def test_manus_youtube_crawler_status():
    """Manus YouTube Keşif Ajanının durum sorgulamasını test eder."""
    status = youtube_crawler_agent.get_status()
    assert "is_scanning" in status
    assert "total_discovered_channels_playlists" in status

def test_self_tester_real_curriculum_health():
    """SelfTester'ın sahte puan yerine gerçek müfredat kapsamı raporladığını test eder."""
    health = self_tester.evaluate_knowledge_health()
    assert "curriculum_coverage_pct" in health
    assert "fully_mastered_count" in health
    assert "total_official_topics" in health
    assert health["total_official_topics"] >= 35
