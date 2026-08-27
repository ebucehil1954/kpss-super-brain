"""
KPSS Super-Brain: YouTube Kaynak Evreni ve Altın Standart Eğitmen Kataloğu (Curriculum Sources)
ÖSYM KPSS müfredatında Türkiye'nin en popüler, izlenen ve soru tutturan hoca/kanallarının yapılandırılmış haritası.
"""
from typing import Dict, List, Any
from curriculum.models import LessonType, ExamLevel

# 🏛️ ALTIN STANDART KANALLAR
GOLD_STANDARD_CHANNELS = [
    "Benim Hocam",
    "Hocawebde",
    "İsem TV",
    "Pegem Akademi",
    "Yediiklim",
    "Murat Yayınları",
    "Kuzey Akademi"
]

# 🎓 DERS BAZLI POPÜLER EĞİTMEN KATALOĞU
TEACHER_CATALOG: Dict[LessonType, List[Dict[str, Any]]] = {
    LessonType.TARIH: [
        {"name": "Ramazan Yetgin", "channel": "Benim Hocam", "style": "Kronolojik Hikayeleştirme & Detay Kodlamalar"},
        {"name": "Mehmet Celal Özyıldız", "channel": "İsem TV", "style": "Mizahi ve Duygusal Akılda Kalıcı Anlatım"},
        {"name": "Aydın Yüce", "channel": "Yediiklim", "style": "Nokta Atışı & Soru Çözüm Odaklı"},
        {"name": "Kadir Koç", "channel": "Hocawebde", "style": "Haritalarla Tarih ve Sınav İpuçları"},
        {"name": "Birol Yetimoğlu", "channel": "Pegem Akademi", "style": "Akademik ve Müfredat Uyumlu"}
    ],
    LessonType.COGRAFYA: [
        {"name": "Bayram Meral", "channel": "Benim Hocam", "style": "Görsel Harita Hafızası ve Güncel TÜİK Analizi"},
        {"name": "Engin Eraydın", "channel": "Hocawebde", "style": "Şifreli Kodlamalar ve Sınav Tuzakları Vurgusu"},
        {"name": "Hakan Bileyen", "channel": "İsem TV", "style": "Bölgesel Karşılaştırmalı ve Pratik"},
        {"name": "Rıza Akan", "channel": "Yediiklim", "style": "Konu-Soru Entegrasyonu"}
    ],
    LessonType.VATANDASLIK: [
        {"name": "Erdal Kesekler", "channel": "Benim Hocam", "style": "Maddesel Netlik ve Soru Kalıpları"},
        {"name": "Esra Özkan Karaoğlu", "channel": "Benim Hocam", "style": "Kavram Karşılaştırmaları ve Tablolar"},
        {"name": "Emrah Vahap Özkaraca", "channel": "Hocawebde", "style": "Şematik İdare Hukuku ve Pratik Çözümleme"},
        {"name": "Yasemin Özkanlı", "channel": "İsem TV", "style": "Örnek Olaylar ve Güncel Anayasa Değişiklikleri"}
    ],
    LessonType.TURKCE: [
        {"name": "Yelda Ünal", "channel": "Benim Hocam", "style": "TDK Güncel Kurallar ve Noktalama Taktikleri"},
        {"name": "Aker Kartal", "channel": "Hocawebde", "style": "Dilbilgisi Pratik Metotları ve Hafıza Teknikleri"},
        {"name": "Rüştü Bayındır", "channel": "Rüştü Hoca ile Türkçe", "style": "Paragraf Taktikleri ve Soru Yakalama"},
        {"name": "Önder Hoca", "channel": "İsem TV", "style": "Metin Analizi ve Cümle Anlamı"}
    ],
    LessonType.MATEMATIK: [
        {"name": "İlyas Güneş", "channel": "Benim Hocam", "style": "Temelden Zirveye & Pratik Formülsüz Çözümler"},
        {"name": "Güven Gökkaya", "channel": "Hocawebde", "style": "ÖSYM Soru Tipleri ve Zaman Kazandıran Taktikler"},
        {"name": "Mehmet Bilge Yıldız", "channel": "İsem TV", "style": "Problem Çözme Mantığı ve Analiz"}
    ],
    LessonType.SOZEL_MANTIK: [
        {"name": "Aker Kartal", "channel": "Hocawebde", "style": "Tablo Kurma Sanatı ve İhtimal Eleme"},
        {"name": "Yelda Ünal", "channel": "Benim Hocam", "style": "Değişken Belirleme ve Kısıt Matrisleri"}
    ],
    LessonType.SAYISAL_MANTIK: [
        {"name": "İlyas Güneş", "channel": "Benim Hocam", "style": "Kural Tabanlı Şekil ve Dizi Problemleri"},
        {"name": "Güven Gökkaya", "channel": "Hocawebde", "style": "Hızlı Muhakeme ve Seçenek Analizi"}
    ],
    LessonType.GUNCEL: [
        {"name": "Benim Hocam Güncel", "channel": "Benim Hocam", "style": "Yılın Önemli Olayları ve UNESCO Listeleri"},
        {"name": "Hocawebde Güncel", "channel": "Hocawebde", "style": "Uluslararası Örgütler ve Spor/Sanat Başarıları"}
    ]
}


def get_teachers_for_lesson(lesson: LessonType) -> List[Dict[str, Any]]:
    """Belirli bir ders için popüler hoca listesini döner."""
    return TEACHER_CATALOG.get(lesson, [])


def generate_search_queries(
    lesson: LessonType,
    topic_name: str,
    exam_level: ExamLevel = ExamLevel.ALL,
    max_queries: int = 5
) -> List[str]:
    """
    Hedef konu ve sınav türü için YouTube'da en yüksek bilgi değerine sahip
    akıllı arama sorguları üretir.
    """
    exam_prefix = ""
    if exam_level == ExamLevel.LISANS:
        exam_prefix = "KPSS Lisans"
    elif exam_level == ExamLevel.ONLISANS:
        exam_prefix = "KPSS Ön Lisans"
    elif exam_level == ExamLevel.ORTAOGRETIM:
        exam_prefix = "KPSS Ortaöğretim"
    else:
        exam_prefix = "KPSS"

    lesson_str = lesson.value.capitalize()
    queries = [
        f"{exam_prefix} {lesson_str} {topic_name} konu anlatımı",
        f"{exam_prefix} {topic_name} çıkmış soru çözümü",
        f"{exam_prefix} {lesson_str} {topic_name} tekrar ve kritik bilgiler"
    ]

    # Popüler hoca isimleriyle zenginleştir
    teachers = get_teachers_for_lesson(lesson)
    for t in teachers[:2]:
        queries.append(f"{t['name']} {topic_name} {lesson_str}")

    return queries[:max_queries]
