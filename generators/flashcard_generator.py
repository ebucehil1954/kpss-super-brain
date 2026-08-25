"""
KPSS Super-Brain: Günün Güncel Bilgisi Flashcard Fabrikası (Flashcard Generator)
"""
import httpx
import json
from typing import List, Dict, Any
from config import super_brain_config
from anti_hallucination.fact_checker import fact_checker

class FlashcardGenerator:
    @classmethod
    async def generate_daily_facts(cls, raw_news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        generated_cards = []
        for item in raw_news_list:
            prompt = f"""
            Aşağıdaki güncel gelişmeyi KPSS standartlarında bir 'HAP BİLGİ FLASHCARD'ına dönüştür.
            
            KAYNAK: {item.get('source')}
            METİN: {item.get('content') or item.get('summary')}
            
            SADECE şu JSON formatında yaz:
            {{
              "tag": "{item.get('tag', 'GÜNCEL BİLGİLER')}",
              "title": "Kısa ve Net Başlık",
              "fact": "ÖSYM tarzı net bilgi cümlesi",
              "key_fact": "Sınavda çıkabilecek kritik püf nokta"
            }}
            """
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    res = await client.post(
                        f"{super_brain_config.OLLAMA_BASE_URL}/api/generate",
                        json={
                            "model": super_brain_config.MAIN_MODEL,
                            "prompt": prompt,
                            "stream": False,
                            "format": "json",
                            "options": {"temperature": 0.2}
                        }
                    )
                    if res.status_code == 200:
                        data = json.loads(res.json().get("response", "{}"))
                        is_valid, _ = fact_checker.verify_content(f"{data.get('title')} {data.get('fact')}")
                        if is_valid:
                            generated_cards.append(data)
                            continue
            except Exception:
                pass

            # Fallback
            generated_cards.append({
                "tag": item.get("tag", "GÜNCEL BİLGİLER"),
                "title": item.get("title", "KPSS Güncel Not"),
                "fact": item.get("content", item.get("summary", "ÖSYM güncel genel kültür bilgisi.")),
                "key_fact": "ÖSYM bu bilgiyi 6 soruluk Genel Kültür güncel bilgiler alanında sorabilir."
            })
            
        return generated_cards

flashcard_generator = FlashcardGenerator()
