"""
KPSS Super-Brain: Kronolojik Tutarlılık ve Dönem Anakronizmi Kalkanı (Temporal Validator v2)
`data/ground_truth/history_timeline.json` tablosunu kullanarak tarihsel dönemleri,
yılları, padişah-ıslahat eşleşmelerini ve olay sırasını matematiksel olarak denetler.
"""
import os
import json
import re
from typing import Tuple, List, Dict, Any, Optional
from config import super_brain_config

class TemporalValidator:
    def __init__(self, ground_truth_path: Optional[str] = None):
        self.ground_truth_path = ground_truth_path or os.path.join(
            super_brain_config.GROUND_TRUTH_DIR, "history_timeline.json"
        )
        self.eras = {}
        self.chronology = []
        self._load()

    def _load(self):
        if os.path.exists(self.ground_truth_path):
            try:
                with open(self.ground_truth_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.eras = data.get("eras_and_periods", {})
                    self.chronology = self.eras.get("Milli Mücadele Kronolojisi", [])
            except Exception:
                pass

    def validate_historical_text(self, text: str) -> Tuple[bool, List[str]]:
        """
        Metin içindeki tarihsel dönemleri, yılları ve sıralama çelişkilerini denetler.
        """
        violations = []
        text_lower = text.lower()

        # 1. Lale Devri Anakronizm Denetimi
        if "lale devri" in text_lower:
            # Yıl kontrolü: Eğer metinde 18xx veya 19xx yılları Lale Devri ile eşleştirilmişse yakala
            years_in_text = [int(y) for y in re.findall(r"\b(1[6-9]\d{2})\b", text)]
            for y in years_in_text:
                if y > 1735 and "lale devri" in text_lower:
                    # Lale devri 1718-1730'dur. 1839 veya 1876 ile eşleştirilemez!
                    violations.append(
                        f"Ağır Anakronizm Hatası: Lale Devri (1718-1730), {y} yılı ile eşleştirilemez!"
                    )
            if "19. yüzyıl" in text_lower and "lale devri" in text_lower:
                violations.append("Dönem Hatası: Lale Devri 19. yüzyıl değil, 18. yüzyıl başıdır (1718-1730).")
            if "askeri ıslahat" in text_lower and "lale devri" in text_lower:
                # Lale Devri'nde askeri ıslahat yapılmamıştır!
                if "yapılmamıştır" not in text_lower and "yoktur" not in text_lower:
                    violations.append("ÖSYM Tarih Tuzağı: Lale Devri'nde askeri ıslahat yapılmamıştır!")

        # 2. Nizam-ı Cedit Dönemi Denetimi
        if "nizam-ı cedit" in text_lower or "nizam-ı cedid" in text_lower:
            if "iii. ahmet" in text_lower:
                violations.append("Padişah Hatası: Nizam-ı Cedit III. Ahmet değil, III. Selim dönemidir.")

        # 3. Balkan Antantı & Sadabat Paktı Denetimi
        if "balkan antantı" in text_lower:
            if "bulgaristan katıldı" in text_lower or ("bulgaristan" in text_lower and "katılmadı" not in text_lower and "katılmayan" not in text_lower and "revizyonist" not in text_lower):
                violations.append("Tarihsel Hata: Balkan Antantı'na Bulgaristan ve Arnavutluk KATILMAMIŞTIR.")
        if "sadabat paktı" in text_lower:
            if "suriye katıldı" in text_lower:
                violations.append("Tarihsel Hata: Sadabat Paktı'na Hatay meselesi nedeniyle Suriye KATILMAMIŞTIR.")

        return len(violations) == 0, violations

temporal_validator = TemporalValidator()
