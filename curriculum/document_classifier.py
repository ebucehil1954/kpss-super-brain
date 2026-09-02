"""
KPSS Super-Brain V1.5: Doküman Sınıflandırıcı ve Güvenli Müfredat Eşleyici (Document Classifier)
8 sınıflı taksonomi, kaskat müfredat çözümleme ve tehlikeli varsayılanları engelleyen katı UNKNOWN yönetimi.
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from brain.models import DocumentClassification
from brain.curriculum_matrix import CurriculumMatrixEngine


class DocumentClassifier:
    """
    V1.5 Doküman Tipi ve Müfredat Konusu Sınıflandırıcısı.
    Asla varsayımsal (guesswork) eşleme yapmaz.
    """

    # 1. KANONİK MÜFREDAT ALİAS HARİTASI
    TOPIC_ALIASES: Dict[str, Tuple[str, str]] = {
        # Tarih
        "islamiyet oncesi": ("TARIH", "ILK_TURK_DEVLETLERI"),
        "orta asya turk": ("TARIH", "ILK_TURK_DEVLETLERI"),
        "gokturk": ("TARIH", "ILK_TURK_DEVLETLERI"),
        "uygurlar": ("TARIH", "ILK_TURK_DEVLETLERI"),
        "turk islam": ("TARIH", "ILK_TURK_ISLAM_DEVLETLERI"),
        "karahanlilar": ("TARIH", "ILK_TURK_ISLAM_DEVLETLERI"),
        "gazneliler": ("TARIH", "ILK_TURK_ISLAM_DEVLETLERI"),
        "selcuklu": ("TARIH", "ANADOLU_SELCOKLU_BEYLIKLER"),
        "anadolu selcuklu": ("TARIH", "ANADOLU_SELCOKLU_BEYLIKLER"),
        "osmanli kurulus": ("TARIH", "OSMANLI_KURULUS_YUKSELME"),
        "osmanli kultur": ("TARIH", "OSMANLI_KULTUR_MEDENIYET"),
        "divan-i humayun": ("TARIH", "OSMANLI_KULTUR_MEDENIYET"),
        "timar sistemi": ("TARIH", "OSMANLI_KULTUR_MEDENIYET"),
        "inkilap tarihi": ("TARIH", "ATATURK_ILKE_VE_INKILAPLARI"),
        "amasya genelgesi": ("TARIH", "MILLI_MUCADELE_HAZIRLIK"),
        "erzurum kongresi": ("TARIH", "MILLI_MUCADELE_HAZIRLIK"),
        "sivas kongresi": ("TARIH", "MILLI_MUCADELE_HAZIRLIK"),
        "misak-i milli": ("TARIH", "MILLI_MUCADELE_HAZIRLIK"),
        "lozan": ("TARIH", "MILLI_MUCADELE_MUHAREBELER"),
        # Coğrafya
        "turkiye cografyasi": ("COGRAFYA", "TURKIYE_FIZIKI_COGRAFYASI"),
        "turkiyenin yersekilleri": ("COGRAFYA", "TURKIYE_FIZIKI_COGRAFYASI"),
        "turkiyenin iklimi": ("COGRAFYA", "TURKIYE_IKLIM_VE_BITKI"),
        "turkiyenin madenleri": ("COGRAFYA", "TURKIYE_MADENLER_ENERJI"),
        "turkiye nufusu": ("COGRAFYA", "TURKIYE_BESERI_COGRAFYASI"),
        # Vatandaşlık / Anayasa
        "temel hukuk": ("VATANDASLIK", "TEMEL_HUKUK_KAVRAMLARI"),
        "anayasa hukuku": ("VATANDASLIK", "ANAYASA_TARIHI_VE_ESASLAR"),
        "1982 anayasasi": ("VATANDASLIK", "1982_ANAYASASI_DEVLET_ORG"),
        "yasama organi": ("VATANDASLIK", "1982_ANAYASASI_DEVLET_ORG"),
        "yurutme organi": ("VATANDASLIK", "1982_ANAYASASI_DEVLET_ORG"),
        "yargi organi": ("VATANDASLIK", "1982_ANAYASASI_DEVLET_ORG"),
        "idare hukuku": ("VATANDASLIK", "IDARE_HUKUKU"),
        # Türkçe & Matematik
        "sozcukte anlam": ("TURKCE", "SOZCUKTE_ANLAM"),
        "cumlede anlam": ("TURKCE", "CUMLEDE_ANLAM"),
        "paragraf": ("TURKCE", "PARAGRAF_BILGISI"),
        "dil bilgisi": ("TURKCE", "SES_BILGISI_YAZIM_NOKTALAMA"),
        "sayilar": ("MATEMATIK", "TEMEL_KAVRAMLAR_VE_SAYILAR"),
        "problemler": ("MATEMATIK", "ORAN_ORANTI_VE_PROBLEMLER"),
    }

    # 2. SINIFLANDIRMA BELİRTEÇLERİ (Heuristics)
    CLASSIFICATION_PATTERNS = {
        DocumentClassification.ANSWER_KEY: [
            r"cevap\s*anahtarı", r"doğru\s*seçenek", r"yanıt\s*anahtarı",
            r"test\s*\d+\s*cevapları", r"1\s*[-–]\s*[A-E]\s+2\s*[-–]\s*[A-E]"
        ],
        DocumentClassification.EXAM: [
            r"kpss\s*(lisans|önlisans|ortaöğretim)?\s*\d{4}",
            r"genel\s*yetenek\s*genel\s*kültür\s*testi",
            r"soru\s*kitapçığı", r"deneme\s*sınavı", r"tg\s*deneme"
        ],
        DocumentClassification.QUESTION_BANK: [
            r"soru\s*bankası", r"yaprak\s*test", r"çözümlü\s*sorular",
            r"konu\s*testi", r"test\s*\d+"
        ],
        DocumentClassification.OFFICIAL: [
            r"resmi\s*gazete", r"kanun\s*no", r"mevzuat", r"ösym\s*kılavuz",
            r"t\.c\.\s*anayasası", r"bakanlar\s*kurulu\s*kararı"
        ],
        DocumentClassification.COURSE_MATERIAL: [
            r"ders\s*not[uılar]*", r"özet\s*notlar?", r"ders\s*kitabı",
            r"hafıza\s*kartları", r"şifreler", r"kavram\s*haritası"
        ],
        DocumentClassification.REFERENCE: [
            r"kaynakça", r"akademik", r"tarihsel\s*analiz", r"ansiklopedi"
        ]
    }

    @classmethod
    def classify_document_type(cls, text_sample: str, filename: str = "") -> DocumentClassification:
        """
        Metin örneği ve dosya adına göre doküman türünü belirler.
        Yeterli güven yoksa UNKNOWN döner.
        """
        combined = f"{filename} {text_sample}".lower()

        scores: Dict[DocumentClassification, int] = {}
        for class_type, patterns in cls.CLASSIFICATION_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, combined, re.IGNORECASE))
                score += matches
            if score > 0:
                scores[class_type] = score

        if not scores:
            return DocumentClassification.UNKNOWN

        # En yüksek skorlu sınıfı bul
        best_class, best_score = max(scores.items(), key=lambda item: item[1])

        # Eğer birden fazla güçlü gösterge varsa MIXED olabilir
        high_scorers = [c for c, s in scores.items() if s >= 2]
        if len(high_scorers) > 1 and DocumentClassification.QUESTION_BANK in high_scorers and DocumentClassification.COURSE_MATERIAL in high_scorers:
            return DocumentClassification.MIXED

        if best_score >= 1:
            return best_class

        return DocumentClassification.UNKNOWN

    @classmethod
    def map_curriculum_topic(
        cls,
        text_sample: str,
        filename: str = "",
        explicit_lesson: Optional[str] = None,
        explicit_topic: Optional[str] = None
    ) -> Tuple[str, str, float]:
        """
        Kaskat müfredat eşleme:
        1. Açık topic_id eşleşmesi
        2. Alias eşleşmesi
        3. Müfredat anahtar kelime eşleşmesi
        4. Eşleşme yoksa -> ('UNKNOWN', 'UNKNOWN', 0.0)
        
        ASLA rastgele veya varsayılan (örn: TARIH) atama yapmaz.
        """
        # 1. Açık Eşleme
        if explicit_lesson and explicit_topic:
            lesson_clean = explicit_lesson.strip().upper()
            topic_clean = explicit_topic.strip().upper()
            if lesson_clean in CurriculumMatrixEngine.OFFICIAL_CURRICULUM:
                if topic_clean in CurriculumMatrixEngine.OFFICIAL_CURRICULUM[lesson_clean]:
                    return lesson_clean, topic_clean, 1.0

        combined = f"{filename} {text_sample}".lower()

        # 2. Alias Eşleşmesi
        for alias, (lesson, topic) in cls.TOPIC_ALIASES.items():
            if alias in combined:
                return lesson, topic, 0.90

        # 3. Resmi Müfredat Alt Başlık ve Konu İsimleri Taraması
        best_match = None
        highest_score = 0

        for lesson_key, topics in CurriculumMatrixEngine.OFFICIAL_CURRICULUM.items():
            for topic_key, topic_data in topics.items():
                name_clean = topic_data.get("name", "").lower()
                subtopics = topic_data.get("subtopics", [])

                score = 0
                # Konu ana ismi geçiyor mu?
                if name_clean and len(name_clean) > 5 and name_clean in combined:
                    score += 5

                # Alt başlıklar geçiyor mu?
                for sub in subtopics:
                    sub_clean = sub.lower()
                    if len(sub_clean) > 4 and sub_clean in combined:
                        score += 2

                if score > highest_score:
                    highest_score = score
                    best_match = (lesson_key, topic_key)

        # Güven Eşiği (En az 3 puan)
        if best_match and highest_score >= 3:
            confidence = min(0.95, 0.50 + (highest_score * 0.05))
            return best_match[0], best_match[1], confidence

        # 4. Eşleşme Yetersiz: Katı UNKNOWN
        return "UNKNOWN", "UNKNOWN", 0.0


document_classifier = DocumentClassifier()
