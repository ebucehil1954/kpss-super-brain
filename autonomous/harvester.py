"""
KPSS Super-Brain: Otonom YouTube Karadeliği Motoru (YouTube Harvester)
Müfredat ve Eksiklik Radarı'ndan görev alarak YouTube'da otonom gezinen,
hedef hocaların videolarını keşfeden, transkript ve zaman damgalarını çekerek
bilgi ambarına aktaran saha işçisi (Harvester Worker).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from curriculum import (
    curriculum_queue,
    curriculum_engine,
    ExamLevel,
    LessonType,
    ResearchTask
)
from senses.transcript_fetcher import transcript_fetcher
from brain.database import db_session
import yt_dlp

logger = logging.getLogger("harvester")


class YouTubeHarvester:
    """
    Açık kaldığı her an YouTube'da KPSS ders videolarını yutan otonom karadelik.
    """

    def __init__(self):
        self.is_running: bool = False
        self.current_task: Optional[ResearchTask] = None
        self.current_video_id: Optional[str] = None
        self.stats = {
            "started_at": None,
            "tasks_processed": 0,
            "videos_discovered": 0,
            "transcripts_acquired": 0,
            "total_words_digested": 0,
            "failed_attempts": 0
        }

    async def search_and_enqueue_videos(self, task: ResearchTask, max_per_query: int = 4) -> List[Dict[str, Any]]:
        """
        Görevin arama sorguları üzerinden YouTube'da keşif yapar ve
        keşfedilen yeni videoları kuyruğa kaydeder.
        """
        discovered = []
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
        }

        # Öncelikli arama sorguları
        queries = task.search_queries[:3]
        for query in queries:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    res = ydl.extract_info(f"ytsearch{max_per_query}:{query}", download=False)
                    entries = res.get("entries", []) if res else []

                    for entry in entries:
                        if not entry:
                            continue
                        vid = entry.get("id")
                        title = entry.get("title", "")
                        if not vid or len(vid) != 11:
                            continue

                        duration = int(entry.get("duration", 0) or 0)
                        channel = entry.get("channel") or entry.get("uploader", "YouTube")

                        # Başlıktan hoca tahmin etmeye çalış
                        teacher = "Genel"
                        for target_t in task.target_teachers:
                            if target_t.lower() in title.lower():
                                teacher = target_t
                                break

                        video_data = {
                            "video_id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "title": title,
                            "channel": channel,
                            "teacher_name": teacher,
                            "lesson": task.lesson.value,
                            "topic": task.topic_name,
                            "duration_seconds": duration
                        }

                        # Kuyruğa ekle
                        if curriculum_queue.enqueue_video(video_data, priority=int(task.priority)):
                            self.stats["videos_discovered"] += 1
                        discovered.append(video_data)

            except Exception as e:
                logger.warning(f"⚠️ [HARVESTER] Arama hatası ('{query}'): {e}")

        return discovered

    async def harvest_single_task(
        self,
        exam_level: ExamLevel = ExamLevel.ALL,
        lesson_filter: Optional[LessonType] = None
    ) -> Dict[str, Any]:
        """
        Müfredat kuyruğundan sıradaki bir görevi çeker:
        1. YouTube'da videoları arar ve kuyruğa ekler.
        2. En uygun videonun transkriptini çeker.
        3. Konu hakimiyetini (topic_mastery) günceller.
        """
        task = curriculum_queue.get_next_research_task(
            exam_level=exam_level,
            lesson_filter=lesson_filter
        )
        if not task:
            return {"status": "idle", "message": "İşlenecek araştırma görevi bulunamadı."}

        self.current_task = task
        print("=" * 70)
        print(f"🕳️ [KARADELİK SAHA İŞÇİSİ] Görev Alındı: [{task.lesson.value}] {task.topic_name}")
        print(f"🎯 Hedef Hocalar: {', '.join(task.target_teachers)}")
        print(f"🔎 Öncelikli Arama: '{task.search_queries[0]}'")
        print("=" * 70)

        # 1. YouTube Keşfi ve Kuyruğa Alma
        discovered = await self.search_and_enqueue_videos(task)
        print(f"  └─ 🌐 Keşif Tamamlandı: {len(discovered)} adet aday video bulundu.")

        # 2. Kuyruktan izlenecek sıradaki videoyu çek
        video_to_process = curriculum_queue.get_next_unwatched_video()
        if not video_to_process:
            return {
                "status": "warning",
                "task_id": task.task_id,
                "message": "Kuyrukta izlenebilecek uygun video bulunamadı."
            }

        vid = video_to_process["video_id"]
        self.current_video_id = vid
        title = video_to_process.get("title", "")
        teacher = video_to_process.get("teacher_name", "Genel")
        lesson = video_to_process.get("lesson", task.lesson.value)
        topic = video_to_process.get("topic", task.topic_name)

        print(f"▶️ [VİDEO TÜKETİLİYOR] {vid} — '{title}' ({teacher})")

        # 3. Dayanıklı Transkript Çekimi
        t_res = await transcript_fetcher.fetch_transcript_resilient(vid, enable_whisper_fallback=False)
        full_text = t_res.get("text", "")

        if t_res.get("success") and full_text:
            words_count = len(full_text.split())
            # 4. Bilişsel Analiz (Hoca Zihni, Şifreler, Tuzaklar ve Atomik İddialar)
            from cognition.analyst import cognitive_analyst
            analysis_res = await cognitive_analyst.analyze_transcript(
                transcript=full_text,
                teacher_name=teacher,
                lesson=lesson,
                topic=topic,
                video_id=vid,
                video_title=title,
                channel=video_to_process.get("channel", "YouTube"),
                segments=t_res.get("segments")
            )
            extracted_facts = analysis_res.get("facts_count", 0)
            extracted_mnemonics = analysis_res.get("mnemonics_count", 0)
            extracted_traps = analysis_res.get("traps_count", 0)
            total_items = max(1, extracted_facts + extracted_mnemonics + extracted_traps)

            curriculum_queue.mark_video_watched(
                video_id=vid,
                transcript_length=words_count,
                chunks_extracted=total_items,
                lesson=lesson,
                topic_name=topic,
                teacher_name=teacher
            )

            self.stats["transcripts_acquired"] += 1
            self.stats["total_words_digested"] += words_count
            self.stats["tasks_processed"] += 1

            # Öğrenme günlüğüne kaydet
            self._log_learning_event(
                lesson=lesson,
                topic=topic,
                teacher=teacher,
                summary=f"'{title}' videosundan {words_count} kelime ve {total_items} bilgi (Şifre: {extracted_mnemonics}, Tuzak: {extracted_traps}) hafızaya aktarıldı.",
                details={
                    "video_id": vid,
                    "words_count": words_count,
                    "facts_count": extracted_facts,
                    "mnemonics_count": extracted_mnemonics,
                    "traps_count": extracted_traps
                }
            )

            print(f"  └─ ✅ BAŞARI: {words_count} kelime transkript ve {total_items} epistemik kayıt hafızaya mühürlendi.")
            self.current_video_id = None
            return {
                "status": "success",
                "task_id": task.task_id,
                "video_id": vid,
                "title": title,
                "teacher": teacher,
                "transcript_words": words_count,
                "facts_count": extracted_facts,
                "mnemonics_count": extracted_mnemonics,
                "traps_count": extracted_traps,
                "chunks_count": total_items
            }
        else:
            err = t_res.get("error", "Altyazı bulunamadı.")
            print(f"  └─ ⚠️ Altyazı çekilemedi ({err}). NO_TRANSCRIPT olarak işaretleniyor.")
            curriculum_queue.mark_no_transcript(vid, error_msg=err)
            self.stats["failed_attempts"] += 1
            self.current_video_id = None
            return {
                "status": "no_transcript",
                "task_id": task.task_id,
                "video_id": vid,
                "error": err
            }

    async def start_continuous_harvest(
        self,
        sleep_between_tasks: int = 5,
        exam_level: ExamLevel = ExamLevel.ALL
    ):
        """
        7/24 Kesintisiz Karadelik Döngüsü:
        Açık kaldığı her an müfredat kuyruğundan beslenerek YouTube'u tarar ve tüketir.
        """
        self.is_running = True
        self.stats["started_at"] = datetime.now().isoformat()
        print("\n" + "=" * 70)
        print("🌌 [KPSS SÜPER ZEKA] 7/24 OTONOM YOUTUBE KARADELİĞİ BAŞLATILDI")
        print("   Açık kaldığı sürece YouTube'daki dersleri yutmaya devam edecektir.")
        print("=" * 70 + "\n")

        try:
            while self.is_running:
                try:
                    res = await self.harvest_single_task(exam_level=exam_level)
                    if res.get("status") == "idle":
                        print("💤 [BEKLEMEDE] İşlenecek görev yok. 15 saniye dinleniliyor...")
                        await asyncio.sleep(15)
                    else:
                        await asyncio.sleep(sleep_between_tasks)
                except Exception as e:
                    print(f"❌ [KARADELİK DÖNGÜ HATASI]: {e}")
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("🛑 [KARADELİK] Görev durduruldu.")
        finally:
            self.is_running = False

    def stop(self):
        """Karadelik motorunu durdurur."""
        print("🛑 [KARADELİK] Durdurma sinyali gönderildi...")
        self.is_running = False

    def get_status(self) -> Dict[str, Any]:
        """Motorun canlı çalışma durumunu döner."""
        return {
            "is_running": self.is_running,
            "current_task": self.current_task.model_dump() if self.current_task else None,
            "current_video_id": self.current_video_id,
            "stats": self.stats
        }

    @staticmethod
    def _log_learning_event(lesson: str, topic: str, teacher: str, summary: str, details: Dict[str, Any]):
        """Epizodik hafıza günlüğüne olayı kaydeder."""
        now_str = datetime.now().isoformat()
        event_id = f"EVT_{int(datetime.now().timestamp() * 1000)}"
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO learning_events (
                event_id, event_type, lesson, topic, teacher,
                summary, confidence_gain, details_json, created_at
            ) VALUES (?, 'VIDEO_DIGEST', ?, ?, ?, ?, 0.05, ?, ?)
            """, (
                event_id,
                lesson,
                topic,
                teacher,
                summary,
                json.dumps(details, ensure_ascii=False),
                now_str
            ))


youtube_harvester = YouTubeHarvester()
