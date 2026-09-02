"""
KPSS Super-Brain: Video Tüketim ve Kuyruk Yönetimi (Video Queue)
SQLite tabanlı, durum izlemeli ve önceliklendirmeli video izleme kuyruğu.
"""
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from brain.database import db_session
from curriculum.queue import is_valid_youtube_video_id

class VideoQueue:
    @classmethod
    def enqueue_video(cls, video: Dict[str, Any], priority: int = 10, strict_validation: bool = False) -> bool:
        """Yeni bir videoyu kuyruğa ekler (zaten varsa yoksayar)."""
        vid = (video.get("video_id") or "").strip()
        if not vid:
            return False
        if strict_validation and not is_valid_youtube_video_id(vid):
            return False

        now_str = datetime.now().isoformat()
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO video_queue (
                video_id, url, title, channel, teacher_name,
                lesson, topic, duration_seconds, status, priority,
                retry_count, transcript_length, chunks_extracted, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, 0, 0, 0, ?)
            ON CONFLICT(video_id) DO NOTHING
            """, (
                vid,
                video.get("url", f"https://www.youtube.com/watch?v={video['video_id']}"),
                video.get("title", "KPSS Dersi"),
                video.get("channel", "YouTube"),
                video.get("teacher_name", "Genel"),
                video.get("lesson", "GENEL"),
                video.get("topic", "Genel Konu"),
                video.get("duration_seconds", 0),
                priority,
                now_str
            ))
            return cursor.rowcount > 0

    @classmethod
    def enqueue_batch(cls, videos: List[Dict[str, Any]], priority: int = 10) -> int:
        """Toplu video ekler ve eklenen yeni video sayısını döner."""
        added = 0
        for v in videos:
            if cls.enqueue_video(v, priority=priority):
                added += 1
        return added

    @classmethod
    def get_next_unwatched(cls) -> Optional[Dict[str, Any]]:
        """Kuyruktan izlenecek sıradaki en öncelikli videoyu çeker ve 'PROCESSING' yapar."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM video_queue
            WHERE status = 'PENDING'
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
            """)
            row = cursor.fetchone()
            if not row:
                return None
            
            vid = row["video_id"]
            cursor.execute("UPDATE video_queue SET status = 'PROCESSING' WHERE video_id = ?", (vid,))
            return dict(row)

    @classmethod
    def mark_watched(cls, video_id: str, transcript_length: int, chunks_extracted: int):
        """Videoyu başarıyla izlendi olarak günceller."""
        now_str = datetime.now().isoformat()
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE video_queue
            SET status = 'WATCHED',
                transcript_length = ?,
                chunks_extracted = ?,
                watched_at = ?,
                error_message = NULL
            WHERE video_id = ?
            """, (transcript_length, chunks_extracted, now_str, video_id))

    @classmethod
    def mark_transcript_deferred(cls, video_id: str, error_msg: str = "", status: str = "TRANSCRIPT_DEFERRED"):
        """Altyazısı temin edilemeyen videoyu DEFERRED olarak işaretler."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE video_queue
            SET status = ?,
                error_message = ?
            WHERE video_id = ?
            """, (status, error_msg, video_id))

    @classmethod
    def mark_no_transcript(cls, video_id: str, error_msg: str = ""):
        """Altyazısı bulunamayan videoyu işaretler."""
        cls.mark_transcript_deferred(video_id, error_msg=error_msg, status="NO_TRANSCRIPT")

    @classmethod
    def mark_failed(cls, video_id: str, error_msg: str = ""):
        """Hata veren videoyu günceller ve yeniden deneme sayısını artırır."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE video_queue
            SET status = CASE WHEN retry_count >= 3 THEN 'FAILED' ELSE 'PENDING' END,
                retry_count = retry_count + 1,
                error_message = ?
            WHERE video_id = ?
            """, (error_msg, video_id))

    @classmethod
    def get_queue_summary(cls) -> Dict[str, Any]:
        """Kuyruk durum özetini döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) as count FROM video_queue GROUP BY status")
            status_counts = {r["status"]: r["count"] for r in cursor.fetchall()}
            
            cursor.execute("SELECT teacher_name, COUNT(*) as count FROM video_queue WHERE status = 'WATCHED' GROUP BY teacher_name")
            teacher_watched = {r["teacher_name"]: r["count"] for r in cursor.fetchall()}
            
            return {
                "status_counts": status_counts,
                "teacher_watched": teacher_watched,
                "total_in_queue": sum(status_counts.values())
            }

    @classmethod
    def get_total_count(cls) -> int:
        """Kuyruktaki toplam video sayısını döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM video_queue")
            row = cursor.fetchone()
            return row["total"] if row else 0

video_queue = VideoQueue()
