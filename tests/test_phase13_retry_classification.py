"""
KPSS Super-Brain: Phase 13 — Hata Sınıflandırması ve Dead-Letter Kuyruğu Testleri
Master Refactor Plan Phase 13 Kapsamı:
1. test_permanent_error_is_not_retried: 404, silinmiş veya özel videolar DEAD_LETTER'a aktarılır, yeniden denenmez.
2. test_transient_error_is_retried: Geçici ağ timeout'ları FAILED olup retry_count artırılır.
3. test_schema_violation_routes_to_dead_letter: Bozuk veri/şema ihlalleri doğrudan DEAD_LETTER kuyruğuna yönlendirilir.
"""
import pytest
from curriculum.queue import CurriculumQueue
from curriculum.models import QueueStatus, FailureClass
from brain.database import db_session

@pytest.fixture
def queue():
    return CurriculumQueue()

def test_permanent_error_is_not_retried(queue):
    """Phase 13: Kalıcı hata (video unavailable / 404) DEAD_LETTER'a gider, retry edilmez."""
    vid = "vid_perm_404"
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM video_queue WHERE video_id = ?", (vid,))
        cursor.execute("""
        INSERT INTO video_queue (video_id, url, title, channel, teacher_name, lesson, topic, status, retry_count, created_at)
        VALUES (?, 'https://youtube.com', 'Silinmiş Video', 'YouTube', 'Genel', 'GENEL', 'Genel', 'PROCESSING', 0, datetime('now'))
        """, (vid,))

    # Kalıcı hata ile mark_failed
    f_class = queue.mark_failed(vid, error_msg="HTTP Error 404: Not Found or Video Unavailable")
    assert f_class == FailureClass.PERMANENT

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, retry_count, error_message FROM video_queue WHERE video_id = ?", (vid,))
        row = cursor.fetchone()
        # Durum DEAD_LETTER olmalı ve retry_count 0 kalmalı (asla yeniden denenmez)
        assert row["status"] == "DEAD_LETTER"
        assert row["retry_count"] == 0
        assert "PERMANENT" in row["error_message"]

def test_transient_error_is_retried(queue):
    """Phase 13: Geçici hata (network timeout) FAILED işaretlenir ve retry_count artırılır."""
    vid = "vid_trans_01"
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM video_queue WHERE video_id = ?", (vid,))
        cursor.execute("""
        INSERT INTO video_queue (video_id, url, title, channel, teacher_name, lesson, topic, status, retry_count, created_at)
        VALUES (?, 'https://youtube.com', 'Geçici Timeout', 'YouTube', 'Genel', 'GENEL', 'Genel', 'PROCESSING', 0, datetime('now'))
        """, (vid,))

    f_class = queue.mark_failed(vid, error_msg="Connection timed out while waiting for YouTube gateway")
    assert f_class == FailureClass.TRANSIENT

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, retry_count FROM video_queue WHERE video_id = ?", (vid,))
        row = cursor.fetchone()
        assert row["status"] == "FAILED"
        assert row["retry_count"] == 1

def test_schema_violation_routes_to_dead_letter(queue):
    """Phase 13: Şema veya bozuk veri hataları derhal DEAD_LETTER'a yönlendirilir."""
    vid = "vid_schema_err"
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM video_queue WHERE video_id = ?", (vid,))
        cursor.execute("""
        INSERT INTO video_queue (video_id, url, title, channel, teacher_name, lesson, topic, status, retry_count, created_at)
        VALUES (?, 'https://youtube.com', 'Bozuk JSON', 'YouTube', 'Genel', 'GENEL', 'Genel', 'PROCESSING', 0, datetime('now'))
        """, (vid,))

    f_class = queue.mark_failed(vid, error_msg="JSONDecodeError: Corrupted transcript schema payload")
    assert f_class == FailureClass.SCHEMA_VIOLATION

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, retry_count FROM video_queue WHERE video_id = ?", (vid,))
        row = cursor.fetchone()
        assert row["status"] == "DEAD_LETTER"
        assert row["retry_count"] == 0
