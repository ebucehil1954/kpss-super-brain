"""
KPSS Super-Brain: Deterministik Konu ve Bilgi Grafiği (DAG)
"""
class KPSSKnowledgeGraph:
    ANAYASA_SAYILARI = {
        "TBMM_UYE_SAYISI": 600,
        "SECIM_YENILEME_COGUNLUGU": "3/5 (360 Milletvekili)",
        "ANAYASA_DEGISIKLIGI_TEKLIF": "1/3 (200 Milletvekili)",
        "ANAYASA_DEGISIKLIGI_REFERANDUMSUZ": "2/3 (400 Milletvekili)",
        "SIYASI_PARTI_GRUBU": 20,
        "SIYASI_PARTI_KURULUSU": 30,
        "AYM_UYE_SAYISI": 15,
        "AYM_GOREV_SURESI": "12 Yıl",
        "HSK_UYE_SAYISI": 13,
        "SECILME_YASI": 18,
        "CUMHURBASKANI_SECILME_YASI": 40
    }

    OSMANLI_ISLAHATLARI = {
        "LALE_DEVRI": {
            "padisah": "III. Ahmet",
            "donem": "1718-1730",
            "islahtlar": ["İlk özel Türk matbaası", "Tulumbacılar ocağı", "Çiçek aşısı", "Tercüme heyetleri"]
        },
        "NIZAM_I_CEDIT": {
            "padisah": "III. Selim",
            "donem": "1789-1807",
            "islahtlar": ["Nizam-ı Cedit Ordusu", "İrad-ı Cedit Hazinesi", "İlk daimi elçilikler (Londra)"]
        }
    }

    @classmethod
    def verify_fact(cls, topic_key: str, candidate_text: str) -> bool:
        if topic_key in cls.ANAYASA_SAYILARI:
            expected = str(cls.ANAYASA_SAYILARI[topic_key])
            return expected.lower() in candidate_text.lower()
        return True
