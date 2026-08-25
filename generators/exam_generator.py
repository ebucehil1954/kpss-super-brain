"""
KPSS Super-Brain: Hakem Onaylı 5 Şıklı ÖSYM Soru Fabrikası
"""
import httpx
import json
from typing import Optional, Dict, Any
from config import super_brain_config
from anti_hallucination.fact_checker import FactChecker
from anti_hallucination.adversarial_solver import AdversarialRefereeSolver

class ExamQuestionFactory:
    @classmethod
    async def generate_single_question(cls, lesson: str, topic: str, difficulty: str = "ORTA") -> Optional[Dict[str, Any]]:
        prompt = f"""
        Sen ÖSYM KPSS Soru Hazırlama Komisyonu Başuzmanısın.
        GÖREV: '{lesson}' dersinin '{topic}' konusu için {difficulty} zorlukta 5 şıklı (A, B, C, D, E) özgün bir KPSS sorusu yaz.
        
        KURALLAR:
        1. Sadece 1 adet kesin doğru cevap olsun.
        2. Çeldiriciler güçlü olsun ama çelişki barındırmasın.
        3. Güncel 1982 Anayasası ve MEB müfredatına sadık kal.
        
        FORMAT:
        {{
          "lesson": "{lesson}",
          "topic": "{topic}",
          "stem": "Soru metni...",
          "options": {{
             "A": "Seçenek A",
             "B": "Seçenek B",
             "C": "Seçenek C",
             "D": "Seçenek D",
             "E": "Seçenek E"
          }},
          "expected_answer": "A",
          "explanation": "Detaylı çözüm açıklaması"
        }}
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    f"{super_brain_config.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": super_brain_config.MAIN_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.3}
                    }
                )
                q_data = json.loads(res.json().get("response", "{}"))
                
                # 1. Aşama: Kara Liste ve Halüsinasyon Kontrolü
                full_text = f"{q_data.get('stem')} {' '.join(q_data.get('options', {}).values())}"
                is_clean, _ = FactChecker.verify_content(full_text)
                if not is_clean:
                    return None
                
                # 2. Aşama: Bağımsız Hakem Doğrulaması
                is_approved, _ = await AdversarialRefereeSolver.audit_generated_question(q_data)
                if not is_approved:
                    return None
                
                return q_data
        except Exception:
            return None
