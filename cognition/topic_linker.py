"""
KPSS Super-Brain: Konular Arası Bağlantı ve Ontoloji Keşfi (Topic Linker)
Dersler ve konular arasındaki neden-sonuç, kronoloji ve hiyerarşi bağlarını otomatik keşfeder.
"""
from typing import Dict, Any, List
from brain.knowledge_store import knowledge_store

class TopicLinker:
    # Deterministik Temel Ontoloji ve Bağlantı Ağları
    HISTORICAL_TIMELINE = [
        "İlk Türk Devletleri",
        "Türk-İslam Devletleri",
        "Osmanlı Kuruluş ve Yükselme",
        "Osmanlı Duraklama ve Gerileme",
        "18. ve 19. Yüzyıl Islahatları (Tanzimat, Islahat, Meşrutiyet)",
        "XX. Yüzyıl Başlarında Osmanlı ve Trablusgarp/Balkan Savaşları",
        "I. Dünya Savaşı ve Mondros",
        "Milli Mücadele Dönemi (Genelgeler, Kongreler, Muharebeler)",
        "Lozan Barış Antlaşması ve Cumhuriyetin İlanı",
        "Atatürk İlke ve İnkılapları",
        "Çağdaş Türk ve Dünya Tarihi"
    ]

    CONSTITUTIONAL_HIERARCHY = [
        "1. Norm: Anayasa (Madde 11: Anayasanın Bağlayıcılığı ve Üstünlüğü)",
        "2. Norm: Kanunlar ve Milletlerarası Andlaşmalar",
        "3. Norm: Cumhurbaşkanlığı Kararnameleri (CBK)",
        "4. Norm: Yönetmelikler",
        "5. Norm: Genelgeler, Tebliğler ve Adsız Düzenleyici İşlemler"
    ]

    @classmethod
    def get_contextual_links(cls, lesson: str, topic: str) -> List[Dict[str, Any]]:
        """Verilen konunun bağlı olduğu önceki ve sonraki kavram bağlarını döner."""
        links = []
        l_upper = lesson.upper()
        
        if l_upper == "TARIH":
            for idx, period in enumerate(cls.HISTORICAL_TIMELINE):
                if any(w.lower() in topic.lower() for w in period.split()):
                    prev_period = cls.HISTORICAL_TIMELINE[idx - 1] if idx > 0 else None
                    next_period = cls.HISTORICAL_TIMELINE[idx + 1] if idx < len(cls.HISTORICAL_TIMELINE) - 1 else None
                    links.append({
                        "type": "CHRONOLOGICAL_FLOW",
                        "current": period,
                        "preceding": prev_period,
                        "succeeding": next_period,
                        "exam_note": "ÖSYM bu dönemler arasındaki geçiş nedenlerini ve antlaşma sıralamalarını sorar."
                    })
                    break

        elif l_upper == "VATANDASLIK":
            links.append({
                "type": "LEGAL_HIERARCHY",
                "hierarchy": cls.CONSTITUTIONAL_HIERARCHY,
                "exam_note": "Normlar hiyerarşisi alt normun üst norma aykırı olamayacağı kuralına dayanır."
            })

        return links

topic_linker = TopicLinker()
