"""
KPSS Super-Brain V1.5: Sınav Tuzakları ve Çeldirici Zekası (Trap & Distractor Intelligence)
ÖSYM distraktör modellemesi, bilişsel yanılgı türleri ve kanıta dayalı tuzak ambarı.
"""
import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from brain.models import TrapRecord
from brain.database import db_session, initialize_database

logger = logging.getLogger("trap_detector")


class TrapDetector:
    """
    V1.5 Çeldirici ve Bilişsel Yanılgı Analizörü.
    Kural: Zayıf veya kanıtsız spekülasyonlardan evrensel tuzak üretilmez; her tuzak gerçek bir soruya ve bilişsel nedene dayanmalıdır.
    """

    TRAP_TYPES = [
        "CHRONOLOGY_CONFUSION",    # Kronolojik yanılgı (olay sırasını karıştırma)
        "SIMILAR_TERM_CONFUSION",  # Benzer terim karmaşası (fonetik/semantik benzerlik)
        "EXCEPTION_TRAP",          # İstisna tuzağı (genel kural yerine istisna sunma)
        "CAUSE_RESULT_REVERSAL",   # Sebep-sonuç tersyüzü (sonucu sebep gibi gösterme)
        "CONCEPT_SWAP",            # Kavram takası (iki kurum veya kavramın özelliklerini yer değiştirme)
        "NUMBER_SWAP"              # Sayı / oran kaydırma
    ]

    def __init__(self):
        initialize_database()

    def register_trap(
        self,
        topic_id: str,
        target_concept: str,
        distractor_concept: str,
        trap_type: str,
        why_attractive: str,
        supporting_question_id: str,
        confidence: float = 0.85
    ) -> TrapRecord:
        """
        Yeni bir bilişsel tuzak kaydı açar veya mevcut tuzağa destekleyici soru bağlar.
        """
        if trap_type not in self.TRAP_TYPES:
            trap_type = "CONCEPT_SWAP"

        if not supporting_question_id:
            raise ValueError("Tuzak kaydı için en az bir destekleyici soru ID'si (supporting_question_id) zorunludur.")

        if not why_attractive or len(why_attractive.strip()) < 10:
            raise ValueError("Tuzak kaydı için geçerli bir çeldiricilik gerekçesi (why_attractive) zorunludur.")

        trap_id = f"trap_{topic_id.lower()}_{distractor_concept.lower().replace(' ', '_')[:20]}"
        now_str = datetime.now().isoformat()

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM v15_traps WHERE trap_id = ?", (trap_id,))
            row = cursor.fetchone()

            if row:
                existing_questions = json.loads(row["supporting_questions_json"])
                if supporting_question_id not in existing_questions:
                    existing_questions.append(supporting_question_id)
                new_conf = min(0.99, row["confidence"] + 0.05)

                cursor.execute("""
                UPDATE v15_traps
                SET supporting_questions_json = ?,
                    confidence = ?
                WHERE trap_id = ?
                """, (json.dumps(existing_questions, ensure_ascii=False), new_conf, trap_id))

                return TrapRecord(
                    trap_id=trap_id,
                    topic_id=row["topic_id"],
                    target_concept=row["target_concept"],
                    distractor_concept=row["distractor_concept"],
                    trap_type=row["trap_type"],
                    why_attractive=row["why_attractive"],
                    supporting_questions=existing_questions,
                    confidence=new_conf,
                    created_at=row["created_at"]
                )
            else:
                supporting_list = [supporting_question_id]
                record = TrapRecord(
                    trap_id=trap_id,
                    topic_id=topic_id,
                    target_concept=target_concept,
                    distractor_concept=distractor_concept,
                    trap_type=trap_type,
                    why_attractive=why_attractive.strip(),
                    supporting_questions=supporting_list,
                    confidence=confidence,
                    created_at=now_str
                )

                cursor.execute("""
                INSERT INTO v15_traps (
                    trap_id, topic_id, target_concept, distractor_concept,
                    trap_type, why_attractive, supporting_questions_json,
                    confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.trap_id,
                    record.topic_id,
                    record.target_concept,
                    record.distractor_concept,
                    record.trap_type,
                    record.why_attractive,
                    json.dumps(record.supporting_questions, ensure_ascii=False),
                    record.confidence,
                    record.created_at
                ))
                return record

    def get_traps_for_topic(self, topic_id: str) -> List[Dict[str, Any]]:
        """Konu bazlı kayıtlı tuzakları döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM v15_traps
            WHERE topic_id = ?
            ORDER BY confidence DESC
            """, (topic_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def tag_option_as_trap(
        self,
        question_id: str,
        option_key: str,
        trap_type: str
    ) -> bool:
        """
        v15_question_options tablosunda ilgili seçeneği tuzak/çeldirici (is_trap=1) olarak işaretler.
        """
        if trap_type not in self.TRAP_TYPES:
            trap_type = "CONCEPT_SWAP"

        opt_clean = option_key.strip().upper()
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE v15_question_options
            SET is_trap = 1, trap_type = ?
            WHERE question_id = ? AND option_key = ?
            """, (trap_type, question_id, opt_clean))
            return cursor.rowcount > 0

    def list_all_traps(self) -> List[Dict[str, Any]]:
        """Kayıtlı tüm bilişsel sınav tuzaklarını döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM v15_traps
            ORDER BY confidence DESC, created_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]


trap_detector = TrapDetector()
