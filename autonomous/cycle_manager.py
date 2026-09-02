"""
KPSS Super-Brain: Otonom Öğrenme Döngü Yöneticisi (Cycle Manager)
7/24 kesintisiz çalışan: Keşfet -> İzle & Sindir -> Çapraz Doğrula -> Eksikleri Tespit Et -> Konsolide Et & Dışa Aktar.
"""
import sys
import asyncio
import random
import time
from typing import Dict, Any, Optional
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from config import super_brain_config
from senses.video_crawler import video_crawler
from senses.video_queue import video_queue
from senses.transcript_fetcher import transcript_fetcher
from senses.transcript_processor import transcript_processor
from cognition.teacher_learner import teacher_learner
from cognition.self_tester import self_tester
from brain.exporter import data_exporter

class CycleManager:
    _last_discovery_time = 0.0
    _last_consolidation_time = 0.0
    _last_self_eval_time = 0.0

    @classmethod
    async def run_discovery_if_needed(cls, force: bool = False) -> int:
        """Belirli aralıklarla hedef öğretmenlerin yeni videolarını tarar ve kuyruğa ekler."""
        now = time.time()
        if not force and (now - cls._last_discovery_time < super_brain_config.CHANNEL_DISCOVERY_INTERVAL_SEC):
            return 0
        
        print("\n🔍 [CYCLE MANAGER] Hedef KPSS Kanalları ve Öğretmen Videoları Keşfediliyor...")
        total_discovered = 0
        
        for t_cfg in super_brain_config.TARGET_TEACHERS:
            name = t_cfg["name"]
            lesson = t_cfg["lesson"]
            channel = t_cfg.get("channel", "")
            query = t_cfg.get("search_query", f"{name} KPSS {lesson}")
            
            videos = video_crawler.search_teacher_videos(
                search_query=query,
                teacher_name=name,
                lesson=lesson,
                channel_name=channel,
                max_results=8
            )
            added = video_queue.enqueue_batch(videos, priority=20)
            total_discovered += added
            if added > 0:
                print(f"  └─ 📺 {name} ({lesson}): {added} yeni video kuyruğa eklendi.")

        cls._last_discovery_time = now
        return total_discovered

    @classmethod
    async def process_single_video_step(cls) -> Optional[Dict[str, Any]]:
        """Kuyruktan bir sonraki videoyu çeker, transkriptini alır ve zihne işler."""
        next_vid = video_queue.get_next_unwatched()
        if not next_vid:
            # Kuyruk boşsa keşif yapmayı dene
            await cls.run_discovery_if_needed(force=True)
            next_vid = video_queue.get_next_unwatched()
            if not next_vid:
                print("💤 [CYCLE MANAGER] Kuyrukta izlenecek video kalmadı. Bekleniyor...")
                return None

        video_id = next_vid["video_id"]
        title = next_vid.get("title", "KPSS Dersi")
        teacher = next_vid.get("teacher_name", "Genel")
        lesson = next_vid.get("lesson", "GENEL")
        topic = next_vid.get("topic", "Genel Konu")
        channel = next_vid.get("channel", "")

        print(f"\n🎬 [İNCELENİYOR] '{teacher}' — '{title}' ({lesson} - {topic})")

        # 1. Transkript Çek
        t_res = transcript_fetcher.fetch_transcript(video_id)
        full_text = t_res.get("text", "")
        
        if not t_res.get("success") or not full_text:
            err = t_res.get("error", "Transkript çekilemedi")
            print(f"  └─ ⚠️ YouTube altyazısı doğrudan alınamadı ({err[:60]}...).")
            print(f"  └─ 🌐 [WEB ARAŞTIRMA MODU] '{teacher}' hocanın '{topic}' konusu için web araştırması yapılıyor...")
            
            # [P0-5 DÜZELTME] Sahte transkript üretmek yerine web araştırma sonuçlarını
            # ayrı kaynak tipiyle staging'e yaz ve videoyu DEFERRED olarak işaretle
            from senses.web_researcher import web_researcher
            from brain.knowledge_store import knowledge_store
            web_data = await web_researcher.deep_research_and_ingest(topic, lesson)
            
            # Web verilerini WEB_SYNTHESIZED kaynak tipiyle staging'e yaz (kanonik ambara DEĞİL)
            web_facts_count = 0
            for s in web_data.get("sources", []):
                summary = s.get("summary", "").strip()
                if summary and len(summary) > 20:
                    knowledge_store.stage_pending_record(
                        text=summary,
                        record_type="FACT",
                        lesson=lesson,
                        topic=topic,
                        confidence=0.85,  # Web kaynakları daha düşük güvenle staging'e girer
                        source={
                            "type": "WEB_SYNTHESIZED",
                            "title": s.get("title", ""),
                            "url": s.get("url", ""),
                            "teacher_context": teacher,
                            "original_video_id": video_id
                        },
                        tags=["web_synthesized", teacher.lower(), "needs_verification"]
                    )
                    web_facts_count += 1
            
            # Video'yu DEFERRED olarak işaretle (WATCHED değil!)
            video_queue.mark_transcript_deferred(
                video_id=video_id,
                error_msg=f"Transkript bulunamadı. Web araştırmasından {web_facts_count} bilgi staging'e alındı."
            )
            
            print(f"  └─ 📋 Web araştırmasından {web_facts_count} bilgi PENDING staging'e yazıldı (kaynak: WEB_SYNTHESIZED)")
            return {
                "status": "web_fallback",
                "source_type": "WEB_SYNTHESIZED",
                "facts_extracted": web_facts_count,
                "video_id": video_id
            }

        # === NORMAL AKIŞ: Transkript başarıyla çekildi ===
        words_count = len(full_text.split())
        print(f"  └─ 📝 Transkript hazır ({words_count} kelime). LLM ile derin analiz başlıyor...")

        # 2. Transkripti Bölümle ve Çıkarım Yap
        proc_result = await transcript_processor.process_video_transcript(
            video_id=video_id,
            title=title,
            teacher_name=teacher,
            lesson=lesson,
            topic=topic,
            full_transcript=full_text
        )

        # 3. Öğretmen Profilini Güncelle
        teacher_learner.update_profile_from_lecture(
            teacher_name=teacher,
            lesson=lesson,
            topic=topic,
            transcript_words_count=words_count,
            facts_count=proc_result.get("facts_extracted", 0),
            mnemonics_count=proc_result.get("mnemonics_extracted", 0),
            reasoning_count=proc_result.get("reasoning_extracted", 0),
            traps_count=proc_result.get("traps_extracted", 0),
            channel=channel
        )

        # 4. Kuyruk Durumunu Güncelle
        video_queue.mark_watched(
            video_id=video_id,
            transcript_length=words_count,
            chunks_extracted=proc_result.get("facts_extracted", 0) + proc_result.get("mnemonics_extracted", 0)
        )

        print(f"  └─ ✅ Başarıyla Sindirildi: +{proc_result.get('facts_extracted')} Bilgi, +{proc_result.get('mnemonics_extracted')} Şifre, +{proc_result.get('reasoning_extracted')} Mantık Zinciri.")
        return proc_result

    @classmethod
    async def run_consolidation_and_exports(cls, force: bool = False):
        """Zihin ambarını periyodik olarak konsolide eder ve sade JSON dosyalarını günceller."""
        now = time.time()
        if not force and (now - cls._last_consolidation_time < super_brain_config.CONSOLIDATION_INTERVAL_SEC):
            return
        
        print("\n💾 [KONSOLİDASYON] Zihin ambarı 'data/exports/' dizinine dışa aktarılıyor...")
        files = data_exporter.export_all()
        print(f"  └─ 📁 Güncellenen JSON Dosyaları: {', '.join(files.keys())}")
        cls._last_consolidation_time = now

    @classmethod
    async def run_self_eval_if_needed(cls, force: bool = False):
        """Kör nokta analizi yapar ve eksik ders konuları için öncelikli video araştırır."""
        now = time.time()
        if not force and (now - cls._last_self_eval_time < super_brain_config.SELF_EVAL_INTERVAL_SEC):
            return

        print("\n🧪 [ÖZ-DEĞERLENDİRME] Bilişsel olgunluk ve konu eksikleri kontrol ediliyor...")
        repaired = self_tester.auto_repair_gaps()
        if repaired > 0:
            print(f"  └─ 🎯 Tespit edilen eksik konular için {repaired} yeni hedef video kuyruğa eklendi.")
        cls._last_self_eval_time = now

cycle_manager = CycleManager()
