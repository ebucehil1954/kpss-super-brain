"""
KPSS Super-Brain: Soru Kalıpları ve ÖSYM Arketip Öğrenme Motoru (Pattern Learner)
ÖSYM'nin çıkmış soru eğilimlerini ve hocaların tespit ettiği sınav kalıplarını modeller.
"""
from typing import Dict, Any, List
from datetime import datetime
from brain.database import db_session

class PatternLearner:
    CORE_PATTERNS = [
        {
            "pattern_id": "pt_negative_stem",
            "name": "Olumsuz Soru Kökü (Hangisi Söylenemez / Değildir)",
            "lesson": "GENEL",
            "topic": "Tüm Konular",
            "frequency_analysis": "ÖSYM KPSS sınavlarının %35-40'ını oluşturur.",
            "solving_strategy": "4 doğru 1 yanlış aranır. Mutlak ve kesinlik bildiren (asla, sadece, yalnızca) ifadelere odaklan.",
            "common_traps": ["Doğru bilgiye hemen atlayıp soru kökünün 'değildir' dediğini unutmak"],
            "teacher_tips": {
                "Ramazan Yetgin": "Önce soru kökündeki olumsuz kelimenin altını çiz, sonra şıklara geç.",
                "Erdal Kesekler": "Olumsuz kökte 4 şık birbiriyle uyumludur, uyumsuz olan sırıtır."
            }
        },
        {
            "pattern_id": "pt_multiple_premises",
            "name": "Çoklu Öncüllü Çıkarım (I-II-III Yalnız I / I ve III)",
            "lesson": "TARIH",
            "topic": "Tarih ve Vatandaşlık",
            "frequency_analysis": "Tarih testinin en az 6-8 sorusu bu kalıptadır.",
            "solving_strategy": "Kesinlikle yanlış olan bir öncülü bulup o öncülü içeren tüm şıkları ele (Şık eleme metodu).",
            "common_traps": ["Öncülde verilen bilginin doğru olması fakat soru kökündeki amaca hizmet etmemesi"],
            "teacher_tips": {
                "Mehmet Celal Özyıldız": "Bir öncülü elediğinde genelde 2 şıkka inersin, sakin kal ve ikinci öncüle bak."
            }
        },
        {
            "pattern_id": "pt_chronology_sequence",
            "name": "Kronolojik Sıralama ve Antlaşma/Olay Dizilimi",
            "lesson": "TARIH",
            "topic": "İnkılap Tarihi ve Islahatlar",
            "frequency_analysis": "Her yıl en az 2 adet net kronoloji sorusu gelir.",
            "solving_strategy": "Dönem (Nizamı Cedit -> Tanzimat -> Meşrutiyet) ve Padişah eşleştirmesi ile sırala.",
            "common_traps": ["Tanzimat Fermanı (1839) ile Islahat Fermanı (1856) sırasını karıştırmak"],
            "teacher_tips": {
                "Ramazan Yetgin": "Padişah sıralaması kronolojinin omurgasıdır."
            }
        },
        {
            "pattern_id": "pt_geography_map_distribution",
            "name": "Mekansal Dağılış ve Harita Üzerinde Taralı Alan",
            "lesson": "COGRAFYA",
            "topic": "Madenler, İklim, Nüfus",
            "frequency_analysis": "18 coğrafya sorusunun 5-6 tanesi doğrudan harita üzerindendir.",
            "solving_strategy": "Marmara/Ege/Akdeniz/Karadeniz/İç Anadolu/Doğu/Güneydoğu bölgelerinin karakteristik maden ve iklim haritasını hatırla.",
            "common_traps": ["Bakır ile Boksit yataklarının harita yerlerini karıştırmak"],
            "teacher_tips": {
                "Bayram Meral": "Dilsiz harita üzerine kodlama yapmadan coğrafya çalışılmaz."
            }
        }
    ]

    @classmethod
    def initialize_default_patterns(cls):
        """Varsayılan kalıpları veritabanına işler."""
        now_str = datetime.now().isoformat()
        import json
        with db_session() as conn:
            cursor = conn.cursor()
            for p in cls.CORE_PATTERNS:
                cursor.execute("""
                INSERT INTO exam_patterns (
                    pattern_id, name, lesson, topic, frequency_analysis,
                    solving_strategy, common_traps_json, teacher_tips_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pattern_id) DO UPDATE SET
                    solving_strategy = excluded.solving_strategy,
                    teacher_tips_json = excluded.teacher_tips_json,
                    updated_at = excluded.updated_at
                """, (
                    p["pattern_id"],
                    p["name"],
                    p["lesson"],
                    p["topic"],
                    p["frequency_analysis"],
                    p["solving_strategy"],
                    json.dumps(p["common_traps"], ensure_ascii=False),
                    json.dumps(p["teacher_tips"], ensure_ascii=False),
                    now_str,
                    now_str
                ))

    @classmethod
    def get_all_patterns(cls) -> List[Dict[str, Any]]:
        """Tüm sınav kalıplarını çeker."""
        import json
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM exam_patterns")
            rows = cursor.fetchall()
            return [{
                "pattern_id": r["pattern_id"],
                "name": r["name"],
                "lesson": r["lesson"],
                "topic": r["topic"],
                "frequency_analysis": r["frequency_analysis"],
                "solving_strategy": r["solving_strategy"],
                "common_traps": json.loads(r["common_traps_json"]),
                "teacher_tips": json.loads(r["teacher_tips_json"]),
                "updated_at": r["updated_at"]
            } for r in rows]

pattern_learner = PatternLearner()
pattern_learner.initialize_default_patterns()
