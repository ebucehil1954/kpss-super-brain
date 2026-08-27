"""
KPSS Super-Brain: Birleşik Müfredat ve Araştırma Kuyruğu (Curriculum & Task Queue)
OpenManus otonom saha işçisi ile tam senkronize çalışan, SQLite kalıcı veritabanı destekli
akıllı araştırma ve video tüketim kuyruğu.
"""
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from brain.database import db_session
from curriculum.models import (
    ExamLevel,
    LessonType,
    QueueStatus,
    ResearchTask,
    VideoItem
)
from curriculum.engine import curriculum_engine


class CurriculumQueue:
    """
    Hem OpenManus araştırma görevlerini (ResearchTask) hem de keşfedilen
    YouTube videolarını öncelik sırasına göre yöneten birleşik kuyruk.
    """

    def __init__(self):
        self._memory_tasks: List[ResearchTask] = []

    # ==========================================
    # 1. OPENMANUS ARAŞTIRMA GÖREVLERİ (TASKS)
    # ==========================================

    def get_next_research_task(
        self,
        exam_level: ExamLevel = ExamLevel.ALL,
        lesson_filter: Optional[LessonType] = None
    ) -> Optional[ResearchTask]:
        """
        OpenManus saha işçisinin YouTube'da arayacağı sıradaki en değerli görevi döner.
        Kuyruk boşsa Eksiklik Radarı'ndan (Gap Radar) otomatik olarak 5 yeni görev üretir.
        """
        if not self._memory_tasks:
            fresh_tasks = curriculum_engine.generate_next_research_tasks(
                count=5,
                exam_level=exam_level,
                lesson_filter=lesson_filter
            )
            self._memory_tasks.extend(fresh_tasks)

        if self._memory_tasks:
            # En yüksek öncelikli görevi çek
            self._memory_tasks.sort(key=lambda t: t.priority, reverse=True)
            return self._memory_tasks.pop(0)

        return None

    def enqueue_task(self, task: ResearchTask) -> None:
        """Yeni bir özel araştırma görevini kuyruğa ekler."""
        self._memory_tasks.append(task)

    # ==========================================
    # 2. VİDEO TÜKETİM KUYRUĞU (VIDEOS)
    # ==========================================

    def enqueue_video(self, video: Dict[str, Any], priority: int = 10) -> bool:
        """Keşfedilen bir videoyu SQLite kuyruğuna ekler (zaten varsa yoksayar)."""
        video_id = video.get("video_id")
        if not video_id:
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
            ON CONFLICT(video_id) DO UPDATE SET
                priority = MAX(video_queue.priority, excluded.priority)
            """, (
                video_id,
                video.get("url", f"https://www.youtube.com/watch?v={video_id}"),
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

    def enqueue_video_batch(self, videos: List[Dict[str, Any]], priority: int = 10) -> int:
        """Toplu video ekler ve eklenen sayıyı döner."""
        added = 0
        for v in videos:
            if self.enqueue_video(v, priority=priority):
                added += 1
        return added

    def get_next_unwatched_video(self) -> Optional[Dict[str, Any]]:
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

    def mark_video_watched(
        self,
        video_id: str,
        transcript_length: int = 0,
        chunks_extracted: int = 0,
        lesson: Optional[str] = None,
        topic_name: Optional[str] = None,
        teacher_name: Optional[str] = None
    ) -> None:
        """Videoyu başarıyla izlendi olarak günceller ve topic_mastery tablosunu senkronize eder."""
        now_str = datetime.now().isoformat()
        with db_session() as conn:
            cursor = conn.cursor()
            # 1. Video durumunu WATCHED yap
            cursor.execute("""
            UPDATE video_queue
            SET status = 'WATCHED',
                transcript_length = ?,
                chunks_extracted = ?,
                watched_at = ?,
                error_message = NULL
            WHERE video_id = ?
            """, (transcript_length, chunks_extracted, now_str, video_id))

            # 2. Topic mastery tablosunda hoca ve video sayacını artır
            if topic_name:
                cursor.execute("""
                SELECT * FROM topic_mastery WHERE topic_name = ? OR topic_id LIKE ?
                LIMIT 1
                """, (topic_name, f"%{topic_name}%"))
                tm_row = cursor.fetchone()
                if tm_row:
                    tm = dict(tm_row)
                    v_ids = set(json.loads(tm.get("consumed_video_ids_json", "[]")))
                    v_ids.add(video_id)
                    teachers = set(json.loads(tm.get("distinct_teachers_json", "[]")))
                    if teacher_name and teacher_name != "Genel":
                        teachers.add(teacher_name)

                    count = len(v_ids)
                    target = tm.get("target_videos_count", 4)
                    stage = "UNSTARTED"
                    if count >= target:
                        stage = "MASTERED"
                    elif count >= 3:
                        stage = "SYNTHESIZING"
                    elif count >= 2:
                        stage = "DEVELOPING"
                    elif count >= 1:
                        stage = "STARTED"

                    cursor.execute("""
                    UPDATE topic_mastery
                    SET consumed_videos_count = ?,
                        distinct_teachers_json = ?,
                        consumed_video_ids_json = ?,
                        facts_count = facts_count + ?,
                        mastery_stage = ?,
                        is_mastered = ?,
                        last_digested_at = ?,
                        updated_at = ?
                    WHERE topic_id = ?
                    """, (
                        count,
                        json.dumps(list(teachers), ensure_ascii=False),
                        json.dumps(list(v_ids)),
                        chunks_extracted,
                        stage,
                        1 if count >= target else 0,
                        now_str,
                        now_str,
                        tm["topic_id"]
                    ))

    def mark_no_transcript(self, video_id: str, error_msg: str = "") -> None:
        """Altyazısı bulunamayan videoyu işaretler."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE video_queue
            SET status = 'NO_TRANSCRIPT',
                error_message = ?
            WHERE video_id = ?
            """, (error_msg, video_id))

    def mark_failed(self, video_id: str, error_msg: str = "") -> None:
        """Hata veren videoyu günceller ve yeniden deneme sayısını artırır."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE video_queue
            SET status = 'FAILED',
                retry_count = retry_count + 1,
                error_message = ?
            WHERE video_id = ?
            """, (error_msg, video_id))

    # ==========================================
    # 3. KUYRUK İSTATİSTİKLERİ VE DURUM RAPORU
    # ==========================================

    def get_queue_stats(self) -> Dict[str, Any]:
        """Kuyruktaki canlı video metriklerini döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT status, COUNT(*) as cnt
            FROM video_queue
            GROUP BY status
            """)
            rows = cursor.fetchall()
            status_map = {r["status"]: r["cnt"] for r in rows}

            cursor.execute("SELECT COUNT(*) as total FROM video_queue")
            total_vids = cursor.fetchone()["total"]

            cursor.execute("SELECT SUM(transcript_length) as total_words FROM video_queue WHERE status = 'WATCHED'")
            total_words = cursor.fetchone()["total_words"] or 0

        return {
            "total_videos": total_vids,
            "pending_videos": status_map.get("PENDING", 0),
            "processing_videos": status_map.get("PROCESSING", 0),
            "watched_videos": status_map.get("WATCHED", 0),
            "no_transcript_videos": status_map.get("NO_TRANSCRIPT", 0),
            "failed_videos": status_map.get("FAILED", 0),
            "total_transcript_words_digested": total_words,
            "cached_memory_tasks_count": len(self._memory_tasks)
        }


curriculum_queue = CurriculumQueue()
