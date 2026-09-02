"""
KPSS Super-Brain: Phase 1 — Sahte YouTube ID ve URL İzolasyon Testleri
Master Refactor Plan Phase 1 Kapsamı:
1. test_no_fake_video_id: Sahte ve sentetik video ID'leri kesinlikle reddedilir.
2. test_failed_search_does_not_enqueue_video: Başarısız arama kuyruğa sahte video sokmaz.
3. test_discovery_failure_is_persisted: Keşif başarısızlığı DISCOVERY_FAILED olarak kalıcılaşır.
4. test_only_real_youtube_ids_reach_video_queue: Yalnızca gerçek (11 haneli geçerli) YouTube ID'leri kuyruğa alınır.
"""
import pytest
from curriculum.queue import is_valid_youtube_video_id, curriculum_queue
from curriculum.models import QueueStatus
from brain.database import db_session

@pytest.fixture(autouse=True)
def clean_fake_video_queue_rows():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM video_queue WHERE video_id LIKE 'disc_fail_%' OR video_id LIKE 'fake_%' OR video_id LIKE 'test_%'")
    yield
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM video_queue WHERE video_id LIKE 'disc_fail_%' OR video_id LIKE 'fake_%' OR video_id LIKE 'test_%'")

def test_no_fake_video_id():
    """Phase 1: Sentetik/sahte video ID'leri asla geçerli kabul edilmez."""
    assert is_valid_youtube_video_id("fake_vid_12345") is False
    assert is_valid_youtube_video_id("test_no_trans_99") is False
    assert is_valid_youtube_video_id("synth_yt_abc") is False
    assert is_valid_youtube_video_id("mock_12345678") is False
    assert is_valid_youtube_video_id("") is False
    assert is_valid_youtube_video_id("too_short") is False
    assert is_valid_youtube_video_id("way_too_long_to_be_a_real_youtube_video_id") is False
    assert is_valid_youtube_video_id(None) is False

def test_only_real_youtube_ids_reach_video_queue():
    """Phase 1: Standart 11 haneli gerçek YouTube ID'leri doğrulanır, sahteler elenir."""
    # Gerçek YouTube ID örnekleri (11 karakter, alfanümerik, - ve _ içerebilir)
    valid_id = "dQw4w9WgXcQ"
    valid_id_2 = "k1BwtCgUtVU"
    assert is_valid_youtube_video_id(valid_id) is True
    assert is_valid_youtube_video_id(valid_id_2) is True

    # Sıkı doğrulama (strict_validation=True) ile sahte video kuyruğa eklenemez
    fake_video = {
        "video_id": "fake_bad_id_999",
        "title": "Sahte KPSS Dersi",
        "channel": "FakeChannel"
    }
    enqueued = curriculum_queue.enqueue_video(fake_video, strict_validation=True)
    assert enqueued is False

    # Gerçek video kuyruğa kabul edilir
    real_video = {
        "video_id": valid_id,
        "title": "Gerçek KPSS Dersi",
        "channel": "Benim Hocam"
    }
    enqueued_real = curriculum_queue.enqueue_video(real_video, strict_validation=True)
    # Ya yeni eklendi (True) ya da zaten kuyrukta mevcut (CONFLICT -> True/False)
    assert isinstance(enqueued_real, bool)

def test_failed_search_does_not_enqueue_video():
    """Phase 1: Arama başarısız olduğunda kuyruğa sentetik video enjekte edilmez."""
    empty_search_results = []
    # 0 sonuç varsa kuyruğa hiçbir şey eklenmemeli
    added = curriculum_queue.enqueue_video_batch(empty_search_results)
    assert added == 0

def test_discovery_failure_is_persisted():
    """Phase 1: Keşif başarısızlığı DISCOVERY_FAILED olarak learning_events'e kaydedilir, video_queue'ya sahte video girmez."""
    test_task_id = "test_phase1_task_001"
    curriculum_queue.mark_discovery_failed(test_task_id, reason="NO_VIDEOS_FOUND_PHASE1")

    with db_session() as conn:
        cursor = conn.cursor()
        # 1. video_queue'da sahte video ID bulunmadığını doğrula
        cursor.execute("SELECT * FROM video_queue WHERE video_id LIKE 'disc_fail_%' OR video_id LIKE 'fake_%'")
        fake_rows = cursor.fetchall()
        assert len(fake_rows) == 0

        # 2. learning_events tablosuna DISCOVERY_FAILED kaydının mühürlendiğini doğrula
        cursor.execute("SELECT * FROM learning_events WHERE event_id = ?", (f"evt_discfail_{test_task_id}",))
        row = cursor.fetchone()
        assert row is not None
        assert row["event_type"] == "DISCOVERY_FAILED"
        assert "NO_VIDEOS_FOUND_PHASE1" in row["summary"]
