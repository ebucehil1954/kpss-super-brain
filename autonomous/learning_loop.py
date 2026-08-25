"""
KPSS Super-Brain: Sürekli Öğrenme ve Otonom Üretim Döngüsü (Continuous Learning Loop)
Manus-tarzı 'Sense -> Reason -> Act -> Verify -> Consolidate' otonom döngüsü.
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import super_brain_config
from senses.channel_monitor import channel_monitor
from senses.youtube_watcher import youtube_watcher
from senses.web_researcher import web_researcher
from cognition.prediction_engine import prediction_engine
from generators.question_factory import question_factory
from generators.mnemonic_engine import mnemonic_engine
from generators.flashcard_generator import flashcard_generator
from brain.episodic_memory import episodic_memory

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("KPSS_SUPER_BRAIN")

class ContinuousLearningLoop:
    OUTPUTS_DIR = str(super_brain_config.OUTPUTS_DIR)

    @classmethod
    def _save_json(cls, filename: str, new_data: Any) -> str:
        os.makedirs(cls.OUTPUTS_DIR, exist_ok=True)
        filepath = os.path.join(cls.OUTPUTS_DIR, filename)
        tmp_filepath = filepath + ".tmp"
        
        existing_data = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception as e:
                logger.error(f"Hata: {filepath} dosyası okunurken hata oluştu: {e}", exc_info=True)
                existing_data = []
                
        if isinstance(new_data, list):
            existing_data.extend(new_data)
        elif new_data is not None:
            existing_data.append(new_data)
            
        try:
            with open(tmp_filepath, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_filepath, filepath)
        except Exception as e:
            logger.error(f"Hata: {filepath} dosyası atomik olarak kaydedilirken hata oluştu: {e}", exc_info=True)
            if os.path.exists(tmp_filepath):
                try:
                    os.remove(tmp_filepath)
                except Exception:
                    pass
            raise
            
        return filepath

    @classmethod
    def _save_markdown_summary(cls, facts: list, mnemonic: dict, question: dict, research: dict):
        os.makedirs(cls.OUTPUTS_DIR, exist_ok=True)
        filepath = os.path.join(cls.OUTPUTS_DIR, "latest_summary.md")
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        md = f"# 🧠 KPSS Super-Brain — Otonom Zeka Canlı Raporu\n"
        md += f"**Rapor Tarihi:** `{now_str}`\n\n---\n\n"
        
        if research:
            md += f"## 📡 1. Canlı Algılama & Web / YouTube Taraması\n"
            md += f"- **İncelenen Konu:** `{research.get('topic')}` ({research.get('lesson')})\n"
            md += f"- **İşlenen Bilgi Parçacığı:** {research.get('ingested_chunks', 0)}\n\n---\n\n"
            
        if mnemonic:
            md += f"## ✨ 2. Yeni Üretilen Şifreli Kodlama (Akrostiş)\n"
            md += f"- **Kod:** `{mnemonic.get('code')}` — **{mnemonic.get('title')}**\n"
            md += f"- **Açıklama:** {mnemonic.get('description')}\n"
            md += f"- **Harf Açılımları:**\n"
            for b in mnemonic.get("breakdown", []):
                md += f"  - **{b.get('letter')}:** {b.get('word')}\n"
            md += "\n---\n\n"
            
        if facts:
            md += f"## 📰 3. Güncel Bilgi Flashcard'ları\n"
            for f in facts:
                md += f"### [{f.get('tag', 'GÜNCEL')}] {f.get('title')}\n"
                md += f"- {f.get('fact')}\n"
                md += f"- 💡 *{f.get('key_fact')}*\n\n"
            md += "---\n\n"
            
        if question:
            md += f"## 📝 4. Hakem Onaylı ÖSYM Tahmin Sorusu\n"
            md += f"**Ders & Konu:** `{question.get('lesson')}` — `{question.get('topic')}`\n\n"
            md += f"**Soru:**\n{question.get('stem')}\n\n"
            for k, v in question.get("options", {}).items():
                is_exp = (k == question.get('expected_answer'))
                md += f"- **{k})** {v} {'✅ *(Doğru Cevap)*' if is_exp else ''}\n"
            md += f"\n**Gerekçeli Çözüm:** {question.get('explanation')}\n"
            md += f"**Hakem Denetimi:** `{question.get('referee_verification', 'Onaylandı')}`\n\n"
            
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

    @classmethod
    async def execute_full_cycle(
        cls,
        target_topic: Optional[str] = None,
        target_lesson: Optional[str] = None,
        watch_youtube: bool = True
    ) -> Dict[str, Any]:
        """
        Otonom döngünün 1 tam iterasyonunu yürütür.
        """
        print("\n🚀 [SUPER-BRAIN] Otonom Öğrenme Döngüsü Başladı...")
        
        # 1. Aşama: Tahmin Motorundan En Yüksek Öncelikli Konuyu Seç
        topic = target_topic
        lesson = target_lesson
        if not topic or not lesson:
            top_pred = prediction_engine.get_top_prediction_for_lesson("VATANDASLIK") or {
                "lesson": "VATANDASLIK",
                "topic": "1982 Anayasası Yasama ve Karar Yeter Sayıları"
            }
            lesson = top_pred.get("lesson", "VATANDASLIK")
            topic = top_pred.get("topic", "1982 Anayasası Yasama ve Karar Yeter Sayıları")

        print(f"🎯 [HEDEF BELİRLENDİ] {lesson} — {topic}")

        # 2. Aşama: Canlı Web ve Vikipedi Araştırması Yap (Algılama)
        research_data = await web_researcher.deep_research_and_ingest(topic, lesson)
        print(f"📡 [ARAŞTIRMA TAMAMLANDI] {research_data.get('ingested_chunks')} bilgi parçası hafızaya alındı.")

        # 3. Aşama: YouTube Video İzleme & Eğitmen Mantığı Çıkarma (İsteğe Bağlı)
        yt_insights = None
        if watch_youtube:
            target_teacher = "Emrah Vahap Özkaraca" if lesson == "VATANDASLIK" else "Ramazan Yetgin"
            yt_insights = await youtube_watcher.analyze_and_learn_from_lecture(
                video_id_or_url="kpss_demo_yt_video",
                teacher_name=target_teacher,
                lesson=lesson,
                topic=topic
            )
            print(f"🎥 [YOUTUBE ANALİZİ] {target_teacher} hocanın bakış açısı ve tahminleri modellendi.")

        # 4. Aşama: Flashcard Üretimi
        news_items = research_data.get("sources", [])
        facts = []
        if news_items:
            raw_facts = [{"source": s.get("source"), "content": s.get("summary"), "tag": lesson} for s in news_items]
            facts = await flashcard_generator.generate_daily_facts(raw_facts)
            if facts:
                cls._save_json("daily_facts.json", facts)
                print(f"📰 [FLASHCARD] {len(facts)} adet hap kart 'outputs/daily_facts.json'a yazıldı.")

        # 5. Aşama: Şifreli Kodlama (Akrostiş) Üretimi
        mnemonic = await mnemonic_engine.generate_mnemonic(lesson, topic)
        if mnemonic:
            cls._save_json("mnemonics.json", mnemonic)
            print(f"✨ [ŞİFRELEME] '{mnemonic.get('code')}' akrostişi 'outputs/mnemonics.json'a yazıldı.")

        # 6. Aşama: Hakem Onaylı Soru Üretimi
        question = await question_factory.generate_single_question(
            lesson=lesson,
            topic=topic,
            difficulty="ORTA"
        )
        if question:
            cls._save_json("exam_questions.json", question)
            print(f"✅ [HAKEMLİ SORU] Doğru cevap [{question.get('expected_answer')}] olarak onaylandı ve kaydedildi.")

        # 7. Aşama: Canlı Markdown Raporunu Oluştur
        cls._save_markdown_summary(facts, mnemonic, question, research_data)
        print("📄 [RAPOR] 'outputs/latest_summary.md' güncellendi.\n")

        return {
            "status": "success",
            "lesson": lesson,
            "topic": topic,
            "research": research_data,
            "youtube_insights": yt_insights,
            "facts": facts,
            "mnemonic": mnemonic,
            "question": question,
            "completed_at": datetime.now().isoformat()
        }

learning_loop = ContinuousLearningLoop()
