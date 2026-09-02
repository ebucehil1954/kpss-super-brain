"""
KPSS Super-Brain V1.5: Sınav İstatistikleri ve Yeniden Hesaplanabilir Metrik Motoru (Exam Statistics Engine)
Konu frekansı, soru kalıbı dağılımı, tuzak sıklığı ve kronolojik trend analizleri.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from brain.models import ExamStatisticRecord
from brain.database import db_session, initialize_database

logger = logging.getLogger("exam_statistics_engine")


class ExamStatisticsEngine:
    """
    V1.5 Sınav İstatistik ve Trend Toplama Motoru.
    Kural: İstatistikler türetilmiş ve yeniden inşa edilebilir (rebuildable) kayıtlardır.
    Sınav sıklığı, pedagojik hakikatten ayrı tutulur.
    """

    def __init__(self):
        initialize_database()

    def recompute_all_statistics(self) -> Dict[str, int]:
        """
        Tüm v15_exam_statistics tablosunu temizler ve güncel sorulardan/kalıplardan sıfırdan yeniden hesaplar.
        """
        now_str = datetime.now().isoformat()
        metrics_inserted = 0

        with db_session() as conn:
            cursor = conn.cursor()
            # 1. Eski istatistikleri temizle
            cursor.execute("DELETE FROM v15_exam_statistics")

            # 2. KONU FREKANSI (Topic Frequency)
            cursor.execute("""
            SELECT q.lesson, q.topic_id, e.exam_code, e.year, COUNT(q.question_id) as q_count
            FROM v15_questions q
            JOIN v15_exams e ON q.exam_id = e.exam_id
            GROUP BY q.lesson, q.topic_id, e.exam_code, e.year
            """)
            topic_rows = cursor.fetchall()

            for row in topic_rows:
                lesson, topic_id, exam_code, year, count_val = row
                stat_id = f"stat_tf_{lesson}_{topic_id}_{exam_code}_{year}"
                cursor.execute("""
                INSERT INTO v15_exam_statistics (
                    stat_id, metric_type, metric_key, exam_code, year,
                    count_value, percentage_value, meta_details_json, last_computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stat_id,
                    "TOPIC_FREQ",
                    f"{lesson}:{topic_id}",
                    exam_code,
                    year,
                    count_val,
                    None,
                    json.dumps({"lesson": lesson, "topic_id": topic_id}, ensure_ascii=False),
                    now_str
                ))
                metrics_inserted += 1

            # 3. SORU KALIBI FREKANSI (Pattern Frequency)
            cursor.execute("""
            SELECT p.pattern_code, COUNT(l.link_id) as p_count
            FROM v15_question_pattern_links l
            JOIN v15_question_patterns p ON l.pattern_id = p.pattern_id
            GROUP BY p.pattern_code
            """)
            pat_rows = cursor.fetchall()

            for row in pat_rows:
                code, count_val = row
                stat_id = f"stat_pf_{code.lower()}"
                cursor.execute("""
                INSERT INTO v15_exam_statistics (
                    stat_id, metric_type, metric_key, exam_code, year,
                    count_value, percentage_value, meta_details_json, last_computed_at
                ) VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?)
                """, (
                    stat_id,
                    "PATTERN_FREQ",
                    code,
                    count_val,
                    None,
                    json.dumps({"pattern_code": code}, ensure_ascii=False),
                    now_str
                ))
                metrics_inserted += 1

            # 4. TUZAK TÜRÜ FREKANSI (Trap Frequency)
            cursor.execute("""
            SELECT trap_type, COUNT(trap_id) as t_count
            FROM v15_traps
            GROUP BY trap_type
            """)
            trap_rows = cursor.fetchall()

            for row in trap_rows:
                trap_type, count_val = row
                stat_id = f"stat_tf_{trap_type.lower()}"
                cursor.execute("""
                INSERT INTO v15_exam_statistics (
                    stat_id, metric_type, metric_key, exam_code, year,
                    count_value, percentage_value, meta_details_json, last_computed_at
                ) VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?)
                """, (
                    stat_id,
                    "TRAP_FREQ",
                    trap_type,
                    count_val,
                    None,
                    json.dumps({"trap_type": trap_type}, ensure_ascii=False),
                    now_str
                ))
                metrics_inserted += 1

            # 5. KAVRAM REKÜRANSI (Concept Recurrence from Traps & Focus)
            cursor.execute("""
            SELECT target_concept, COUNT(trap_id) as c_count
            FROM v15_traps
            GROUP BY target_concept
            """)
            concept_rows = cursor.fetchall()

            for row in concept_rows:
                concept, count_val = row
                safe_key = concept.lower().replace(" ", "_")[:50]
                stat_id = f"stat_cf_{safe_key}"
                cursor.execute("""
                INSERT INTO v15_exam_statistics (
                    stat_id, metric_type, metric_key, exam_code, year,
                    count_value, percentage_value, meta_details_json, last_computed_at
                ) VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?)
                """, (
                    stat_id,
                    "CONCEPT_FREQ",
                    concept,
                    count_val,
                    None,
                    json.dumps({"concept": concept}, ensure_ascii=False),
                    now_str
                ))
                metrics_inserted += 1

            # 6. YILLIK VE SINAV BAZLI DAĞILIM (Year & Exam Code Distribution)
            cursor.execute("""
            SELECT e.exam_code, e.year, COUNT(q.question_id) as y_count
            FROM v15_questions q
            JOIN v15_exams e ON q.exam_id = e.exam_id
            GROUP BY e.exam_code, e.year
            """)
            year_rows = cursor.fetchall()

            for row in year_rows:
                exam_code, year, count_val = row
                stat_id = f"stat_yd_{exam_code}_{year}"
                cursor.execute("""
                INSERT INTO v15_exam_statistics (
                    stat_id, metric_type, metric_key, exam_code, year,
                    count_value, percentage_value, meta_details_json, last_computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stat_id,
                    "YEAR_DIST",
                    f"{exam_code}:{year}",
                    exam_code,
                    year,
                    count_val,
                    None,
                    json.dumps({"exam_code": exam_code, "year": year}, ensure_ascii=False),
                    now_str
                ))
                metrics_inserted += 1

        return {"status": "SUCCESS", "metrics_recomputed": metrics_inserted}

    def get_topic_frequency_summary(self) -> List[Dict[str, Any]]:
        """Konu bazlı soru sıklıklarını döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT metric_key, SUM(count_value) as total_questions
            FROM v15_exam_statistics
            WHERE metric_type = 'TOPIC_FREQ'
            GROUP BY metric_key
            ORDER BY total_questions DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_pattern_frequency_summary(self) -> List[Dict[str, Any]]:
        """Soru kalıbı sıklıklarını döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT metric_key as pattern_code, count_value as frequency
            FROM v15_exam_statistics
            WHERE metric_type = 'PATTERN_FREQ'
            ORDER BY frequency DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_trap_frequency_summary(self) -> List[Dict[str, Any]]:
        """Tuzak türü dağılımlarını döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT metric_key as trap_type, count_value as frequency
            FROM v15_exam_statistics
            WHERE metric_type = 'TRAP_FREQ'
            ORDER BY frequency DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_year_distribution_summary(self) -> List[Dict[str, Any]]:
        """Yıllık soru dağılımını döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT exam_code, year, count_value as total_questions
            FROM v15_exam_statistics
            WHERE metric_type = 'YEAR_DIST'
            ORDER BY year DESC, exam_code ASC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]


exam_statistics_engine = ExamStatisticsEngine()
