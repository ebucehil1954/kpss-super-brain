"""
KPSS Super-Brain: Açgözlü, Bilinçli ve Dayanıklı Otonom Öğrenme Motoru (Hungry Engine v5)
"Yüzeysel öğrenme yok: Her resmi konu başlığı için en az 3-4 farklı hocanın ders videosunu
tüketen, Manus tarzı YouTube keşfi yapan ve çoklu hoca sentezi üreten KPSS Profesörü Zihni."
"""
import sys
import os
import asyncio
import json
import time
import random
import signal
from datetime import datetime
from typing import Dict, Any, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import super_brain_config
from autonomous.priority_queue import priority_queue
from autonomous.stats_tracker import stats_tracker
from autonomous.state_persistence import state_persistence
from autonomous.consciousness import consciousness
from autonomous.worker_coordinator import worker_coordinator
from senses.youtube_crawler_agent import youtube_crawler_agent
from senses.video_crawler import video_crawler
from senses.video_queue import video_queue
from senses.transcript_fetcher import transcript_fetcher
from senses.transcript_processor import transcript_processor
from senses.web_researcher import web_researcher
from cognition.teacher_learner import teacher_learner
from cognition.self_tester import self_tester
from cognition.cross_teacher_analyzer import cross_teacher_analyzer
from brain.exporter import data_exporter
from brain.knowledge_store import knowledge_store
from brain.episodic_memory import episodic_memory
from brain.deep_ontology import deep_ontology
from brain.curriculum_matrix import curriculum_matrix

class HungryEngine:
    def __init__(self):
        self.is_running = False
        self.stats = {
            "started_at": None,
            "total_cycles": 0,
            "items_consumed": 0,
            "mastered_topics_count": 0,
            "facts_stored": 0,
            "traps_stored": 0,
            "syntheses_generated": 0,
            "workers_active": 0
        }

    async def start(self):
        """Açgözlü motoru başlatır, önceki durumu yükler ve paralel hatları ayağa kaldırır."""
        self.is_running = True
        self.stats["started_at"] = datetime.now().isoformat()
        session_id = state_persistence.record_session_start()

        # Veritabanı müfredat matrisini eşitle
        curriculum_matrix.initialize_mastery_matrix()

        print("=" * 75)
        print("🧠 [HUNGRY ENGINE v5] KPSS OTONOM BİLİNÇLİ SÜPER ZEKA BAŞLATILDI")
        print("=" * 75)
        print(f"⚡ Mod: MANUS YOUTUBE KEŞİF & 3-4 VİDEO RESMİ MÜFREDAT DERİNLEŞTİRME (Oturum: {session_id})")
        print(f"📍 Ana Model: {super_brain_config.MAIN_MODEL} | Muhakeme: {super_brain_config.REASONING_MODEL}")
        print(f"📍 Donanım / GPU: {'CUDA Aktif' if super_brain_config.WHISPER_DEVICE == 'cuda' else 'Otomatik/CPU'}")
        print(f"📍 Veritabanı: {super_brain_config.BRAIN_DB_FILE}")
        print("=" * 75)

        # 1. State Persistence: Zombi görevleri kurtar ve önceki durumu yükle
        recovered = state_persistence.recover_zombie_tasks()
        if recovered > 0:
            print(f"🔄 [CHECKPOINT KURTARMA] Önceki oturumdan yarım kalan {recovered} görev başarıyla kurtarıldı.")

        checkpoint = state_persistence.load_checkpoint()
        if checkpoint:
            saved_stats = checkpoint.get("engine_stats", {})
            self.stats["items_consumed"] = saved_stats.get("items_consumed", 0)
            self.stats["facts_stored"] = saved_stats.get("facts_stored", 0)
            self.stats["traps_stored"] = saved_stats.get("traps_stored", 0)
            self.stats["syntheses_generated"] = saved_stats.get("syntheses_generated", 0)
            print(f"💾 [KALDIĞI YERDEN DEVAM] Toplam {self.stats['items_consumed']} video tüketildi, {self.stats['facts_stored']} bilgi hafızada.")

        # 2. Bilinç Motoru: İlk stratejik deliberasyonu yap
        initial_plan = consciousness.deliberate_next_step()
        print(f"🧭 [İLK STRATEJİK ODAK] Hedef: {initial_plan.get('target_lesson')} — {initial_plan.get('target_topic')}")
        print(f"   └─ Gerekçe (CoT): {initial_plan.get('chain_of_thought', [''])[0]}")

        # 3. Öncelik hedeflerini besle
        await self._seed_curriculum_targets()

        # 4. Paralel Asenkron Hatları Başlat
        try:
            await asyncio.gather(
                self._manus_youtube_discovery_loop(),
                self._digestion_worker(worker_id=1),
                self._digestion_worker(worker_id=2),
                self._expert_synthesis_loop(),
                self._continuous_self_eval_and_repair(),
                self._periodic_consolidation_and_exports(),
                self._periodic_checkpoint_loop()
            )
        except asyncio.CancelledError:
            print("\n🛑 [HUNGRY ENGINE] Görevler iptal edildi. Güvenle kapanıyor...")
        finally:
            await self._safe_shutdown()

    async def stop(self):
        """Motoru durdurur."""
        print("🛑 [HUNGRY ENGINE] Durdurma sinyali alındı...")
        self.is_running = False

    async def _seed_curriculum_targets(self):
        """Başlangıçta müfredatta video eksiği olan konuları öncelik kuyruğuna doldurur."""
        print("🎯 [HEDEF BELİRLEME] Resmi ÖSYM KPSS Müfredatı ve 3-4 Video İhtiyaçları Kuyruğa Ekleniyor...")
        needed = curriculum_matrix.get_topics_needing_videos(max_topics=10)
        for item in needed:
            lesson = item["lesson"]
            topic = item["topic_name"]
            needed_count = item["needed_videos_count"]
            
            priority_queue.enqueue(
                source_type="YOUTUBE",
                lesson=lesson,
                topic=topic,
                payload={"query": f"KPSS {lesson} {topic} konu anlatımı", "teacher": "Çoklu Hoca"},
                base_priority=needed_count * 25.0
            )
        print(f"  └─ 🚀 Toplam {priority_queue.size()} adet yüksek öncelikli müfredat hedefi kuyrukta.")

    async def _sleep_interruptible(self, seconds: int):
        """Durdurma sinyalini hızlıca algılayarak verimli bekler."""
        step = 5
        elapsed = 0
        while self.is_running and elapsed < seconds:
            to_sleep = min(step, seconds - elapsed)
            await asyncio.sleep(to_sleep)
            elapsed += to_sleep

    async def _manus_youtube_discovery_loop(self):
        """Arka planda sürekli Manus tarzı YouTube keşfi yaparak tüm popüler kaynakları ve hocaları tarar."""
        while self.is_running:
            try:
                print("🕵️‍♂️ [MANUS RADAR DÖNGÜSÜ] YouTube oynatma listeleri ve eksik konular taranıyor...")
                res = await youtube_crawler_agent.run_manus_style_deep_discovery(force_all_topics=False)
                print(f"  └─ 🌐 Keşif Sonucu: +{res.get('videos_queued', 0)} yeni video kuyruğa eklendi.")

                # 30 dakikada bir derin keşfi tekrarla
                await self._sleep_interruptible(1800)
            except Exception as e:
                print(f"⚠️ [MANUS KEŞİF DÖNGÜSÜ HATASI]: {e}")
                await self._sleep_interruptible(15)

    async def _digestion_worker(self, worker_id: int):
        """Açgözlü sindirici: Kuyruktan video çeker, transkriptini çıkarır ve zihne işler."""
        worker_name = f"worker_{worker_id}"
        print(f"🍽️ [SİNDİRİCİ #{worker_id}] Bilinçli video tüketici işçi aktif edildi.")
        while self.is_running:
            try:
                task = priority_queue.dequeue()
                if not task:
                    next_vid = video_queue.get_next_unwatched()
                    if next_vid:
                        task = {
                            "source_type": "YOUTUBE",
                            "lesson": next_vid.get("lesson", "GENEL"),
                            "topic": next_vid.get("topic", "Genel"),
                            "payload": next_vid
                        }

                if not task:
                    await asyncio.sleep(3)
                    continue

                source_type = task.get("source_type")
                lesson = task.get("lesson", "GENEL")
                topic = task.get("topic", "Genel")
                payload = task.get("payload", {})

                task_key = f"{source_type}_{payload.get('video_id', topic)}"
                # Görev Kilidi Al (Çakışmayı önle)
                has_lock = await worker_coordinator.acquire_task_lock(task_key, worker_name)
                if not has_lock:
                    await asyncio.sleep(1)
                    continue

                try:
                    print(f"🍴 [SİNDİRİCİ #{worker_id} TÜKETİYOR] [{source_type}] {lesson} — {topic}")
                    if source_type == "YOUTUBE":
                        await self._digest_youtube_video(payload, lesson, topic)
                    elif source_type == "WEB_ACADEMIC":
                        await self._digest_web_research(topic, lesson)

                    self.stats["items_consumed"] += 1
                finally:
                    await worker_coordinator.release_task_lock(task_key, worker_name)

                # Rate limit ve IP koruması için kısa nefes alma
                await asyncio.sleep(random.randint(super_brain_config.VIDEO_DIGEST_SLEEP_MIN_SEC, super_brain_config.VIDEO_DIGEST_SLEEP_MAX_SEC))

            except Exception as e:
                print(f"❌ [SİNDİRME HATASI #{worker_id}]: {e}")
                await asyncio.sleep(4)

    async def _digest_youtube_video(self, payload: Dict[str, Any], lesson: str, topic: str):
        """Bir YouTube dersini IP engeline dayanıklı (Proxy / GPU Whisper) şekilde transkribe edip zihne işler."""
        video_id = payload.get("video_id")
        teacher = payload.get("teacher_name", "Genel")
        title = payload.get("title", "KPSS Dersi")

        if not video_id:
            return

        # 6 Katmanlı Dayanıklı Transkript Çekimi (IP Engeli Savunması)
        t_res = await transcript_fetcher.fetch_transcript_resilient(video_id, enable_whisper_fallback=True)
        full_text = t_res.get("text", "")

        if not t_res.get("success") or not full_text:
            # Kesin Hata Semantiği: Sahte veriyle doldurma, açıkça NO_TRANSCRIPT olarak işaretle
            print(f"⚠️ [TRANSCRIPT BULUNAMADI] {video_id} ({teacher}) - TRANSCRIPT_UNAVAILABLE.")
            video_queue.mark_no_transcript(video_id, error_msg=t_res.get("error", "Transkript bulunamadı."))
            return

        proc_result = await transcript_processor.process_video_transcript(
            video_id=video_id,
            title=title,
            teacher_name=teacher,
            lesson=lesson,
            topic=topic,
            full_transcript=full_text,
            segments=t_res.get("segments", [])
        )

        teacher_learner.update_profile_from_lecture(
            teacher_name=teacher,
            lesson=lesson,
            topic=topic,
            transcript_words_count=len(full_text.split()),
            facts_count=proc_result.get("facts_extracted", 0),
            mnemonics_count=proc_result.get("mnemonics_extracted", 0),
            reasoning_count=proc_result.get("reasoning_extracted", 0),
            traps_count=proc_result.get("traps_extracted", 0)
        )

        video_queue.mark_watched(
            video_id=video_id,
            transcript_length=len(full_text.split()),
            chunks_extracted=proc_result.get("facts_extracted", 0)
        )
        self.stats["facts_stored"] += proc_result.get("facts_extracted", 0)
        self.stats["traps_stored"] += proc_result.get("traps_extracted", 0)

    async def _digest_web_research(self, topic: str, lesson: str):
        """Akademik web ve mevzuat kaynaklarını sindirir."""
        research_data = await web_researcher.deep_research_and_ingest(topic, lesson)
        news_items = research_data.get("sources", [])
        if news_items:
            for s in news_items:
                knowledge_store.stage_pending_record(
                    text=s.get("summary", ""),
                    record_type="FACT",
                    lesson=lesson,
                    topic=topic,
                    confidence=0.95,
                    source={"type": "web_academic", "title": s.get("title", ""), "url": s.get("url", "")},
                    tags=["web_academic", "staged"]
                )
                self.stats["facts_stored"] += 1

    async def _expert_synthesis_loop(self):
        """En az 3-4 video tüketilmiş konuların periyodik olarak çapraz hoca sentezini yapar."""
        while self.is_running:
            try:
                await asyncio.sleep(120)
                report = curriculum_matrix.get_curriculum_mastery_report()
                for t in report.get("topics", []):
                    if t.get("consumed_videos_count", 0) >= 3:
                        cross_teacher_analyzer.synthesize_master_topic_profile(t["lesson"], t["topic_name"])
                        self.stats["syntheses_generated"] += 1
            except Exception as e:
                print(f"⚠️ [UZMAN SENTEZ DÖNGÜSÜ HATASI]: {e}")

    async def evaluate_and_trigger(self) -> Dict[str, Any]:
        """
        Müfredat skoru < 0.85 olan konular için otonom OpenManus araştırma ajanını ve anti-halüsinasyon hattını tetikler.
        """
        from ingestion.live_researcher import openmanus_agent
        from anti_hallucination.fact_checker import fact_checker
        from brain.knowledge_graph import kpss_knowledge_graph
        from brain.curriculum_matrix import curriculum_matrix

        scores = curriculum_matrix.get_scores()
        triggered_count = 0
        elevated_count = 0

        for topic_id, score in scores.items():
            if score < 0.85:
                triggered_count += 1
                # 1. OpenManus Ajanı Araştırır (senkron çağrıyı async thread'e taşı)
                research_result = await asyncio.to_thread(openmanus_agent.run_research_cycle, topic_id, "")
                
                # 2. Anti-Hallucination Hattı Denetler (senkron çağrıyı async thread'e taşı)
                is_verified = await asyncio.to_thread(fact_checker.validate, topic_id, research_result.get("text", ""))
                
                # 3. Başarılıysa Knowledge Graph'e İşlenir ve Skor Yükseltilir
                if is_verified.get("passed"):
                    kpss_knowledge_graph.add_triplets(is_verified.get("verified_triplets", []))
                    curriculum_matrix.update_score(topic_id, 0.98)
                    elevated_count += 1
                    break # Bir döngüde en kritik konuyu güncelle

        return {
            "triggered_count": triggered_count,
            "elevated_count": elevated_count,
            "status": "success"
        }

    async def _continuous_self_eval_and_repair(self):
        """Düzenli olarak zeka sağlığını ölçer ve eksikleri onarır."""
        while self.is_running:
            try:
                await asyncio.sleep(180)
                health = self_tester.evaluate_knowledge_health()
                repaired = await self_tester.auto_repair_gaps()
                # Otonom OpenManus & Anti-Hallucination tetikle
                await self.evaluate_and_trigger()
                # Bilinçli planı tazele
                consciousness.deliberate_next_step()
                print(f"📊 [MÜFREDAT DURUMU] Kapsam: %{health['curriculum_coverage_pct']} ({health['status']}) | Tamamlanan Konu: {health['fully_mastered_count']}/{health['total_official_topics']} | Kuyruğa Eklenen Video: +{repaired}")
            except Exception as e:
                print(f"⚠️ [ÖZ-DEĞERLENDİRME HATASI]: {e}")

    async def _periodic_consolidation_and_exports(self):
        """Zihin ambarını periyodik olarak konsolide edip temiz JSON'lara döker."""
        while self.is_running:
            try:
                await asyncio.sleep(300)
                files = data_exporter.export_all()
                self._update_live_markdown_report()
            except Exception as e:
                print(f"⚠️ [KONSOLİDASYON HATASI]: {e}")

    async def _periodic_checkpoint_loop(self):
        """Her 30 saniyede motor durumunu SQLite Checkpoint DB'ye kaydeder."""
        while self.is_running:
            try:
                await asyncio.sleep(super_brain_config.AUTO_CHECKPOINT_INTERVAL_SEC)
                state_persistence.save_checkpoint({
                    "engine_stats": self.stats,
                    "priority_queue_size": priority_queue.size(),
                    "video_queue_size": video_queue.get_total_count(),
                    "consciousness": consciousness.get_current_consciousness_state(),
                    "curriculum_mastery": curriculum_matrix.get_curriculum_mastery_report(),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"⚠️ [CHECKPOINT HATASI]: {e}")

    def _update_live_markdown_report(self):
        filepath = os.path.join(super_brain_config.OUTPUTS_DIR, "latest_summary.md")
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        health = self_tester.evaluate_knowledge_health()
        stats_info = knowledge_store.get_stats()
        c_state = consciousness.get_current_consciousness_state()
        m_report = curriculum_matrix.get_curriculum_mastery_report()

        md = f"# 🧠 Promius KPSS Super-Brain v5 — Canlı Zeka & Müfredat Raporu\n"
        md += f"**Son Güncelleme:** `{now_str}` | **Mod:** `MANUS YOUTUBE KEŞFİ & ÇOKLU HOCA SENTEZİ`\n\n---\n\n"
        md += f"## 🧭 1. Bilinç ve Düşünce Durumu (Metacognition)\n"
        if c_state.get("active_focus"):
            foc = c_state["active_focus"]
            md += f"- **Aktif Odak:** `{foc.get('target_lesson')}` — `{foc.get('target_topic')}`\n"
            md += f"- **Pedagojik Eğitmen:** `{foc.get('recommended_teacher')}`\n"
            md += f"- **Akıl Yürütme Gerekçesi (CoT):**\n"
            for step in foc.get("chain_of_thought", []):
                md += f"  - {step}\n"
        md += f"\n---\n\n"
        md += f"## 📊 2. Resmi Müfredat Konu Hakimiyet Matrisi (En Az 3-4 Video Şartı)\n"
        md += f"- **Müfredat Kapsam Skoru:** `%{m_report.get('mastery_percentage', 0)}` ({health.get('status')})\n"
        md += f"- **Tamamlanan Konular (>= 4 Video):** `{m_report.get('fully_mastered_count', 0)}` / `{m_report.get('total_official_topics', 0)}`\n"
        md += f"- **Sentez Aşaması (3 Video):** `{m_report.get('synthesizing_count', 0)}` konu\n"
        md += f"- **Devam Eden Konular (1-2 Video):** `{m_report.get('in_progress_count', 0)}` konu\n"
        md += f"- **Henüz Başlanmamış Konular:** `{m_report.get('unstarted_count', 0)}` konu\n"
        md += f"- **Toplam Kayıtlı Bilgi:** `{stats_info.get('total_records', 0)}` parçacık\n"
        md += f"- **Tüketilen Ders Videosu:** `{self.stats['items_consumed']}` adet\n\n---\n\n"
        md += f"## 📚 3. Ders Bazlı Konu Durumu\n"
        for ls, st in m_report.get("by_lesson", {}).items():
            md += f"- **{ls}:** {st['mastered']}/{st['total']} Konu Uzman Seviyesinde ({st['videos_consumed']} video tüketildi)\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

    async def _safe_shutdown(self):
        """Kapanışta tüm durumu kaydeder ve oturumu mühürler."""
        print("💾 [HUNGRY ENGINE] Nihai durum mühürleniyor ve konsolide ediliyor...")
        state_persistence.save_checkpoint({
            "engine_stats": self.stats,
            "priority_queue_size": priority_queue.size(),
            "video_queue_size": video_queue.get_total_count(),
            "consciousness": consciousness.get_current_consciousness_state(),
            "curriculum_mastery": curriculum_matrix.get_curriculum_mastery_report(),
            "timestamp": datetime.now().isoformat()
        })
        state_persistence.record_session_stop(reason="GRACEFUL_STOP", stats=self.stats)
        data_exporter.export_all()
        self._update_live_markdown_report()
        print("👋 KPSS Super-Brain Hungry Engine v5 güvenle kapatıldı. Bir sonraki açılışta tam buradan devam edecek.")

hungry_engine = HungryEngine()

if __name__ == "__main__":
    asyncio.run(hungry_engine.start())
