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
from curriculum.channel_scanner import channel_scanner
from openmanus_bridge import openmanus_bridge_client, ResearchResult, DiscoveredVideo
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
        [PHASE 6 & PHASE 7 DOĞRULANMIŞ KEŞİF KÖPRÜSÜ]
        OpenManus köprüsü ve ChannelScanner doğrulaması ile hedef hocaların ve kanalların
        videolarını arar, doğrular ve kuyruğa ekler.
        """
        discovered = []

        # 1. OpenManus Araştırma Köprüsü üzerinden yapılandırılmış arama yürüt
        try:
            bridge_result: ResearchResult = await openmanus_bridge_client.execute_research(task)
            for v in bridge_result.videos:
                v_dict = {
                    "video_id": v.video_id,
                    "url": v.url,
                    "title": v.title,
                    "channel": v.channel,
                    "teacher_name": v.teacher_name,
                    "lesson": task.lesson.value,
                    "topic": task.topic_name,
                    "duration_seconds": v.duration_seconds
                }
                # Hedef kanal kısıtı varsa doğrula
                if task.target_channels:
                    matched = False
                    for tch in task.target_channels:
                        if channel_scanner.filter_videos_by_channel([v_dict], tch):
                            matched = True
                            break
                    if not matched and not channel_scanner.verify_channel_identity(v.channel):
                        continue

                if curriculum_queue.enqueue_video(v_dict, priority=int(task.priority), strict_validation=True):
                    self.stats["videos_discovered"] += 1
                discovered.append(v_dict)
        except Exception as e:
            logger.warning(f"⚠️ [HARVESTER BRIDGE] Köprü araması hatası: {e}")

        # 2. Eğer köprüden sonuç gelmediyse ek yedek arama sorgularını channel_scanner ile süzerek tara
        if not discovered:
            from senses.youtube_api_client import youtube_api_client
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
            }
            queries = task.search_queries[:3]
            for query in queries:
                try:
                    entries = []
                    # 2A. Önce Resmi YouTube Data API v3 ile IP engelsiz ve hızlı ara
                    if youtube_api_client.is_available():
                        api_results = youtube_api_client.search_videos(query, max_results=max_per_query)
                        if api_results:
                            entries = [{
                                "id": r["video_id"],
                                "title": r["title"],
                                "duration": r.get("duration_seconds", 0),
                                "channel": r.get("channel", "YouTube")
                            } for r in api_results]

                    # 2B. Resmi API boş dönerse veya tanımlı değilse yt_dlp fallback
                    if not entries:
                        try:
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                res = ydl.extract_info(f"ytsearch{max_per_query}:{query}", download=False)
                                entries = res.get("entries", []) if res else []
                        except Exception as ydl_err:
                            logger.warning(f"yt_dlp arama hatası: {ydl_err}")
                            entries = []

                    for entry in entries:
                        if not entry:
                            continue
                        vid = entry.get("id")
                        title = entry.get("title", "")
                        if not vid or len(vid) != 11:
                            continue

                        duration = int(entry.get("duration", 0) or 0)
                        channel = entry.get("channel") or entry.get("uploader", "YouTube")

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

                        if task.target_channels:
                            filtered = []
                            for tch in task.target_channels:
                                filtered.extend(channel_scanner.filter_videos_by_channel([video_data], tch))
                            if not filtered:
                                continue

                        if curriculum_queue.enqueue_video(video_data, priority=int(task.priority), strict_validation=True):
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
            curriculum_queue.mark_discovery_failed(task.task_id, reason="NO_VIDEOS_FOUND_DURING_DISCOVERY")
            return {
                "status": "DISCOVERY_FAILED",
                "task_id": task.task_id,
                "message": "Kuyrukta izlenebilecek uygun video bulunamadı (DISCOVERY_FAILED kaydedildi)."
            }

        vid = video_to_process["video_id"]
        self.current_video_id = vid
        title = video_to_process.get("title", "")
        teacher = video_to_process.get("teacher_name", "Genel")
        lesson = video_to_process.get("lesson", task.lesson.value)
        topic = video_to_process.get("topic", task.topic_name)

        print(f"▶️ [VİDEO TÜKETİLİYOR] {vid} — '{title}' ({teacher})")

        # 3. Dayanıklı Transkript Çekimi (Transcript Gateway V1: 4 Kademeli Fallback)
        try:
            t_res = await transcript_fetcher.fetch_transcript_resilient(vid, enable_whisper_fallback=True)
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

                prov = t_res.get("provider", "UNKNOWN")
                print(f"  └─ ✅ BAŞARI [{prov}]: {words_count} kelime transkript ve {total_items} epistemik kayıt hafızaya mühürlendi.")
                self.current_video_id = None
                return {
                    "status": "success",
                    "task_id": task.task_id,
                    "video_id": vid,
                    "provider": prov,
                    "title": title,
                    "teacher": teacher,
                    "transcript_words": words_count,
                    "facts_count": extracted_facts,
                    "mnemonics_count": extracted_mnemonics,
                    "traps_count": extracted_traps,
                    "chunks_count": total_items
                }
            else:
                err = t_res.get("error", "Altyazı temin edilemedi.")
                status_val = t_res.get("status", "TRANSCRIPT_DEFERRED")
                print(f"  └─ ⚠️ Altyazı çekilemedi ({err}). {status_val} olarak işaretleniyor.")
                curriculum_queue.mark_transcript_deferred(vid, error_msg=err, status=status_val)
                self.stats["failed_attempts"] += 1
                self.current_video_id = None
                return {
                    "status": "transcript_deferred",
                    "task_id": task.task_id,
                    "video_id": vid,
                    "error": err,
                    "status_code": status_val
                }
        except Exception as task_err:
            # Şartname Kuralı 8: Tek bir video hatası asla işçiyi veya kuyruğu durduramaz
            print(f"  └─ ❌ [VİDEO HATASI İZOLE EDİLDİ] {vid}: {task_err}")
            curriculum_queue.mark_transcript_deferred(vid, error_msg=str(task_err), status="TRANSCRIPT_FAILED_TEMPORARY")
            self.stats["failed_attempts"] += 1
            self.current_video_id = None
            return {
                "status": "transcript_deferred",
                "task_id": task.task_id,
                "video_id": vid,
                "error": str(task_err),
                "status_code": "TRANSCRIPT_FAILED_TEMPORARY"
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
harvester = youtube_harvester
