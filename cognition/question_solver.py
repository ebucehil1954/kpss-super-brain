"""
KPSS Super-Brain V1.5: Soru Çözücü ve Cevap Anahtarı Güvenlik Motoru (Question Solver & Safety)
Resmi cevap anahtarı mutlak otoritedir; LLM uyuşmazlıklarında LLM_DISAGREEMENT bayrağı kaydedilir.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from brain.models import (
    AnswerKeyRecord,
    QuestionResolution
)
from brain.database import db_session, initialize_database


class QuestionSolver:
    """
    V1.5 Soru ve Cevap Anahtarı Uzlaştırma Motoru.
    Kural 7: Resmi cevap anahtarı birincil kanıttır. LLM asla resmi anahtarı ezemez.
    """

    def __init__(self):
        initialize_database()

    def bind_official_answer_key(
        self,
        exam_id: str,
        answer_keys: Dict[int, str],
        source_document_id: Optional[str] = None
    ) -> List[AnswerKeyRecord]:
        """
        Resmi cevap anahtarını veritabanına bağlar ve v15_question_options üzerindeki doğru seçeneği işaretler.
        """
        now_str = datetime.now().isoformat()
        records: List[AnswerKeyRecord] = []

        with db_session() as conn:
            cursor = conn.cursor()
            for q_num, opt_char in answer_keys.items():
                opt_clean = opt_char.strip().upper()
                key_id = f"ak_{exam_id}_{q_num}"
                record = AnswerKeyRecord(
                    key_id=key_id,
                    exam_id=exam_id,
                    question_number=q_num,
                    correct_option=opt_clean,
                    source_document_id=source_document_id,
                    created_at=now_str
                )
                records.append(record)

                cursor.execute("""
                INSERT INTO v15_answer_keys (
                    key_id, exam_id, question_number, correct_option,
                    source_document_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_id, question_number) DO UPDATE SET
                    correct_option = excluded.correct_option
                """, (
                    record.key_id,
                    record.exam_id,
                    record.question_number,
                    record.correct_option,
                    record.source_document_id,
                    record.created_at
                ))

                # İlgili sorunun seçeneğini doğru olarak işaretle
                question_id = f"q_{exam_id}_{q_num}"
                # Önce diğer tüm seçenekleri 0 yap
                cursor.execute("""
                UPDATE v15_question_options
                SET is_correct_official = 0
                WHERE question_id = ?
                """, (question_id,))

                # Doğru seçeneği 1 yap
                cursor.execute("""
                UPDATE v15_question_options
                SET is_correct_official = 1
                WHERE question_id = ? AND option_key = ?
                """, (question_id, opt_clean))

            # Sınavda resmi anahtar var olarak işaretle
            cursor.execute("""
            UPDATE v15_exams
            SET has_official_key = 1
            WHERE exam_id = ?
            """, (exam_id,))

        return records

    def get_official_answer(self, exam_id: str, question_number: int) -> Optional[str]:
        """Soru için resmi cevap anahtarını sorgular."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT correct_option FROM v15_answer_keys
            WHERE exam_id = ? AND question_number = ?
            """, (exam_id, question_number))
            row = cursor.fetchone()
            if row:
                return row["correct_option"]
        return None

    def reconcile_answer(
        self,
        official_key: Optional[str],
        llm_answer: str,
        llm_reasoning: str = ""
    ) -> QuestionResolution:
        """
        Resmi anahtar ile LLM cevabını uzlaştırır.
        
        Kural 1 & 7:
        1. Eğer resmi anahtar yoksa (None veya UNKNOWN) -> final_answer = UNKNOWN.
        2. Eğer LLM ve resmi anahtar uyuşmuyorsa -> final_answer = official_key, LLM_DISAGREEMENT = True.
        3. LLM cevabı ASLA resmi anahtarın yerine geçemez.
        """
        if official_key is None or official_key.strip().upper() == "UNKNOWN":
            return QuestionResolution(
                final_answer="UNKNOWN",
                disagreement_flag=False,
                note="Resmi cevap anahtarı bulunamadı. LLM cevabı tek başına kanonik kılınamaz."
            )

        official_clean = official_key.strip().upper()
        llm_clean = llm_answer.strip().upper()

        if official_clean != llm_clean:
            return QuestionResolution(
                final_answer=official_clean,  # Resmi anahtar DAİMA kazanır
                disagreement_flag=True,
                disagreement_details={
                    "status": "LLM_DISAGREEMENT",
                    "official_key": official_clean,
                    "llm_suggested": llm_clean,
                    "llm_reasoning": llm_reasoning,
                    "resolution_rule": "Official answer key overrides LLM candidate solution."
                },
                note=f"LLM uyuşmazlığı tespit edildi: LLM '{llm_clean}' önerdi, resmi anahtar '{official_clean}' kabul edildi."
            )

        return QuestionResolution(
            final_answer=official_clean,
            disagreement_flag=False,
            note="LLM ve resmi cevap anahtarı tam mutabakat sağladı."
        )


question_solver = QuestionSolver()
