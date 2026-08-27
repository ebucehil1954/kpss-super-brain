"""
KPSS Super-Brain: Bilişsel Analiz Motoru (Cognitive Analyst)
Ders transkriptlerinden Local LLM (Qwen 2.5 14B) ve kural tabanlı hibrit motorla:
1. Atomik Sınav Doğruları (Facts)
2. Hoca Zihniyeti ve Soru Vurguları (Teacher Insights)
3. Hafıza Kodlamaları ve Şifreler (Mnemonics)
4. ÖSYM Çeldirici Soru Tuzakları (Exam Traps)
5. Muhakeme ve Eleme Zincirleri (Reasoning Chains)
çıkarır ve kalıcı zihin ambarına mühürler.
"""
from __future__ import annotations

import re
import json
import httpx
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from config import super_brain_config
from brain.knowledge_store import knowledge_store
from brain.reasoning_store import reasoning_store
from cognition.teacher_learner import teacher_learner
from brain.database import db_session

logger = logging.getLogger("cognitive_analyst")


class CognitiveAnalyst:
    """
    Transkriptleri derinlemesine analiz eden yapay zeka bilişsel analisti.
    """
    CHUNK_WORDS = 2200

    @classmethod
    def _chunk_transcript(cls, text: str) -> List[str]:
        """Transkripti anlamlı kelime bloklarına böler."""
        words = text.split()
        if not words:
            return []
        chunks = []
        for i in range(0, len(words), cls.CHUNK_WORDS):
            chunks.append(" ".join(words[i:i + cls.CHUNK_WORDS]))
        return chunks

    @classmethod
    def _find_time_estimate(cls, text_snippet: str, segments: Optional[List[Dict[str, Any]]]) -> str:
        """İddianın geçtiği zaman damgasını hesaplar."""
        if not segments:
            return "ZAMAN_BELİRTİLMEDİ"
        clean = text_snippet.lower()[:35]
        for seg in segments:
            stxt = seg.get("text", "").lower()
            if clean in stxt or any(w in stxt for w in clean.split() if len(w) > 5):
                start = int(seg.get("start", seg.get("start_seconds", 0)))
                end = int(seg.get("end", seg.get("end_seconds", start + 30)))
                return f"{start//60:02d}:{start%60:02d} - {end//60:02d}:{end%60:02d}"
        return "ZAMAN_BELİRTİLMEDİ"

    @classmethod
    def _extract_heuristic_mnemonics(cls, text: str) -> List[Dict[str, str]]:
        """Deterministik kurallarla bilinen ve metinde geçen KPSS şifrelerini yakalar."""
        found = []
        known_codes = {
            "KAYIP SAKAL": "Türkiye rüzgarları: Karayel, Yıldız, Poyraz, Samyeli, Kıble, Lodos",
            "MİLAD": "I. İnönü Muharebesi sonuçları: Moskova Antlaşması, İstiklal Marşı, Londra Konferansı, Afganistan Dostluk, Teşkilat-ı Esasiye",
            "TALİM": "I. İnönü Muharebesi sonuçları kronolojik alternatifi",
            "TAYYAR": "Balkan Antantı üyeleri: Türkiye, Atina (Yunanistan), Yugoslavya, Romanya",
            "TİAİ": "Sadabat Paktı üyeleri: Türkiye, İran, Irak, Afganistan",
            "FISTIKÇI ŞAHAP": "Türkçe sert ünsüz harfler: f, s, t, k, ç, ş, h, p"
        }
        for code, expl in known_codes.items():
            if code.lower() in text.lower():
                found.append({"code": code, "title": f"KPSS Kodlaması ({code})", "explanation": expl})

        # Regex ile "şifremiz X", "kodlama X" kalıplarını ara
        regex_patterns = [
            r"(?:şifremiz|kodumuz|akrostiş|şifre)[:\s]+([A-ZÇĞİÖŞÜa-zçğıöşü\s\-]{3,25})",
            r"([A-ZÇĞİÖŞÜ]{4,8})\s+(?:diye\s+kodluyoruz|olarak\s+kodlayın)"
        ]
        for pat in regex_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                val = m.group(1).strip().upper()
                if len(val) >= 3 and val not in [f["code"] for f in found]:
                    found.append({"code": val, "title": f"Eğitmen Şifresi: {val}", "explanation": f"Videoda geçen özel kodlama: {val}"})
        return found

    @classmethod
    def _extract_heuristic_traps(cls, text: str) -> List[Dict[str, str]]:
        """Hocanın 'aman dikkat', 'karıştırmayın' dediği çeldirici tuzakları yakalar."""
        traps = []
        trap_patterns = [
            r"(?:sakın\s+karıştırmayın|aman\s+dikkat|öğrenci\s+burada\s+düşüyor|en\s+büyük\s+tuzak|çeldirici\s+olarak\s+gelir)[^.!?]{5,150}[.!?]",
            r"(?:öbür\s+türlü|bununla\s+o\s+farklı|aynı\s+şey\s+değil)[^.!?]{5,150}[.!?]"
        ]
        for pat in trap_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                sentence = m.group(0).strip()
                if len(sentence) > 20:
                    traps.append({
                        "trap": sentence,
                        "correction": "Hocanın ders içi sınav tuzağı ve dikkat uyarısı."
                    })
        return traps[:5]

    async def analyze_transcript(
        self,
        transcript: str,
        teacher_name: str,
        lesson: str,
        topic: str,
        video_id: str,
        video_title: str = "",
        channel: str = "YouTube",
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Transkripti analiz eder, atomik iddiaları, şifreleri, hoca vurgularını ve
        tuzakları çıkararak veritabanına kaydeder.
        """
        if not transcript or len(transcript.strip()) < 50:
            return {"status": "error", "message": "Transkript metni yetersiz veya boş."}

        chunks = self._chunk_transcript(transcript)
        print(f"🧠 [BİLİŞSEL ANALİST] {teacher_name} — '{topic}' ({len(chunks)} parça analiz ediliyor...)")

        total_facts = 0
        total_mnemonics = 0
        total_traps = 0
        total_insights = 0
        total_reasoning = 0
        extracted_mnemonics_list: List[Dict[str, str]] = []

        now_str = datetime.now().isoformat()
        source_meta = {
            "type": "youtube_lecture",
            "video_id": video_id,
            "title": video_title,
            "teacher": teacher_name,
            "channel": channel,
            "lesson": lesson,
            "topic": topic,
            "analyzed_at": now_str
        }

        # 1. Deterministik Heuristic Taramalar (Her zaman çalışır)
        h_mnemonics = self._extract_heuristic_mnemonics(transcript)
        for mn in h_mnemonics:
            knowledge_store.add_or_reinforce_record(
                text=f"[{mn['code']}] {mn['title']}: {mn['explanation']}",
                record_type="MNEMONIC",
                lesson=lesson,
                topic=topic,
                confidence=0.95,
                source=source_meta,
                tags=["mnemonic", teacher_name.lower(), mn["code"].lower()]
            )
            total_mnemonics += 1
            extracted_mnemonics_list.append(mn)

        h_traps = self._extract_heuristic_traps(transcript)
        for tr in h_traps:
            knowledge_store.add_or_reinforce_record(
                text=f"⚠️ [ÖSYM TUZAĞI] {tr['trap']}",
                record_type="TRAP",
                lesson=lesson,
                topic=topic,
                confidence=0.92,
                source=source_meta,
                tags=["trap", teacher_name.lower(), "exam_warning"]
            )
            total_traps += 1

        # 2. Local LLM (Qwen 2.5 14B) ile Yapılandırılmış Derin Epistemik Çıkarım
        # En fazla ilk 3 parçayı derinlemesine LLM'e sok (performans ve hız için)
        for idx, chunk in enumerate(chunks[:3]):
            prompt = f"""Sen Türkiye'nin en kıdemli KPSS Eğitim Uzmanısın.
Aşağıdaki ders transkriptini incele ve SADECE geçerli bir JSON objesi döndür:

DERS: {lesson}
KONU: {topic}
EĞİTMEN: {teacher_name}
METİN:
\"\"\"{chunk[:4000]}\"\"\"

GÖREV:
1. Kesin, doğrulanabilir sınav bilgilerini (facts)
2. Eğitmenin ezber için verdiği şifre ve kodlamaları (mnemonics)
3. Öğrencilerin karıştırabileceği ÖSYM soru tuzaklarını (traps)
4. Eğitmenin "ÖSYM kesinlikle sorar" dediği önemli yerleri (insights)
çıkar.

JSON FORMATI:
{{
  "facts": [
    {{"text": "Doğrulanabilir olgusal bilgi", "subtopic": "Alt başlık"}}
  ],
  "mnemonics": [
    {{"code": "ŞİFRE", "title": "Başlık", "explanation": "Açıklama"}}
  ],
  "traps": [
    {{"trap": "ÖSYM'nin kullandığı çeldirici", "correction": "Doğrusu"}}
  ],
  "insights": [
    {{"emphasis": "Hocanın sınav uyarısı", "teaching_style": "Anlatım tarzı"}}
  ]
}}
"""
            llm_response = None
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(
                        f"{super_brain_config.OLLAMA_BASE_URL}/api/generate",
                        json={
                            "model": super_brain_config.MAIN_MODEL,
                            "prompt": prompt,
                            "stream": False,
                            "format": "json",
                            "options": {"temperature": 0.15}
                        }
                    )
                    if resp.status_code == 200:
                        llm_response = json.loads(resp.json().get("response", "{}"))
            except Exception as e:
                logger.debug(f"Ollama bağlantı/timeout ({e}). Heuristic çıkarımlar geçerli kalacak.")

            if llm_response:
                # LLM Facts
                for f in llm_response.get("facts", []):
                    f_text = f.get("text", "").strip() if isinstance(f, dict) else str(f).strip()
                    if f_text and len(f_text) > 15:
                        time_str = self._find_time_estimate(f_text, segments)
                        knowledge_store.add_or_reinforce_record(
                            text=f_text,
                            record_type="FACT",
                            lesson=lesson,
                            topic=topic,
                            subtopic=f.get("subtopic", "") if isinstance(f, dict) else "",
                            confidence=0.94,
                            source={**source_meta, "timestamp": time_str},
                            tags=["fact", teacher_name.lower(), lesson.lower()]
                        )
                        total_facts += 1

                # LLM Mnemonics
                for m in llm_response.get("mnemonics", []):
                    if isinstance(m, dict) and m.get("code"):
                        m_code = m["code"].strip().upper()
                        knowledge_store.add_or_reinforce_record(
                            text=f"[{m_code}] {m.get('title', 'Kodlama')}: {m.get('explanation', '')}",
                            record_type="MNEMONIC",
                            lesson=lesson,
                            topic=topic,
                            confidence=0.96,
                            source=source_meta,
                            tags=["mnemonic", teacher_name.lower(), m_code.lower()]
                        )
                        total_mnemonics += 1
                        extracted_mnemonics_list.append(m)

                # LLM Traps
                for t in llm_response.get("traps", []):
                    if isinstance(t, dict) and t.get("trap"):
                        knowledge_store.add_or_reinforce_record(
                            text=f"⚠️ [ÖSYM TUZAĞI] {t['trap']} -> Doğrusu: {t.get('correction', '')}",
                            record_type="TRAP",
                            lesson=lesson,
                            topic=topic,
                            confidence=0.95,
                            source=source_meta,
                            tags=["trap", teacher_name.lower(), "exam_trap"]
                        )
                        total_traps += 1

                # LLM Insights
                for ins in llm_response.get("insights", []):
                    if isinstance(ins, dict) and ins.get("emphasis"):
                        knowledge_store.add_or_reinforce_record(
                            text=f"🎯 [HOCA VURGUSU] {ins['emphasis']}",
                            record_type="TEACHER_INSIGHT",
                            lesson=lesson,
                            topic=topic,
                            confidence=0.90,
                            source=source_meta,
                            tags=["insight", teacher_name.lower()]
                        )
                        total_insights += 1

        # 3. Eğitmenin Zihin Profilini (Teacher Profile) Güncelle
        prof = teacher_learner.update_profile_from_lecture(
            teacher_name=teacher_name,
            lesson=lesson,
            topic=topic,
            transcript_words_count=len(transcript.split()),
            facts_count=total_facts,
            mnemonics_count=total_mnemonics,
            reasoning_count=total_reasoning,
            traps_count=total_traps,
            channel=channel
        )

        # Hoca profiline çıkarılan yeni şifreleri kaydet
        if extracted_mnemonics_list:
            self._append_mnemonics_to_teacher_profile(teacher_name, extracted_mnemonics_list)

        print(f"  └─ 📊 [ANALİZ TAMAMLANDI] +{total_facts} Bilgi | +{total_mnemonics} Şifre | +{total_traps} Tuzak | +{total_insights} Hoca Vurgusu")

        return {
            "status": "success",
            "video_id": video_id,
            "teacher": teacher_name,
            "lesson": lesson,
            "topic": topic,
            "facts_count": total_facts,
            "mnemonics_count": total_mnemonics,
            "traps_count": total_traps,
            "insights_count": total_insights,
            "teacher_profile_updated": prof.get("teacher_id")
        }

    @staticmethod
    def _append_mnemonics_to_teacher_profile(teacher_name: str, new_mnemonics: List[Dict[str, str]]):
        """Öğretmenin profiline çıkarılan yeni şifreleri ekler."""
        teacher_id = re.sub(r'[^a-zA-Z0-9_]', '', teacher_name.lower().replace(' ', '_'))
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mnemonics_used_json FROM teacher_profiles WHERE teacher_id = ?", (teacher_id,))
            row = cursor.fetchone()
            if row:
                existing = json.loads(row["mnemonics_used_json"] or "[]")
                existing_codes = {item.get("code") for item in existing if isinstance(item, dict)}
                for mn in new_mnemonics:
                    if mn.get("code") not in existing_codes:
                        existing.append(mn)
                        existing_codes.add(mn.get("code"))
                cursor.execute(
                    "UPDATE teacher_profiles SET mnemonics_used_json = ? WHERE teacher_id = ?",
                    (json.dumps(existing, ensure_ascii=False), teacher_id)
                )


cognitive_analyst = CognitiveAnalyst()
