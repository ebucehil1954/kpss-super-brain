"""
KPSS Super-Brain: Öğrenilmiş Zihin ve Mantık Tabanlı Akıllı Soru Fabrikası (Smart Question Generator v2)
Yapay zekanın videolardan öğrendiği öğretmen üslubunu, sınav tuzaklarını ve soru kalıplarını
kullanarak hakem denetiminden (%0 halüsinasyon kalkanı) geçen 5 şıklı ÖSYM soruları üretir.
"""
import json
import httpx
from typing import Dict, Any, List, Optional
from config import super_brain_config
from brain.knowledge_store import knowledge_store
from brain.reasoning_store import reasoning_store
from cognition.teacher_learner import teacher_learner
from cognition.reasoning_engine import reasoning_engine
from anti_hallucination.fact_checker import fact_checker
from anti_hallucination.adversarial_solver import adversarial_solver

class SmartQuestionGenerator:
    @classmethod
    async def generate_master_question(
        cls,
        lesson: str,
        topic: str,
        teacher_style: Optional[str] = None,
        difficulty: str = "ORTA"
    ) -> Optional[Dict[str, Any]]:
        """
        Öğrenilmiş hafıza kayıtları ve öğretmen zihniyetine dayalı hakemli soru üretir.
        """
        # 1. Hafızadaki doğrulanmış bilgileri ve tuzakları topla
        records = knowledge_store.get_records_by_topic(lesson, topic, limit=12)
        chains = reasoning_store.get_chains_for_topic(lesson, topic)
        
        facts_text = "\n".join([f"- {r['text']}" for r in records if r["record_type"] == "FACT"][:8])
        traps_text = "\n".join([f"- {r['text']}" for r in records if r["record_type"] == "TRAP"][:4])
        
        teacher_name = teacher_style or ("Ramazan Yetgin" if lesson == "TARIH" else ("Emrah Vahap Özkaraca" if lesson == "VATANDASLIK" else "Bayram Meral"))
        profile = teacher_learner.get_or_create_profile(teacher_name)

        prompt = f"""
Sen Türkiye'nin en kıdemli KPSS Soru Hazırlama Komisyonu Üyesi ve Eğitmen '{teacher_name}' Zihniyetisin.
Aşağıdaki doğrulanmış hafıza kayıtlarını, sınav tuzaklarını ve öğretmen üslubunu kullanarak ÖSYM STANDARTLARINDA 5 ŞIKLI 1 SORU YAZ.

DERS: {lesson}
KONU: {topic}
ZORLUK DERECESİ: {difficulty}

HAFIZADAKİ DOĞRULANMIŞ BİLGİLER:
{facts_text or '- 1982 Anayasası ve güncel KPSS müfredat kuralları.'}

ÖĞRENİLEN SINAV TUZAKLARI VE ÇELDIRICILER:
{traps_text or '- Mülga kavramlar (Başbakanlık, Tüzük, Gensoru) soruya konulamaz.'}

ÖĞRETMEN ÜSLUBU ({teacher_name}):
- Pedagoji: {json.dumps(profile.get('teaching_patterns', {}), ensure_ascii=False)}

ZORUNLU GÜVENLİK KURALLARI:
1. 2017 Anayasa Değişikliği sonrası yürürlükteki mevzuata %100 sadık kal.
2. Türkiye'de var olmayan sahte kanun isimleri (örn. 'İdare Hukuku Kanunu') ASLA kullanılamaz.
3. Tarihsel dönemlerde (örn. Lale Devri 1718-1730) kesinlikle anakronizm yapılamaz.
4. Şıklar (A, B, C, D, E) eşit uzunlukta ve inandırıcı çeldiricilere sahip olmalı.
5. Sadece ve kesinlikle tek bir tartışmasız doğru cevap bulunmalı.

SADECE GEÇERLİ JSON DÖNDÜR:
{{
  "lesson": "{lesson}",
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "teacher_inspiration": "{teacher_name}",
  "stem": "Soru metni ve kökü...",
  "options": {{
    "A": "Seçenek A",
    "B": "Seçenek B",
    "C": "Seçenek C",
    "D": "Seçenek D",
    "E": "Seçenek E"
  }},
  "expected_answer": "C",
  "explanation": "Gerekçeli ayrıntılı çözüm...",
  "trap_analyzed": "Çeldirici şıkların mantığı"
}}
"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(
                    f"{super_brain_config.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": super_brain_config.MAIN_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.25}
                    }
                )
                if res.status_code == 200:
                    q_data = json.loads(res.json().get("response", "{}"))
                    
                    # 1. Aşama: Çok Kademeli Fact Checker Kalkanı
                    full_text = f"{q_data.get('stem', '')} {' '.join(q_data.get('options', {}).values())} {q_data.get('explanation', '')}"
                    is_clean, reason = fact_checker.verify_content(full_text, topic=topic, lesson=lesson)
                    if not is_clean:
                        print(f"⚠️ [SMART QUESTION GEN] FactChecker tarafından reddedildi: {reason}")
                        return None

                    # 2. Aşama: Bağımsız Çift Kör Hakem Denetimi (Adversarial Referee)
                    is_approved, ref_msg = await adversarial_solver.audit_generated_question(q_data)
                    if not is_approved:
                        print(f"⚠️ [SMART QUESTION GEN] Hakem Heyeti tarafından reddedildi: {ref_msg}")
                        return None
                        
                    q_data["referee_verification"] = ref_msg
                    return q_data
        except Exception as e:
            print(f"⚠️ [SMART QUESTION GEN] Hata: {e}")
        return None

smart_question_generator = SmartQuestionGenerator()
