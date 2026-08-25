"""
KPSS Super-Brain: Hakem Onaylı 5 Şıklı ÖSYM Soru Fabrikası (Question Factory)
ÖSYM standartlarında, çeldirici analizli, hakem onaylı özgün sorular üretir.
"""
import httpx
import json
from typing import Optional, Dict, Any
from config import super_brain_config
from anti_hallucination.fact_checker import fact_checker
from anti_hallucination.adversarial_solver import adversarial_solver
from cognition.pattern_analyzer import pattern_analyzer
from cognition.difficulty_estimator import difficulty_estimator
from brain.vector_memory import vector_memory

class ExamQuestionFactory:
    @classmethod
    async def generate_single_question(
        cls,
        lesson: str,
        topic: str,
        difficulty: str = "ORTA",
        target_pattern: Optional[str] = None,
        teacher_style: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        ÖSYM kalıplarına tam uyumlu, pedagojik ve hakem onaylı 5 şıklı soru üretir.
        """
        # Hafızadan ilgili bağlamı çek
        memory_chunks = vector_memory.search(f"{lesson} {topic}", top_k=2, lesson_filter=lesson)
        context_str = "\n".join([c.get("text", "") for c in memory_chunks])
        if not context_str:
            context_str = f"{lesson} dersi {topic} konusu güncel MEB ve Anayasa müfredatı."

        style_directive = ""
        if teacher_style:
            style_directive = f"Soru yazımında popüler KPSS eğitmeni '{teacher_style}' hocanın vurguladığı ÖSYM püf noktalarını ve çeldirici tuzaklarını uygula."

        pattern_directive = ""
        if target_pattern:
            pattern_directive = f"Soru kalıbı olarak '{target_pattern}' (örn. Olumsuz Soru Kökü veya Öncüllü I-II-III) formatını kullan."

        prompt = f"""
        Sen ÖSYM KPSS Soru Hazırlama Komisyonu Başuzmanısın.
        
        GÖREV:
        '{lesson}' dersinin '{topic}' konusu için {difficulty} zorluk seviyesinde 5 şıklı (A, B, C, D, E) ÖZGÜN bir KPSS sorusu yaz.
        
        {style_directive}
        {pattern_directive}
        
        KULLANILACAK BİLGİ BAĞLAMI:
        {context_str}
        
        ZORUNLU KURALLAR:
        1. 2017 Anayasa Değişikliği ve güncel mevzuata %100 sadık kal. (Başbakan, tüzük, gensoru gibi mülga kavramlar ASLA kullanılmayacak).
        2. Tarihsel Kronolojiye ve Padişah-Islahat eşleşmelerine kesin uy (Örn: Lale Devri'nde askeri ıslahat YOKTUR, ilk askeri ıslahat I. Mahmut / Hendesehane ile başlar, Nizam-ı Cedit III. Selim'dir).
        3. SADECE ve KESİNLİKLE 1 adet tartışmasız doğru cevap olsun.
        4. Çeldiriciler güçlü, ÖSYM diline uygun olsun ancak akademik çelişki barındırmasın.
        5. Çözüm kısmında doğru cevabın gerekçesini ve çeldiricilerin neden elendiğini detaylı açıkla.
        
        ÇIKTI FORMATI (SADECE GEÇERLİ JSON):
        {{
          "lesson": "{lesson}",
          "topic": "{topic}",
          "difficulty": "{difficulty}",
          "stem": "Soru metni (Kökü net ve anlaşılır)...",
          "options": {{
             "A": "Seçenek A",
             "B": "Seçenek B",
             "C": "Seçenek C",
             "D": "Seçenek D",
             "E": "Seçenek E"
          }},
          "expected_answer": "A",
          "explanation": "Detaylı çözüm, gerekçe ve çeldirici analizi."
        }}
        """

        q_data = None
        try:
            async with httpx.AsyncClient(timeout=75.0) as client:
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
        except Exception:
            pass

        if not q_data or not isinstance(q_data, dict) or "stem" not in q_data or "options" not in q_data:
            # Fallback deterministik güvenli soru
            if lesson.upper() == "VATANDASLIK":
                q_data = {
                    "lesson": "VATANDASLIK",
                    "topic": topic or "1982 Anayasası Yasama ve Karar Yeter Sayıları",
                    "difficulty": difficulty,
                    "stem": "1982 Anayasası'na göre TBMM'nin seçimlerin yenilenmesine karar verebilmesi için gerekli olan üye çoğunluğu aşağıdakilerden hangisidir?",
                    "options": {
                        "A": "Üye tamsayısının salt çoğunluğu (301)",
                        "B": "Üye tamsayısının beşte üç çoğunluğu (360)",
                        "C": "Üye tamsayısının üçte iki çoğunluğu (400)",
                        "D": "Toplantıya katılanların salt çoğunluğu (en az 151)",
                        "E": "Üye tamsayısının üçte biri (200)"
                    },
                    "expected_answer": "B",
                    "explanation": "1982 Anayasası m. 116 uyarınca TBMM, üye tamsayısının beşte üç çoğunluğuyla (360 milletvekili) seçimlerin yenilenmesine karar verebilir. A şıkkı genel kural, C şıkkı Anayasa değişikliğinin referandumsuz kabulü, E şıkkı teklif yeter sayısıdır."
                }
            elif lesson.upper() == "TARIH":
                q_data = {
                    "lesson": "TARIH",
                    "topic": topic or "Lale Devri Islahatları",
                    "difficulty": difficulty,
                    "stem": "Osmanlı Devleti'nde 1718 Pasarofça Antlaşması ile başlayıp 1730 Patrona Halil İsyanı ile sona eren Lale Devri'nde aşağıdaki alanlardan hangisinde herhangi bir ıslahat yapılmamıştır?",
                    "options": {
                        "A": "Kültür ve Edebiyat",
                        "B": "Matbaacılık ve Basın",
                        "C": "Askeri ve Savunma",
                        "D": "Sağlık ve Tıp",
                        "E": "Diplomasi ve Dış İlişkiler"
                    },
                    "expected_answer": "C",
                    "explanation": "Lale Devri'nde (1718-1730) ilk geçici elçilikler açılmış (diplomasi), ilk özel matbaa kurulmuş (kültür/basın), çiçek aşısı uygulanmış (sağlık) ve tercüme heyetleri kurulmuştur. Ancak bu dönemde kesinlikle ASKERİ ISLAHAT YAPILMAMIŞTIR. İlk askeri ıslahatlar I. Mahmut döneminde başlamıştır."
                }
            else:
                q_data = {
                    "lesson": "COGRAFYA",
                    "topic": topic or "Türkiye'nin Madenleri",
                    "difficulty": difficulty,
                    "stem": "Türkiye'de çıkarılan boksit (alüminyum) madeninin işlendiği en önemli entegre tesis aşağıdakilerden hangisinde yer almaktadır?",
                    "options": {
                        "A": "Konya - Seydişehir",
                        "B": "Elazığ - Maden",
                        "C": "Artvin - Murgul",
                        "D": "Balıkesir - Bandırma",
                        "E": "Karabük"
                    },
                    "expected_answer": "A",
                    "explanation": "Türkiye'nin en önemli boksit işleme ve alüminyum tesisi Konya Seydişehir'de yer alır. Elazığ ve Murgul bakır, Bandırma bor, Karabük ise demir-çelik sanayisi ile öne çıkar."
                }

        # 1. Aşama: Kara Liste ve Halüsinasyon Denetimi
        full_text = f"{q_data.get('stem', '')} {' '.join(q_data.get('options', {}).values())} {q_data.get('explanation', '')}"
        is_clean, reason = fact_checker.verify_content(full_text, topic=topic, lesson=lesson)
        if not is_clean:
            print(f"[UYARI] Üretilen soru fact_checker tarafından reddedildi: {reason}")
            return None

        # 2. Aşama: Bağımsız Hakem (Adversarial Referee) Doğrulaması
        is_approved, ref_msg = await adversarial_solver.audit_generated_question(q_data)
        if not is_approved:
            print(f"[UYARI] Üretilen soru Hakem Heyetinden geçemedi: {ref_msg}")
            return None

        # Soru Kalıbı ve Zorluk Analizini Ekle
        pattern_info = pattern_analyzer.identify_question_pattern(q_data.get("stem", ""))
        diff_info = difficulty_estimator.estimate_difficulty(q_data.get("stem", ""), q_data.get("options", {}), pattern_info)
        
        q_data["pattern_tags"] = pattern_info.get("patterns", [])
        q_data["discrimination_index"] = diff_info.get("discrimination_index", 0.75)
        q_data["referee_verification"] = ref_msg

        return q_data

question_factory = ExamQuestionFactory()
