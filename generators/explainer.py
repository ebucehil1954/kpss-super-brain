"""
KPSS Super-Brain: Otonom Yapay Zeka KPSS Profesörü ve Konu Anlatıcı (Explainer v3)
Öğrenilen tüm öğretmen zihniyetlerini, RefChecker doğrulanmış olgularını ve tuzak analizlerini
harmanlayarak öğrenciye derinlemesine, şifreli ve ÖSYM tuzaklarını deşifre eden ders anlatımı sunar.
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

        # Varsayılan Zengin İçerik Üretimi
        default_summary = facts[0] if facts else f"1982 Anayasası ve güncel ÖSYM müfredatı çerçevesinde {topic} temel bir kazanım alanıdır."
        default_traps = traps[:3] if traps else [
            f"ÖSYM {topic} konusunda genellikle mülga (kaldırılmış) eski kanun maddelerini çeldirici olarak sunar.",
            "Öncüllü sorularda 'kesinlikle' ve 'sadece' ifadelerine dikkat edilmelidir."
        ]
        default_mnemonics = mnemonics[:2] if mnemonics else ["KODLAMA: Akılda tutulması gereken temel kavram sırası."]

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
  "summary": "📌 Konu Özeti: {default_summary}",
  "pedagogical_intro": "Konunun KPSS'deki yeri ve önemi...",
  "core_lecture_points": [
    {{"heading": "1. Temel Boyut", "explanation": "Ayrıntılı açıklama..."}},
    {{"heading": "2. Kritik Boyut", "explanation": "Ayrıntılı açıklama..."}}
  ],
  "osym_traps": [
    "⚠️ ÖSYM BURADAN SORAR! (Tuzak Noktalar)..."
  ],
  "master_mnemonics": [
    {{"code": "ŞİFRE", "explanation": "🧠 HAFIZA KODLAMASI: Akılda tutma yöntemi"}}
  ],
  "professor_advice": "🎓 Sınavda bu konudan soru geldiğinde ilk yapılması gereken şey..."
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
                    data = json.loads(res.json().get("response", "{}"))
                    if "summary" not in data:
                        data["summary"] = f"📌 Konu Özeti: {default_summary}"
                    return data
        except Exception:
            pass

        return {
            "title": f"# [DERS NOTU] {lesson} - {topic} (2026 Güncel)",
            "lesson": lesson,
            "topic": topic,
            "summary": f"📌 Konu Özeti: {default_summary}",
            "pedagogical_intro": f"{lesson} - {topic} konusu ÖSYM sınavlarında her yıl düzenli olarak sorgulanmaktadır.",
            "core_lecture_points": [{"heading": "Temel Kazanım", "explanation": default_summary}],
            "osym_traps": [f"⚠️ ÖSYM BURADAN SORAR! (Tuzak): {t}" for t in default_traps],
            "master_mnemonics": [{"code": "KPSS-ŞİFRE", "explanation": f"🧠 HAFIZA KODLAMASI: {default_mnemonics[0]}"}],
            "professor_advice": "🎓 Sınavda öncüllü sorularda şıkları eleyerek ilerleyiniz ve mülga terimleri hemen çiziniz."
        }

kpss_professor_explainer = KPSSProfessorExplainer()
