"""
KPSS Super-Brain: Semantik Çelişki ve Tutarsızlık Dedektörü (Semantic Contradiction Detector)
Yeni öğrenilen bir bilginin hafızadaki doğrulanmış bilgilerle çelişip çelişmediğini
anlamsal zıtlık ve çelişki kurallarıyla tespit eder.
"""
import re
from typing import Tuple, List, Dict, Any, Optional
from brain.knowledge_store import knowledge_store

class SemanticContradictionDetector:
    # Karşılıklı Dışlayan (Mutually Exclusive) Kavram İkilemleri
    MUTUALLY_EXCLUSIVE_PAIRS = [
        ("askeri ıslahat yapılmıştır", "askeri ıslahat yapılmamıştır"),
        ("yüksek mahkemedir", "yüksek mahkeme değildir"),
        ("kanunla kurulur", "cumhurbaşkanı kararı ile kurulur"),
        ("yetki genişliği vardır", "yetki genişliği yoktur"),
        ("tek meclisli", "çift meclisli"),
        ("katılmıştır", "katılmamıştır"),
        ("1. sıradadır", "son sıradadır"),
        ("en fazladır", "en azdır")
    ]

    @classmethod
    def check_contradiction(
        cls,
        new_text: str,
        lesson: str,
        topic: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """
        Yeni metnin mevcut hafıza kayıtlarıyla doğrudan bir anlamsal çelişki
        içerip içermediğini denetler.
        """
        new_text_l = new_text.lower()
        existing_records = knowledge_store.get_records_by_topic(lesson, topic, limit=10)

        for rec in existing_records:
            existing_text_l = rec.get("text", "").lower()

            # Zıtlık çiftlerini kontrol et
            for positive, negative in cls.MUTUALLY_EXCLUSIVE_PAIRS:
                if positive in new_text_l and negative in existing_text_l:
                    return True, f"Semantik Çelişki: Yeni bilgi ('{positive}') mevcut doğrulanmış hafıza kaydıyla ('{negative}') çelişiyor."
                if negative in new_text_l and positive in existing_text_l:
                    return True, f"Semantik Çelişki: Yeni bilgi ('{negative}') mevcut doğrulanmış hafıza kaydıyla ('{positive}') çelişiyor."

        return False, None

semantic_contradiction_detector = SemanticContradictionDetector()
