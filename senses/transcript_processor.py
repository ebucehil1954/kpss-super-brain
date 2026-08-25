"""
KPSS Super-Brain: Transkript İşleme ve Çok Kademeli Çıkarım Hattı (Transcript Processor)
Uzun ders transkriptlerini pedagojik bölümlere ayırıp Ollama LLM ile olgular, öğretmen pedagojisi,
hafıza şifreleri, mantık zincirleri ve sınav tuzaklarını çıkarır ve SQLite ambarına yazar.
"""
import json
import httpx
import re
from typing import Dict, Any, List, Optional
from config import super_brain_config
from brain.knowledge_store import knowledge_store
from brain.reasoning_store import reasoning_store
from brain.database import db_session
from datetime import datetime

class TranscriptProcessor:
    CHUNK_WORD_SIZE = 2000

    @classmethod
    def _chunk_text(cls, text: str, word_limit: int = CHUNK_WORD_SIZE) -> List[str]:
        """Metni yaklaşık kelime sınırına göre anlamlı parçalara böler."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), word_limit):
            chunks.append(" ".join(words[i:i + word_limit]))
        return chunks if chunks else [text]

    @classmethod
    async def process_video_transcript(
        cls,
        video_id: str,
        title: str,
        teacher_name: str,
        lesson: str,
        topic: str,
        full_transcript: str
    ) -> Dict[str, Any]:
        """
        Transkripti bölümleyerek derinlemesine analiz eder ve beynin ambarına kaydeder.
        """
        chunks = cls._chunk_text(full_transcript)
        total_facts = 0
        total_mnemonics = 0
        total_traps = 0
        total_reasoning = 0
        total_insights = 0
        
        extracted_facts_list = []
        extracted_mnemonics_list = []
        extracted_traps_list = []
        extracted_reasoning_list = []

        now_str = datetime.now().isoformat()
        source_meta = {
            "type": "youtube_lecture",
            "teacher": teacher_name,
            "video_id": video_id,
            "video_title": title,
            "lesson": lesson,
            "topic": topic,
            "date": now_str
        }

        for idx, chunk in enumerate(chunks):
            # 5 Aşamalı Yapılandırılmış Çıkarım Prompt'u
            prompt = f"""
Sen Türkiye'nin en kıdemli KPSS Eğitim Bilimleri ve Alan Uzmanısın.
Aşağıda popüler KPSS eğitmeni '{teacher_name}' hocanın '{lesson} - {topic}' ders videosundan alınmış transkript parçası (Bölüm {idx+1}/{len(chunks)}) yer almaktadır.

GÖREV:
Bu transkripti derinlemesine incele ve hocanın aktardığı tüm bilgileri, pedagojik öğretme metodunu, soru çözme mantığını ve sınav tuzaklarını çıkar.

TRANSKRİPT METNİ:
\"\"\"{chunk[:4500]}\"\"\"

SADECE GEÇERLİ JSON DÖNDÜR:
{{
  "facts": [
    {{"text": "Kesin, doğrulanabilir sınav bilgisi cümlesi", "subtopic": "Alt konu", "tags": ["etiket1", "etiket2"]}}
  ],
  "teacher_insights": [
    {{"emphasis": "Hocanın 'ÖSYM bunu kesin sorar / buna dikkat edin' dediği vurgu", "teaching_style": "Kavramı açıklama biçimi"}}
  ],
  "mnemonics": [
    {{"code": "AKROSTİŞ_KODU", "title": "Şifre Başlığı", "explanation": "Harf açılımları ve hikayesi"}}
  ],
  "reasoning_chains": [
    {{
      "title": "Hocanın soru çözme ve eleme mantığı",
      "steps": [
        {{"step": 1, "action": "İlk bakılacak yer"}},
        {{"step": 2, "action": "Çeldiriciyi eleme kuralı"}}
      ]
    }}
  ],
  "traps": [
    {{"trap": "ÖSYM'nin adayları düşürdüğü yanıltıcı detay veya mülga kavram", "correction": "Doğru bilgi"}}
  ]
}}
"""
            res_json = await cls._query_llm_json(prompt)
            if not res_json:
                continue

            # 1. FACTS Ekle
            for f in res_json.get("facts", []):
                if isinstance(f, dict) and f.get("text"):
                    knowledge_store.add_or_reinforce_record(
                        text=f["text"],
                        record_type="FACT",
                        lesson=lesson,
                        topic=topic,
                        subtopic=f.get("subtopic", ""),
                        confidence=0.96,
                        source=source_meta,
                        tags=f.get("tags", [lesson, topic])
                    )
                    total_facts += 1
                    extracted_facts_list.append(f["text"])

            # 2. TEACHER INSIGHTS Ekle
            for ti in res_json.get("teacher_insights", []):
                if isinstance(ti, dict) and ti.get("emphasis"):
                    knowledge_store.add_or_reinforce_record(
                        text=f"[{teacher_name} Vurgusu] {ti['emphasis']}",
                        record_type="TEACHER_INSIGHT",
                        lesson=lesson,
                        topic=topic,
                        subtopic="Pedagojik Vurgu",
                        confidence=0.98,
                        source=source_meta,
                        tags=["TEACHER_INSIGHT", teacher_name, lesson]
                    )
                    total_insights += 1

            # 3. MNEMONICS Ekle
            for m in res_json.get("mnemonics", []):
                if isinstance(m, dict) and m.get("code"):
                    knowledge_store.add_or_reinforce_record(
                        text=f"Şifreli Kodlama [{m['code']}]: {m.get('explanation', '')}",
                        record_type="MNEMONIC",
                        lesson=lesson,
                        topic=topic,
                        subtopic=m.get("title", "Şifre"),
                        confidence=0.95,
                        source=source_meta,
                        tags=["MNEMONIC", m["code"], lesson]
                    )
                    total_mnemonics += 1
                    extracted_mnemonics_list.append(m)

            # 4. REASONING CHAINS Ekle
            for rc in res_json.get("reasoning_chains", []):
                if isinstance(rc, dict) and rc.get("steps"):
                    reasoning_store.save_reasoning_chain(
                        chain_type="QUESTION_SOLVING",
                        lesson=lesson,
                        topic=topic,
                        description=rc.get("title", f"{teacher_name} Soru Çözme Mantığı"),
                        steps=rc["steps"],
                        learned_from=[f"yt_{video_id}"],
                        teacher_source=teacher_name
                    )
                    total_reasoning += 1
                    extracted_reasoning_list.append(rc)

            # 5. TRAPS Ekle
            for tr in res_json.get("traps", []):
                if isinstance(tr, dict) and tr.get("trap"):
                    knowledge_store.add_or_reinforce_record(
                        text=f"⚠️ [ÖSYM Sınav Tuzağı] {tr['trap']} (Doğrusu: {tr.get('correction', '')})",
                        record_type="TRAP",
                        lesson=lesson,
                        topic=topic,
                        subtopic="Sınav Çeldiricisi",
                        confidence=0.97,
                        source=source_meta,
                        tags=["TRAP", "ÇELDİRİCİ", lesson]
                    )
                    total_traps += 1
                    extracted_traps_list.append(tr)

        # Öğrenme Olayı Kaydet (Learning Event)
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO learning_events (
                event_id, event_type, lesson, topic, teacher,
                summary, confidence_gain, details_json, created_at
            ) VALUES (?, 'VIDEO_DIGEST', ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"ev_{video_id}_{int(datetime.now().timestamp())}",
                lesson,
                topic,
                teacher_name,
                f"{teacher_name} hocanın '{title}' videosu sindirildi. {total_facts} bilgi, {total_mnemonics} şifre, {total_reasoning} mantık zinciri öğrenildi.",
                0.12,
                json.dumps({
                    "video_id": video_id,
                    "facts_count": total_facts,
                    "mnemonics_count": total_mnemonics,
                    "reasoning_count": total_reasoning,
                    "traps_count": total_traps
                }, ensure_ascii=False),
                now_str
            ))

        # Dinamik Ontoloji ve Bilgi Grafiğini Otomatik Genişlet
        try:
            from cognition.ontology_learner import ontology_learner
            await ontology_learner.extract_and_expand_graph(full_transcript[:3000], lesson, topic)
        except Exception:
            pass

        # Resmi Müfredat Konu Hakimiyet Matrisini Güncelle (En az 3-4 Video Kuralı)
        mastery_result = {}
        try:
            from brain.curriculum_matrix import curriculum_matrix
            mastery_result = curriculum_matrix.record_video_consumption(
                lesson=lesson,
                topic=topic,
                video_id=video_id,
                teacher_name=teacher_name,
                channel_name=source_meta.get("channel", "YouTube"),
                facts_extracted=total_facts,
                traps_extracted=total_traps,
                reasoning_extracted=total_reasoning,
                mnemonics_extracted=total_mnemonics
            )
            
            # Eğer konu 3 veya daha fazla videoya ulaştıysa çoklu hoca sentezi yap
            if mastery_result.get("consumed_videos_count", 0) >= 3:
                from cognition.cross_teacher_analyzer import cross_teacher_analyzer
                cross_teacher_analyzer.synthesize_master_topic_profile(lesson, topic)
                print(f"🎓 [UZMAN SENTEZİ OLUŞTURULDU] '{lesson}' — '{topic}' için çoklu hoca sentezi tamamlandı.")
        except Exception as e:
            print(f"⚠️ [MÜFREDAT MATRİSİ GÜNCELLEME HATASI]: {e}")

        return {
            "video_id": video_id,
            "teacher": teacher_name,
            "lesson": lesson,
            "topic": topic,
            "chunks_processed": len(chunks),
            "facts_extracted": total_facts,
            "mnemonics_extracted": total_mnemonics,
            "reasoning_extracted": total_reasoning,
            "traps_extracted": total_traps,
            "insights_extracted": total_insights,
            "mastery_info": mastery_result
        }

    @classmethod
    async def _query_llm_json(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """Ollama üzerinden JSON formatında güvenli sorgu yapar."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(
                    f"{super_brain_config.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": super_brain_config.MAIN_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": super_brain_config.FACT_TEMPERATURE
                        }
                    }
                )
                if res.status_code == 200:
                    raw_text = res.json().get("response", "{}")
                    return json.loads(raw_text)
        except Exception:
            # Ollama bağlantısı yoksa sessizce fallback kural tabanlı çıkarıma geç
            pass
        return None

transcript_processor = TranscriptProcessor()
