"""
KPSS Super-Brain: Deterministik Sayısal ve Oran Doğrulayıcı (Numerical & Quorum Validator v2)
Vatandaşlık, Tarih ve Coğrafya alanlarındaki anayasal sayıları, üye tamsayılarını,
yaş sınırlarını, süreleri ve oranları Türkçe çekim eklerine duyarlı kural setiyle denetler.
"""
import re
from typing import Tuple, List, Dict, Any

class NumericalValidator:
    # Kesin anayasal ve yasal kurallar (Değiştirilemez / Deterministik)
    NUMERICAL_RULES = [
        {
            "id": "TBMM_UYE_TAMSAYISI",
            "context_keywords": ["tbmm", "milletvekil", "meclis"],
            "must_match": [(r"\b550\s*(?:milletvekil\w*|mv\w*|üye\w*)", False, "TBMM üye tamsayısı 550 değil, 600'dür (2017 değişikliği).")],
            "correct_value": "600 milletvekili"
        },
        {
            "id": "TOPLANTI_YETER_SAYISI",
            "context_keywords": ["toplantı yeter", "toplanma yeter"],
            "must_match": [
                (r"\b151\b.*toplantı", False, "Toplantı yeter sayısı en az 200'dür (üye tamsayısının 1/3'ü). 151 karar yeter sayısı alt sınırıdır."),
                (r"toplantı.*(?:151|150|140|301)\b", False, "Toplantı yeter sayısı 200 milletvekilidir (1/3).")
            ],
            "correct_value": "200 (1/3)"
        },
        {
            "id": "KARAR_YETER_SAYISI_TABAN",
            "context_keywords": ["karar yeter"],
            "must_match": [
                (r"karar yeter.*(?:139|140|150|200)\b", False, "Karar yeter sayısı hiçbir şekilde 151'den (1/4 + 1) az olamaz.")
            ],
            "correct_value": "En az 151 (üye tamsayısının 1/4'ünün 1 fazlası)"
        },
        {
            "id": "SECIM_YENILEME_COGUNLUGU",
            "context_keywords": ["seçimlerin yenilenmesi", "erken seçim", "seçim yenileme", "seçimlerin yenilenmesine"],
            "must_match": [
                (r"seçim\w*.*yenilen\w*.*(?:salt çoğunluk|301|400|200)\b", False, "TBMM'nin seçimleri yenileme kararı için üye tamsayısının 3/5 çoğunluğu (360 milletvekili) gerekir.")
            ],
            "correct_value": "3/5 (360 milletvekili)"
        },
        {
            "id": "ANAYASA_DEGISIKLIGI_TEKLIF",
            "context_keywords": ["anayasa değişikliği teklif", "anayasa teklif"],
            "must_match": [
                (r"anayasa\w*.*teklif\w*.*(?:salt çoğunluk|360|400|151)\b", False, "Anayasa değişikliği teklifi için üye tamsayısının en az 1/3'ü (200 milletvekili) gerekir.")
            ],
            "correct_value": "1/3 (200 milletvekili)"
        },
        {
            "id": "ANAYASA_MAHKEMESI_UYE_SAYISI",
            "context_keywords": ["anayasa mahkemesi", "aym"],
            "must_match": [
                (r"(?:anayasa mahkemesi|aym)\w*.*(?:11|12|17|21)\s*üye", False, "Anayasa Mahkemesi üye sayısı 15'tir (2017 öncesi 17 idi, Askeri Yargıtay/AYİM üyeleri kaldırıldı).")
            ],
            "correct_value": "15 üye (3 TBMM, 12 Cumhurbaşkanı)"
        },
        {
            "id": "AYM_GOREV_SURESI",
            "context_keywords": ["anayasa mahkemesi", "aym"],
            "must_match": [
                (r"(?:anayasa mahkemesi|aym)\w*.*üye\w*.*(?:4|5|6|9)\s*yıl", False, "AYM üyelerinin görev süresi 12 yıldır (Yeniden seçilemezler, 65 yaş sınırı vardır).")
            ],
            "correct_value": "12 yıl"
        },
        {
            "id": "HSK_UYE_SAYISI",
            "context_keywords": ["hâkimler ve savcılar kurulu", "hsk"],
            "must_match": [
                (r"hsk\w*.*(?:7|11|15|22)\s*üye", False, "HSK 13 üyeden oluşur ve 2 daire halinde çalışır (2017 öncesi 22 idi).")
            ],
            "correct_value": "13 üye (Başkan Adalet Bakanı + Bakan Yardımcısı + 4 CB + 7 TBMM)"
        },
        {
            "id": "SECILME_YASI",
            "context_keywords": ["milletvekili seçilme", "mv seçilme", "seçilme yaşı"],
            "must_match": [
                (r"milletvekili\w*.*seçilme\s*yaşı.*(?:25|30|21)", False, "Milletvekili seçilme yaşı 18'dir (2017 anayasa değişikliği ile 25'ten 18'e indirilmiştir).")
            ],
            "correct_value": "18 yaş"
        },
        {
            "id": "CUMHURBASKANI_SECILME_YASI",
            "context_keywords": ["cumhurbaşkanı seçilme", "cumhurbaşkanı aday"],
            "must_match": [
                (r"cumhurbaşkanı\w*.*seçilme\s*yaşı.*(?:30|35|18)", False, "Cumhurbaşkanı seçilme yaşı 40'tır.")
            ],
            "correct_value": "40 yaş"
        }
    ]

    @classmethod
    def validate_numbers(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Metindeki tüm anayasal ve idari sayısal değerleri tarar,
        çelişkili/yanlış değerleri tespit eder.
        """
        violations = []
        text_lower = text.lower()

        for rule in cls.NUMERICAL_RULES:
            # İlgili bağlam kelimeleri var mı?
            has_context = any(kw in text_lower for kw in rule["context_keywords"])
            if has_context:
                for pattern, allow, err_msg in rule["must_match"]:
                    match = re.search(pattern, text_lower)
                    if match and not allow:
                        # İstisna kontrolü: 'değildir', 'kaldırılmıştır' gibi reddiye ifadeleri
                        start_pos = max(0, match.start() - 30)
                        end_pos = min(len(text_lower), match.end() + 30)
                        surrounding = text_lower[start_pos:end_pos]
                        if "değildir" in surrounding or "kaldırılmıştır" in surrounding or "mülga" in surrounding or "öncesi" in surrounding:
                            continue
                        violations.append(f"Sayısal Bilgi Yanılgısı ({rule['id']}): {err_msg}")

        return len(violations) == 0, violations

numerical_validator = NumericalValidator()
