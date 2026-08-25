"""
KPSS Super-Brain: Eğitmen Kimlik Normalizasyonu (Teacher Identity Canonicalizer v6)
Farklı yazım, unvan ve boşluk varyasyonlarını ("Ramazan Yetgin", " ramazan yetgin ", "RAMAZAN YETGİN", "Ramazan Yetgin Hoca")
tek bir kanonik eğitmen kimliğine dönüştürür.
"""
from __future__ import annotations

import re

class TeacherIdentity:
    ALIASES_PREFIX_SUFFIX = [
        r"\bhoca\b", r"\bhocamız\b", r"\böğretmen\b", r"\bogretmen\b",
        r"\bdr\b\.?", r"\bprof\b\.?", r"\bdoç\b\.?", r"\bdoc\b\.?",
        r"\bkonu\s*anlatımı\b", r"\bders\s*notları\b"
    ]

    KNOWN_TEACHERS = {
        "ramazan yetgin": "Ramazan Yetgin",
        "emrah vahap ozkaraca": "Emrah Vahap Özkaraca",
        "emrah vahap": "Emrah Vahap",
        "esra ozkan karaoglu": "Esra Özkan Karaoğlu",
        "esra ozkan": "Esra Özkan Karaoğlu",
        "ali koc": "Ali Koç",
        "mehmet egit": "Mehmet Eğit",
        "bayram meral": "Bayram Meral",
        "engin eraydin": "Engin Eraydın",
        "hakan dede": "Hakan Dede",
        "ilyas gunes": "İlyas Güneş"
    }

    @classmethod
    def normalize(cls, name: str) -> str:
        """Eğitmen adını kanonik forma dönüştürür ve unvan/varyasyonları temizler."""
        if not name or not name.strip():
            return "Genel"

        cleaned = name.strip()
        # Unvan ve ekleri temizle
        for pat in cls.ALIASES_PREFIX_SUFFIX:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        
        # Türkçe karakter basitleştirme ile lookup
        lookup_key = cleaned.lower()
        lookup_key = lookup_key.replace("ı", "i").replace("İ", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
        lookup_key = re.sub(r"\s+", " ", lookup_key).strip()

        if lookup_key in cls.KNOWN_TEACHERS:
            return cls.KNOWN_TEACHERS[lookup_key]

        # Genel formatlama: her kelimenin ilk harfi büyük
        cleaned_tr = cleaned.replace("İ", "I").replace("ı", "i").replace("I", "i")
        words = cleaned_tr.lower().split(" ")
        norm_words = [w.capitalize() for w in words if w]
        return " ".join(norm_words) if norm_words else "Genel"

teacher_identity = TeacherIdentity()
