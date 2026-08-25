"""
KPSS Super-Brain: Eğitmen Kimlik Normalizasyonu (Teacher Identity Canonicalizer)
Farklı yazım ve boşluk varyasyonlarını ("Ramazan Yetgin", " ramazan yetgin ", "RAMAZAN YETGİN")
tek bir kanonik eğitmen kimliğine dönüştürür.
"""
from __future__ import annotations

import re

class TeacherIdentity:
    @staticmethod
    def normalize(name: str) -> str:
        """Eğitmen adını kanonik forma dönüştürür."""
        if not name or not name.strip():
            return "Genel"
        
        cleaned = re.sub(r"\s+", " ", name.strip())
        # Türkçe büyük İ / küçük i dönüşümünü güvenli hale getir
        cleaned = cleaned.replace("İ", "I").replace("ı", "i").replace("I", "i")
        words = cleaned.lower().split(" ")
        norm_words = [w.capitalize() for w in words if w]
        return " ".join(norm_words)

teacher_identity = TeacherIdentity()
