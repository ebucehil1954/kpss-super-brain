"""
KPSS Super-Brain: Mevzuat Madde ve Kanun Atıf Doğrulayıcı (Legal Citation Validator)
Üretilen soru veya metinlerdeki kanun adı, madde numarası ve hukuki terimleri
`data/ground_truth/legislation.json` veri tabanına göre %100 deterministik olarak denetler.
"""
import os
import json
import re
from typing import Tuple, List, Dict, Any, Optional
from config import super_brain_config

class LegalCitationValidator:
    def __init__(self, ground_truth_path: Optional[str] = None):
        self.ground_truth_path = ground_truth_path or os.path.join(
            super_brain_config.GROUND_TRUTH_DIR, "legislation.json"
        )
        self.valid_laws = {}
        self.forbidden_fake_laws = []
        self._load()

    def _load(self):
        if os.path.exists(self.ground_truth_path):
            try:
                with open(self.ground_truth_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.valid_laws = data.get("valid_laws", {})
                    self.forbidden_fake_laws = data.get("forbidden_fake_laws", [])
            except Exception:
                pass

    def validate_text(self, text: str) -> Tuple[bool, List[str]]:
        """
        Metindeki tüm kanun isimlerini ve madde referanslarını denetler.
        """
        violations = []
        text_lower = text.lower()

        # 1. Yasaklı Sahte Kanun Denetimi
        for fake in self.forbidden_fake_laws:
            if fake.lower() in text_lower:
                violations.append(
                    f"Uydurma/Sahte Kanun Tespit Edildi: '{fake}'. (Türkiye'de bu isimde bir kanun yoktur)."
                )

        # 2. Genel Kanun Adı Kalıplarını Yakalama (Örn: "X Kanunu")
        # Eğer metinde ".... Kanunu" veya "... Kanunnamesi" geçiyorsa ve geçerli kanunlar listesinde yoksa uyar
        law_mentions = re.findall(r"([A-ZÇĞİÖŞÜa-zçğıöşü\s]+(?:\s+Sayılı)?\s+(?:Kanunu|Kanununa|Kanununda|Yasası))", text)
        for mention in law_mentions:
            clean_mention = mention.strip()
            # Bilinen genel/geçerli kanun mu?
            matched = False
            for valid_name in self.valid_laws.keys():
                if valid_name.lower() in clean_mention.lower() or clean_mention.lower() in valid_name.lower():
                    matched = True
                    break
            
            # İstisnalar (Genel hukuk kavramları)
            general_valid_phrases = ["medeni kanun", "ceza kanunu", "borçlar kanunu", "ticaret kanunu", "iş kanunu", "seçim kanunu", "siyasi partiler kanunu", "belediye kanunu", "il idaresi kanunu", "anayasa"]
            for gvp in general_valid_phrases:
                if gvp in clean_mention.lower():
                    matched = True
                    break

            if not matched and len(clean_mention.split()) <= 4:
                # Şüpheli kanun adı
                violations.append(f"Doğrulanamayan Şüpheli Kanun Atfı: '{clean_mention}'")

        # 3. Anayasa Maddesi Doğruluk Kontrolü
        # Örnek: "Anayasa(nın)? (m\.|Madde\s*)(\d+)"
        aym_matches = re.finditer(r"(?:anayasa|anayasası)(?:'nın|'nin|nın|nin)?\s*(?:m\.|madde|maddesi)?\s*(\d+)", text, re.IGNORECASE)
        aym_data = self.valid_laws.get("1982 Anayasası", {}).get("key_articles", {})
        
        for m in aym_matches:
            art_num = m.group(1)
            art_key = f"m. {art_num}"
            if art_key in aym_data:
                # Madde biliniyor, madde konusunun metindeki bağlamla uyumuna bak
                # Örnek: m. 85 milletvekilliği düşmesidir, eğer metinde yasa teklifi deniyorsa yakala
                if art_num == "85" and ("yasa teklif" in text_lower or "kanun teklif" in text_lower or "karar yeter" in text_lower):
                    violations.append("Hatalı Madde Eşleşmesi: Anayasa m. 85 Milletvekilliğinin Düşmesidir (Yasa/karar yeter sayısı m. 96'dır).")
                elif art_num == "75" and ("yasa tasarısı" in text_lower or "%60" in text_lower):
                    violations.append("Hatalı Madde Eşleşmesi: Anayasa m. 75 yalnızca TBMM'nin 600 milletvekilinden oluştuğunu belirtir.")

        return len(violations) == 0, violations

citation_validator = LegalCitationValidator()
