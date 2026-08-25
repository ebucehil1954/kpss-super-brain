"""
KPSS Super-Brain: Eğitmen Zihniyeti ve Pedagojik Profilleme Motoru (Teacher Profiler)
Popüler KPSS hocalarının anlatım tarzını, odaklandığı noktaları ve soru kalıplarını modeller.
"""
from typing import Dict, Any, List, Optional
from config import super_brain_config

class TeacherProfiler:
    TEACHER_PROFILES: Dict[str, Dict[str, Any]] = {
        "Ramazan Yetgin": {
            "name": "Ramazan Yetgin",
            "lesson": "TARIH",
            "channel": "Benim Hocam",
            "pedagogical_style": "Detaylı, kronolojik, akademik derinliği yüksek, 'ÖSYM bunu ilk kez sorabilir' odaklı.",
            "core_strengths": ["Osmanlı Kültür Medeniyeti", "İnkılap Tarihi ve Antlaşmalar", "İlkler ve Kurucular"],
            "signature_techniques": ["Tarihsel hikayeleştirme", "ÖSYM'nin ters köşe yapabileceği ıslahat detayları"],
            "prediction_style": "Klasikleşmiş kalıpların dışına çıkan, akademik kaynaklardaki dipnot bilgiler",
            "common_mnemonics": ["TAYYAR", "MİLAT", "SÖZ-DİN-YAŞA"]
        },
        "Mehmet Celal Özyıldız": {
            "name": "Mehmet Celal Özyıldız",
            "lesson": "TARIH",
            "channel": "Retro Yayıncılık",
            "pedagogical_style": "Hızlı, hap bilgi odaklı, mizahi kodlamalar, sınav stratejisi ve soru üzerinden genel tekrar.",
            "core_strengths": ["Çağdaş Türk ve Dünya Tarihi", "Savaşlar ve Cepheler", "Milli Mücadele Dönemi"],
            "signature_techniques": ["Öncüllü soruları anında eleme mantığı", "Akılda kalıcı hikayeler"],
            "prediction_style": "Son 5 yılın soru trendlerini harmanlayarak nokta atışı soru yakalama",
            "common_mnemonics": ["ŞİFRELİ KODLAMALAR"]
        },
        "Bayram Meral": {
            "name": "Bayram Meral",
            "lesson": "COGRAFYA",
            "channel": "Benim Hocam",
            "pedagogical_style": "Görsel harita destekli, mekansal ilişkilendirme, TÜİK güncel verilerini anında müfredata işleme.",
            "core_strengths": ["Türkiye'nin Yer Şekilleri", "Madenler ve Enerji", "İklim ve Bitki Örtüsü"],
            "signature_techniques": ["Dilsiz harita üzerinde noktasal soru tahminleri", "Mekansal dağılış ilkeleri"],
            "prediction_style": "TÜİK'in en son açıkladığı tarım/nüfus ve MTA maden sıralamalarından soru üretimi",
            "common_mnemonics": ["KADER (Bakır yatakları: Kastamonu, Artvin, Diyarbakır, Elazığ, Rize)"]
        },
        "Mehmet Eğit": {
            "name": "Mehmet Eğit",
            "lesson": "COGRAFYA",
            "channel": "Mehmet Eğit",
            "pedagogical_style": "Hafıza teknikleri, zihin haritaları, animatif çağrışımlar ile sıfır ezber mantığı.",
            "core_strengths": ["Türkiye Ovaları ve Platoları", "Göller ve Akarsular", "Turizm ve UNESCO Alanları"],
            "signature_techniques": ["Görsel çağrışım zincirleri", "Ses benzerliğiyle şifreleme"],
            "prediction_style": "Ezberlenmesi en zor olan karmaşık coğrafi listeleri şifreli tek bir hikayeye dönüştürme",
            "common_mnemonics": ["Hafıza Teknikleri Haritaları"]
        },
        "Emrah Vahap Özkaraca": {
            "name": "Emrah Vahap Özkaraca",
            "lesson": "VATANDASLIK",
            "channel": "İndeks Akademi",
            "pedagogical_style": "Net, şematik, Anayasa maddelerini tablo ve karar ağaçlarına dökerek anlatma.",
            "core_strengths": ["1982 Anayasası Yasama ve Yürütme", "İdare Hukuku Hiyerarşisi", "Temel Hak ve Ödevler"],
            "signature_techniques": ["TBMM karar yeter sayıları tablosu", "İdari vesayet ve hiyerarşi ayrım kuralları"],
            "prediction_style": "Mülga kanun tuzaklarını adaylara gösterip güncel anayasa sayılarını sorgulatma",
            "common_mnemonics": ["TABLO YÖNTEMİ"]
        },
        "Erdal Kesekler": {
            "name": "Erdal Kesekler",
            "lesson": "VATANDASLIK",
            "channel": "Benim Hocam",
            "pedagogical_style": "Soru çözüm odaklı, kavramlar arası ince ayrımları vurgulayan, pratik anlatım.",
            "core_strengths": ["Yargı ve Yüksek Mahkemeler", "Devlet Organları", "Hukukun Temel Kavramları"],
            "signature_techniques": ["Çeldiricileri doğrudan eleme", "ÖSYM'nin benzer soruları arasındaki nüanslar"],
            "prediction_style": "ÖSYM'nin en çok adayı düşürdüğü 'yüksek mahkeme değildir' tarzı tuzak sorular",
            "common_mnemonics": ["KAVRAM AĞAÇLARI"]
        }
    }

    @classmethod
    def get_teacher_profile(cls, teacher_name: str) -> Optional[Dict[str, Any]]:
        return cls.TEACHER_PROFILES.get(teacher_name)

    @classmethod
    def get_all_profiles(cls) -> Dict[str, Dict[str, Any]]:
        return cls.TEACHER_PROFILES

    @classmethod
    def get_teacher_perspective_for_topic(cls, lesson: str, topic: str) -> List[Dict[str, Any]]:
        """
        Belirli bir ders ve konu için ilgili hocaların yaklaşımlarını listeler.
        """
        relevant = []
        for name, profile in cls.TEACHER_PROFILES.items():
            if profile.get("lesson") == lesson.upper():
                relevant.append({
                    "teacher": name,
                    "channel": profile.get("channel"),
                    "style": profile.get("pedagogical_style"),
                    "prediction_style": profile.get("prediction_style")
                })
        return relevant

teacher_profiler = TeacherProfiler()
