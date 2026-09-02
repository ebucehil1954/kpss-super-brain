"""
KPSS Super-Brain V1.5: Soru Kalıpları Zeka Motoru (Question Pattern Classifier)
11 standart ÖSYM soru kalıbı taksonomisi ve soyut şablon sınıflandırması.
"""
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from brain.models import QuestionPatternRecord, QuestionRecord
from brain.database import db_session, initialize_database

logger = logging.getLogger("pattern_classifier")


class PatternClassifier:
    """
    V1.5 Soru Kalıpları Analizörü ve Taksonomi Yöneticisi.
    Kural: Kalıplar soyut yapısal modellerdir, soruların metin kopyaları değildir.
    """

    DEFAULT_PATTERNS = [
        {
            "code": "NEGATIVE_SELECTION",
            "name": "Olumsuz Seçim ve Kök Analizi",
            "description": "Soru kökünde olumsuz ifade barındıran, olmayanı veya yanlış olanı buldurmayı amaçlayan kalıp.",
            "cognitive_level": "ANALYSIS",
            "indicators": ["değildir", "yoktur", "savunulamaz", "ulaşılamaz", "gösterilemez", "söylenemez", "yanlıştır"]
        },
        {
            "code": "STATEMENT_ANALYSIS",
            "name": "Öncüllü Yargı / İfade Analizi (I, II, III)",
            "description": "Romen rakamlarıyla verilen birden fazla öncülün doğruluğunu veya uygulanabilirliğini sorgulayan kalıp.",
            "cognitive_level": "EVALUATION",
            "indicators": ["yalnız i", "i ve ii", "i, ii ve iii", "hangileri", "yargılarından"]
        },
        {
            "code": "CHRONOLOGY",
            "name": "Kronolojik Sıralama ve Zaman Dizilimi",
            "description": "Olayların, antlaşmaların veya dönemlerin kronolojik gelişim sırasını test eden kalıp.",
            "cognitive_level": "KNOWLEDGE",
            "indicators": ["kronolojik", "sırasıyla", "önce", "sonra", "tarihsel sıralama", "döneminde"]
        },
        {
            "code": "CAUSE_RESULT",
            "name": "Neden - Sonuç Bağıntısı",
            "description": "Tarihsel veya coğrafi bir olayın gerekçesini veya doğurduğu sonuçları sorgulayan kalıp.",
            "cognitive_level": "COMPREHENSION",
            "indicators": ["neden olmuştur", "sonucudur", "gerekçesiyle", "ortam hazırlamıştır", "sebebidir"]
        },
        {
            "code": "COMPARISON",
            "name": "Karşılaştırma ve Mukayese",
            "description": "İki veya daha fazla antlaşma, kurum, ilke veya coğrafi bölge arasındaki benzerlik/farklılıkları test eden kalıp.",
            "cognitive_level": "ANALYSIS",
            "indicators": ["farklı olarak", "benzer şekilde", "karşılaştırıldığında", "ortak özelliğidir", "kıyasla"]
        },
        {
            "code": "MATCHING",
            "name": "Eşleştirme ve Tablo",
            "description": "Kavram-tanım, yazar-eser, padişah-ıslahat gibi ikili veya çoklu eşleştirmeleri içeren kalıp.",
            "cognitive_level": "KNOWLEDGE",
            "indicators": ["eşleştirmelerden", "hangisinde doğru verilmiştir", "ilişkilendirilemez", "tabloda"]
        },
        {
            "code": "INFERENCE",
            "name": "Paragraftan Çıkarım ve Yorumlama",
            "description": "Verilen paragraf veya alıntıya dayanarak mantıksal ve pedagojik çıkarım yapmayı gerektiren kalıp.",
            "cognitive_level": "INFERENCE",
            "indicators": ["bilgiye dayanarak", "paragraftan hareketle", "çıkarılabilir", "vurgulanmaktadır"]
        },
        {
            "code": "EXCEPTION",
            "name": "Kural Dışı / İstisna Tespiti",
            "description": "Genel bir kuralın, kanunun veya ilkenin özel istisnasını sorgulayan kalıp.",
            "cognitive_level": "ANALYSIS",
            "indicators": ["istisnadır", "hariçtir", "kapsamı dışındadır", "aykırıdır"]
        },
        {
            "code": "COUNTING",
            "name": "Sayısal Nicelik ve Adet Sayma",
            "description": "Verilen öncül veya unsurlardan kaç tanesinin belirtilen şarta uyduğunu sorgulayan kalıp.",
            "cognitive_level": "ANALYSIS",
            "indicators": ["kaç tanesi", "kaçında", "sayısı kaçtır"]
        },
        {
            "code": "CLASSIFICATION",
            "name": "Tasnif ve Gruplandırma",
            "description": "Bir unsuru ait olduğu doğru zümreye, döneme veya sınıfa yerleştirmeyi test eden kalıp.",
            "cognitive_level": "COMPREHENSION",
            "indicators": ["grubunda yer alır", "sınıflandırılır", "arasında yer almaz", "türündendir"]
        },
        {
            "code": "DIRECT_FACT",
            "name": "Doğrudan Olgusal Bilgi (Spot Bilgi)",
            "description": "Ek bağlam olmadan doğrudan bir kavramı, kişiyi, eseri veya terimi sorgulayan spot kalıp.",
            "cognitive_level": "KNOWLEDGE",
            "indicators": ["kimdir", "hangisidir", "adlandırılır", "nerededir"]
        }
    ]

    def __init__(self):
        initialize_database()
        self._ensure_patterns_seeded()

    def _ensure_patterns_seeded(self):
        """11 standart kalıbı v15_question_patterns tablosuna yükler."""
        now_str = datetime.now().isoformat()
        with db_session() as conn:
            cursor = conn.cursor()
            for pat in self.DEFAULT_PATTERNS:
                pat_id = f"pat_{pat['code'].lower()}"
                cursor.execute("""
                INSERT INTO v15_question_patterns (
                    pattern_id, pattern_code, pattern_name, description,
                    cognitive_level, structural_indicators_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pattern_code) DO UPDATE SET
                    pattern_name = excluded.pattern_name,
                    description = excluded.description,
                    cognitive_level = excluded.cognitive_level,
                    structural_indicators_json = excluded.structural_indicators_json
                """, (
                    pat_id,
                    pat["code"],
                    pat["name"],
                    pat["description"],
                    pat["cognitive_level"],
                    json.dumps(pat["indicators"], ensure_ascii=False),
                    now_str
                ))

    def classify_question_pattern(
        self,
        stem_text: str,
        premises: Optional[List[str]] = None,
        is_negative: bool = False
    ) -> List[Tuple[str, float]]:
        """
        Soru kökü ve öncüllerine göre en uygun soru kalıplarını ve güven puanlarını döner.
        """
        stem_lower = stem_text.lower()
        premises_lower = " ".join(premises or []).lower()
        full_text = f"{stem_lower} {premises_lower}"

        matches: List[Tuple[str, float]] = []

        # 1. Öncüllü Soru Kontrolü
        if premises and len(premises) >= 2 or (" i." in stem_lower or " i, ii" in stem_lower):
            matches.append(("STATEMENT_ANALYSIS", 0.95))

        # 2. Olumsuz Soru Kontrolü
        if is_negative or any(ind in stem_lower for ind in ["değildir", "degildir", "yoktur", "savunulamaz", "ulaşılamaz", "ulasilamaz", "söylenemez", "soylenemez", "yer almaz"]):
            matches.append(("NEGATIVE_SELECTION", 0.95))

        # 3. Diğer Kalıpları Tara
        for pat in self.DEFAULT_PATTERNS:
            code = pat["code"]
            if code in [m[0] for m in matches]:
                continue

            score = 0
            for ind in pat["indicators"]:
                if ind in full_text:
                    score += 1

            if score > 0:
                conf = min(0.90, 0.50 + (score * 0.20))
                matches.append((code, conf))

        if not matches:
            matches.append(("DIRECT_FACT", 0.70))

        # Puana göre sırala
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def link_question_to_patterns(
        self,
        question_id: str,
        stem_text: str,
        premises: Optional[List[str]] = None,
        is_negative: bool = False
    ) -> List[str]:
        """Soruyu tespit edilen kalıplara veritabanında bağlar."""
        classified = self.classify_question_pattern(stem_text, premises, is_negative)
        now_str = datetime.now().isoformat()
        linked_pattern_codes = []

        with db_session() as conn:
            cursor = conn.cursor()
            for code, conf in classified[:2]:  # En iyi 2 kalıbı bağla
                pat_id = f"pat_{code.lower()}"
                link_id = f"qpl_{question_id}_{code.lower()}"
                cursor.execute("""
                INSERT INTO v15_question_pattern_links (
                    link_id, question_id, pattern_id, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(question_id, pattern_id) DO UPDATE SET
                    confidence = excluded.confidence
                """, (link_id, question_id, pat_id, conf, now_str))
                linked_pattern_codes.append(code)

        return linked_pattern_codes


pattern_classifier = PatternClassifier()
