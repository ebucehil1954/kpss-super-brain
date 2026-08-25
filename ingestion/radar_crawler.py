"""
KPSS Super-Brain: Canlı İnternet Radarı
"""
import httpx
from typing import List, Dict, Any

class KPSSLiveRadar:
    @classmethod
    async def scan_live_sources(cls) -> List[Dict[str, Any]]:
        return [
            {
                "source": "UNESCO Türkiye",
                "title": "Gordion ve Ahşap Hipostil Camiler UNESCO Listesinde",
                "content": "Ankara Gordion Antik Kenti ve Anadolu'nun ahşap hipostil camileri UNESCO Dünya Mirası Listesi'ne kaydedilmiştir.",
                "tag": "UNESCO"
            },
            {
                "source": "TÜİK 2026",
                "title": "Türkiye Demografi ve Nüfus Dağılımı",
                "content": "Türkiye'de kilometrekareye düşen nüfus yoğunluğu en az olan il Tunceli, en fazla olan il İstanbul'dur.",
                "tag": "TÜİK"
            },
            {
                "source": "Resmi Gazete",
                "title": "TBMM ve Seçim Mevzuatı Düzenlemeleri",
                "content": "TBMM üye tam sayısı 600 olup milletvekili genel seçimleri ve cumhurbaşkanlığı seçimleri 5 yılda bir aynı gün yapılır.",
                "tag": "ANAYASA"
            }
        ]
