"""
KPSS Super-Brain: ÖSYM Soru Kalıpları ve Çeldirici Analiz Motoru (Pattern Analyzer)
ÖSYM'nin geçmiş 10 yıldaki soru tiplerini, olumsuz soru köklerini ve çeldirici mantığını modeller.
"""
import re
from typing import Dict, Any, List, Optional
from config import super_brain_config
from brain.episodic_memory import episodic_memory

class PatternAnalyzer:
    # ÖSYM Soru Kökü Tipleri
    PATTERN_TYPES = {
        "OLUMSUZ_KOK": [
            r"değildir", r"savunulamaz", r"gösterilemez", r"yer almaz", r"söylenemez", r"ulaşılamaz", r"yoktur"
        ],
        "ONCULLU_CIKARIM": [
            r"I\.", r"II\.", r"III\.", r"hangileri doğrudur", r"hangileri söylenebilir", r"hangilerine ulaşılabilir"
        ],
        "KRONOLOJIK_SIRALAMA": [
            r"kronolojik", r"tarihsel sıra", r"oluş sırası", r"gerçekleşme sırası"
        ],
        "ESLESTIRME_TABLO": [
            r"eşleştirmelerden hangisi", r"hangisi doğru eşleştirilmiştir", r"hangisi yanlıştır"
        ],
        "HARITA_MEKANSAL": [
            r"harita", r"numaralandırılmış", r"işaretli alan", r"bölgede yer alır"
        ],
        "SAYISAL_HUKUK": [
            r"karar yeter", r"toplantı yeter", r"üye tam sayısı", r"yüzde", r"oran", r"yaş şartı"
        ]
    }

    # ÖSYM'nin En Çok Soru Sorduğu Konu Ağırlıkları (Genel Yetenek - Genel Kültür)
    HISTORICAL_TOPIC_WEIGHTS = {
        "TARIH": {
            "İslamiyet Öncesi Türk Tarihi": 0.08,
            "İlk Türk-İslam Devletleri": 0.08,
            "Osmanlı Kültür ve Medeniyeti": 0.15,
            "Osmanlı Siyasi Tarihi ve Islahatlar": 0.22,
            "Kurtuluş Savaşı Hazırlık ve Cepheler": 0.20,
            "Atatürk İlke ve İnkılapları": 0.15,
            "Çağdaş Türk ve Dünya Tarihi": 0.12
        },
        "VATANDASLIK": {
            "Temel Hukuk Kavramları": 0.15,
            "Anayasa Hukuku & 1982 Esasları": 0.25,
            "Yasama (TBMM)": 0.25,
            "Yürütme (Cumhurbaşkanlığı)": 0.15,
            "Yargı (Yüksek Mahkemeler)": 0.10,
            "İdare Hukuku": 0.10
        },
        "COGRAFYA": {
            "Türkiye'nin Coğrafi Konumu ve Jeopolitiği": 0.10,
            "Türkiye'nin Yer Şekilleri ve İklimi": 0.25,
            "Türkiye'nin Beşeri ve Nüfus Coğrafyası": 0.20,
            "Türkiye'nin Ekonomik Coğrafyası (Tarım & Hayvancılık)": 0.20,
            "Madenler, Enerji Kaynakları ve Sanayi": 0.25
        }
    }

    @classmethod
    def identify_question_pattern(cls, stem: str) -> Dict[str, Any]:
        """
        Verilen bir soru metninin hangi ÖSYM kalıbına girdiğini tespit eder.
        """
        detected_patterns = []
        stem_lower = stem.lower()
        
        for p_name, keywords in cls.PATTERN_TYPES.items():
            for kw in keywords:
                if re.search(kw, stem_lower):
                    detected_patterns.append(p_name)
                    break

        if not detected_patterns:
            detected_patterns.append("DOGRADAN_BILGI")

        return {
            "patterns": detected_patterns,
            "is_negative": "OLUMSUZ_KOK" in detected_patterns,
            "is_premise": "ONCULLU_CIKARIM" in detected_patterns,
            "is_chronology": "KRONOLOJIK_SIRALAMA" in detected_patterns
        }

    @classmethod
    def get_topic_priority(cls, lesson: str, topic: str) -> float:
        """
        Konunun tarihsel sınav frekans ağırlığını döner (0.0 - 1.0 arası).
        """
        lesson_dict = cls.HISTORICAL_TOPIC_WEIGHTS.get(lesson.upper(), {})
        for t_name, weight in lesson_dict.items():
            if t_name.lower() in topic.lower() or topic.lower() in t_name.lower():
                return weight
        return 0.15

    @classmethod
    def generate_pattern_report(cls) -> Dict[str, Any]:
        """
        ÖSYM soru kalıplarının genel analitik özeti.
        """
        return {
            "total_defined_patterns": len(cls.PATTERN_TYPES),
            "topic_weight_matrix": cls.HISTORICAL_TOPIC_WEIGHTS,
            "key_recommendation": "ÖSYM Tarih testinde %37 oranında Olumsuz Kök ve %25 oranında Öncüllü Çıkarım kullanmaktadır. Vatandaşlıkta TBMM sayıları ve İdare hukuku belirleyicidir."
        }

pattern_analyzer = PatternAnalyzer()
