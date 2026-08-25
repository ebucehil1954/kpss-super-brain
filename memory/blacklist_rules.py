"""
KPSS Super-Brain: Mülga / Kaldırılmış Terimler ve Kara Liste Denetçisi
"""
import re
from typing import List, Tuple

MULGA_TERIMLER = [
    "başbakan",
    "başbakanlık",
    "bakanlar kurulu kararnamesi",
    "tüzük",
    "tüzükler",
    "gensoru",
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
    "hsyk"
]

class BlacklistAuditor:
    @staticmethod
    def audit_text(text: str) -> Tuple[bool, List[str]]:
        text_lower = text.lower()
        found_violations = []
        
        for term in MULGA_TERIMLER:
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, text_lower):
                found_violations.append(f"Mülga/Kaldırılmış Terim Tespit Edildi: '{term}'")
                
        return len(found_violations) == 0, found_violations
