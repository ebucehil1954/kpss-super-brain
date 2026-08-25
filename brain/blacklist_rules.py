"""
KPSS Super-Brain: Mülga / Kaldırılmış Mevzuat, Yabancı Dil ve Hatalı Bilgi Kara Liste Denetçisi (Blacklist Auditor v2)
2017 Anayasa Değişikliği, mülga kavramlar, yabancı dil sızıntıları ve bilinen ÖSYM tuzaklarını %100 filtreler.
"""
import re
from typing import List, Tuple

# 2017 Anayasa Değişikliği ve Güncel Mevzuatla Kaldırılan / Mülga Terimler
MULGA_TERIMLER = [
    "başbakan",
    "başbakanlık",
    "başbakanın",
    "bakanlar kurulu kararnamesi",
    "bakanlar kurulu",
    "tüzük",
    "tüzükler",
    "tüzüğü",
    "gensoru",
    "gensorusu",
    "güvenoyu",
    "sıkıyönetim",
    "550 milletvekili",
    "550 mv",
    "askeri yargıtay",
    "askeri yüksek idare mahkemesi",
    "ayim",
    "askeri mahkemeler",
    "devlet güvenlik mahkemesi",
    "dgm",
    "hakimler ve savcılar yüksek kurulu",
    "hsyk",
    "kanun hükmünde kararname",
    "khk",
    "kanun tasarısı",
    "yasa tasarısı",
    "tasarı",
    "tasarısı"
]

# Yabancı Dil (İngilizce) Sızıntı Kalıpları
YABANCI_DIL_KALIPLARI = [
    r"\bgrand national assembly\b",
    r"\bassembly of\b",
    r"\bconstitution of\b",
    r"\barticle \d+\b",
    r"\bprime minister\b",
    r"\bparliament of\b",
    r"\bturkish republic\b",
    r"\bthe president\b"
]

# Tarihsel ve Coğrafi Yanılgı Kalıpları
TARIH_YANILGI_KALIPLARI = [
    (r"lale devri.*(?:1839|1876|19\.\s*yüzyıl)", "Lale Devri 18. yüzyıldır (1718-1730), 19. yüzyıl veya Tanzimat dönemiyle eşleştirilemez!"),
    (r"lale devri.*askeri ıslahat(?!\s*yapılmamıştır|\s*yoktur)", "Lale Devri'nde askeri ıslahat yapılmamıştır!"),
    (r"nizam-ı cedit.*iii\. ahmet", "Nizam-ı Cedit III. Ahmet değil, III. Selim dönemidir!"),
    (r"balkan antantı.*(?:bulgaristan katıldı|arnavutluk katıldı)", "Balkan Antantı'na Bulgaristan ve Arnavutluk katılmamıştır!"),
    (r"sadabat paktı.*suriye katıldı", "Sadabat Paktı'na Hatay meselesi nedeniyle Suriye katılmamıştır!")
]

class BlacklistAuditor:
    @classmethod
    def audit_text(cls, text: str) -> Tuple[bool, List[str]]:
        text_lower = text.lower()
        found_violations = []
        
        # 1. Mülga Kanun Denetimi
        for term in MULGA_TERIMLER:
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, text_lower):
                # İstisna: Eğer metin 'tasarı kaldırılmıştır' veya 'başbakanlık makamı 2017'de kaldırılmıştır' diyorsa ihlal sayma
                if f"{term} kaldırılmıştır" in text_lower or f"{term} mülga" in text_lower:
                    continue
                found_violations.append(f"Mülga/Kaldırılmış Terim Tespit Edildi: '{term}' (2017 Anayasa Değişikliği İhlali)")
                
        # 2. Yabancı Dil Sızıntı Denetimi
        for pattern in YABANCI_DIL_KALIPLARI:
            if re.search(pattern, text_lower):
                found_violations.append(f"Yabancı Dil Sızıntısı: Türkçe KPSS içeriğinde İngilizce kalıp tespit edildi ({pattern}).")

        # 3. Tarihsel Kronoloji Yanılgı Denetimi
        for pattern, warning in TARIH_YANILGI_KALIPLARI:
            if re.search(pattern, text_lower):
                found_violations.append(f"Tarihsel Hata / Anakronizm: {warning}")

        return len(found_violations) == 0, found_violations

blacklist_auditor = BlacklistAuditor()
