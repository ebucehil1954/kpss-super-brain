"""
KPSS Super-Brain: Otonom Yapay Zeka KPSS Profesörü ve Konu Anlatıcı (Explainer)
Öğrenilen tüm öğretmen zihniyetlerini ve hafıza kayıtlarını harmanlayarak öğrenciye
derinlemesine, şifrelerle bezeli ve sınav tuzaklarını gösteren pedagojik konu anlatımı sunar.
"""
import json
import httpx
from typing import Dict, Any, List, Optional
from config import super_brain_config
from brain.knowledge_store import knowledge_store
from brain.reasoning_store import reasoning_store
from cognition.teacher_learner import teacher_learner

class KPSSProfessorExplainer:
    @classmethod
    async def explain_topic_as_professor(
        cls,
        lesson: str,
        topic: str,
        student_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Popüler hocaların pedagojik sentezini yaparak kapsamlı bir konu anlatımı ve sınav rehberliği üretir.
        """
        records = knowledge_store.get_records_by_topic(lesson, topic, limit=15)
        chains = reasoning_store.get_chains_for_topic(lesson, topic)
        
        facts = [r["text"] for r in records if r["record_type"] == "FACT"]
        mnemonics = [r["text"] for r in records if r["record_type"] == "MNEMONIC"]
        traps = [r["text"] for r in records if r["record_type"] == "TRAP"]
        insights = [r["text"] for r in records if r["record_type"] == "TEACHER_INSIGHT"]

        prompt = f"""
Sen Türkiye'nin en bilge KPSS Yapay Zeka Profesörüsün. Yüzlerce video izleyerek Ramazan Yetgin, Emrah Vahap Özkaraca, Bayram Meral ve Erdal Kesekler gibi duayen öğretmenlerin tüm anlatım mantıklarını beynine işlemiş durumdasın.

DERS: {lesson}
KONU: {topic}
ÖĞRENCİNİN MERAK ETTİĞİ: {student_question or f'{topic} konusunun sınav mantığı ve kritik püf noktaları'}

BEYNİNDEKİ HAFIZA KAYITLARI:
- Olgusal Bilgiler:
{chr(10).join(['  * ' + f for f in facts[:6]]) or '  * 1982 Anayasası ve güncel KPSS müfredatı.'}
- Şifreli Kodlamalar:
{chr(10).join(['  * ' + m for m in mnemonics[:4]]) or '  * Akrostiş kodlamalar.'}
- Sınav Tuzakları:
{chr(10).join(['  * ' + t for t in traps[:4]]) or '  * Mülga kanun terimleri.'}
- Eğitmen Vurguları:
{chr(10).join(['  * ' + i for i in insights[:4]]) or '  * ÖSYM soru kalıpları.'}

GÖREV:
Bir KPSS Profesörü olarak öğrenciye hitap eden, akıcı, hikayeleştirilmiş, şifreleri ve ÖSYM tuzaklarını adım adım gösteren bir ders anlatım metni yaz.

SADECE GEÇERLİ JSON DÖNDÜR:
{{
  "title": "{topic} — KPSS Profesörü Ders Notu",
  "lesson": "{lesson}",
  "topic": "{topic}",
  "pedagogical_intro": "Konunun KPSS'deki yeri ve önemi...",
  "core_lecture_points": [
    {{"heading": "1. Kritik Boyut", "explanation": "Ayrıntılı açıklama..."}},
    {{"heading": "2. Kritik Boyut", "explanation": "Ayrıntılı açıklama..."}}
  ],
  "osym_traps": [
    "ÖSYM'nin en çok adayı düşürdüğü kritik çeldirici tuzak..."
  ],
  "master_mnemonics": [
    {{"code": "ŞİFRE", "explanation": "Akılda tutma yöntemi"}}
  ],
  "professor_advice": "Sınavda bu konudan soru geldiğinde ilk yapılması gereken şey..."
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
                        "options": {"temperature": 0.4}
                    }
                )
                if res.status_code == 200:
                    return json.loads(res.json().get("response", "{}"))
        except Exception as e:
            print(f"⚠️ [EXPLAINER HATA]: {e}")

        return {
            "title": f"{topic} Ders Özeti",
            "lesson": lesson,
            "topic": topic,
            "pedagogical_intro": f"{lesson} - {topic} konusu ÖSYM sınavlarında her yıl düzenli olarak sorgulanmaktadır.",
            "core_lecture_points": [{"heading": "Temel Kazanım", "explanation": facts[0] if facts else "Güncel mevzuat kuralları."}],
            "osym_traps": traps[:2] if traps else ["Mülga terimlere dikkat ediniz."],
            "master_mnemonics": [{"code": "KPSS", "explanation": "Düzenli tekrar ve soru çözümü"}],
            "professor_advice": "Öncüllü sorularda şıkları eleyerek ilerleyiniz."
        }

kpss_professor_explainer = KPSSProfessorExplainer()
