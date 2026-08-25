"""
KPSS Super-Brain: Şifreli Kodlama (Akrostiş) Üretici Motoru
"""
import httpx
import json
from typing import Optional, Dict, Any
from config import super_brain_config
from anti_hallucination.fact_checker import FactChecker

class MnemonicGenerator:
    @classmethod
    async def generate_mnemonic(cls, lesson: str, topic: str) -> Optional[Dict[str, Any]]:
        prompt = f"""
        Sen 15 yıllık kıdemli bir KPSS Genel Yetenek - Genel Kültür Başuzmanısın.
        GÖREV: '{lesson}' dersinin '{topic}' konusu için Türkçe fonetiğe uygun bir 'ŞİFRELİ KODLAMA (AKROSTİŞ)' üret.
        
        KURALLAR:
        1. Asla mülga kanun veya uydurma bilgi kullanma.
        2. Akrostiş kelimesi anlamlı veya kolay telaffuz edilebilir olsun (Örn: TAYYAR, MİLAT, CEKİST, SALDA TIM).
        3. Çıktıyı SADECE geçerli bir JSON objesi olarak ver.
        
        JSON FORMATI:
        {{
          "code": "ŞİFRE KELİMESİ",
          "title": "Şifrenin Başlığı",
          "lesson": "{lesson}",
          "lessonLabel": "Ders Alt Başlığı",
          "description": "Konunun kısa ve net özeti",
          "importance": "KRİTİK",
          "examFrequency": "ÖSYM Sıkça Sorar",
          "breakdown": [
             {{"letter": "T", "word": "Açıklama 1"}},
             {{"letter": "A", "word": "Açıklama 2"}}
          ]
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
                        "options": {"temperature": super_brain_config.CREATIVE_TEMPERATURE}
                    }
                )
                data = json.loads(res.json().get("response", "{}"))
                full_text = f"{data.get('code', '')} {data.get('title', '')} {data.get('description', '')}"
                is_valid, reason = FactChecker.verify_content(full_text)
                if not is_valid:
                    return None
                return data
        except Exception:
            return None
