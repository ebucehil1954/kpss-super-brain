"""
KPSS Super-Brain: Mantık ve Muhakeme Zinciri Ambarı (Reasoning Store)
Yapay zekanın videolardan ve çıkmış sorulardan öğrendiği adım adım düşünme, eleme ve akıl yürütme zincirleri.
"""
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from brain.database import db_session

class ReasoningStore:
    @classmethod
    def save_reasoning_chain(
        cls,
        chain_type: str,
        lesson: str,
        topic: str,
        description: str,
        steps: List[Dict[str, Any]],
        learned_from: Optional[List[str]] = None,
        teacher_source: str = "GENEL",
        chain_id: Optional[str] = None
    ) -> str:
        """Yeni bir mantık yürütme zinciri kaydeder veya günceller."""
        cid = chain_id or f"rc_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now().isoformat()
        learned_from = learned_from or []

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO reasoning_chains (
                chain_id, chain_type, lesson, topic, description,
                steps_json, learned_from_json, teacher_source,
                times_applied, success_rate, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chain_id) DO UPDATE SET
                description = excluded.description,
                steps_json = excluded.steps_json,
                learned_from_json = excluded.learned_from_json,
                teacher_source = excluded.teacher_source,
                updated_at = excluded.updated_at
            """, (
                cid,
                chain_type.upper(),
                lesson.upper(),
                topic,
                description,
                json.dumps(steps, ensure_ascii=False),
                json.dumps(learned_from, ensure_ascii=False),
                teacher_source,
                0,
                1.0,
                now_str,
                now_str
            ))
        return cid

    @classmethod
    def get_chains_for_topic(cls, lesson: str, topic: str) -> List[Dict[str, Any]]:
        """Ders ve konuya ait mantık zincirlerini çeker."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM reasoning_chains
            WHERE lesson = ? AND topic LIKE ?
            ORDER BY times_applied DESC, success_rate DESC
            """, (lesson.upper(), f"%{topic}%"))
            return [cls._row_to_dict(r) for r in cursor.fetchall()]

    @classmethod
    def get_all_chains(cls, limit: int = 200) -> List[Dict[str, Any]]:
        """Tüm mantık zincirlerini getirir."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reasoning_chains ORDER BY updated_at DESC LIMIT ?", (limit,))
            return [cls._row_to_dict(r) for r in cursor.fetchall()]

    @classmethod
    def record_usage(cls, chain_id: str, success: bool):
        """Mantık zincirinin bir soruda uygulanışını ve başarı sonucunu kaydeder."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT times_applied, success_rate FROM reasoning_chains WHERE chain_id = ?", (chain_id,))
            row = cursor.fetchone()
            if row:
                total = row["times_applied"] + 1
                curr_rate = row["success_rate"]
                new_rate = (curr_rate * row["times_applied"] + (1.0 if success else 0.0)) / total
                cursor.execute("""
                UPDATE reasoning_chains
                SET times_applied = ?, success_rate = ?, updated_at = ?
                WHERE chain_id = ?
                """, (total, new_rate, datetime.now().isoformat(), chain_id))

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        return {
            "chain_id": row["chain_id"],
            "chain_type": row["chain_type"],
            "lesson": row["lesson"],
            "topic": row["topic"],
            "description": row["description"],
            "steps": json.loads(row["steps_json"]),
            "learned_from": json.loads(row["learned_from_json"]),
            "teacher_source": row["teacher_source"],
            "times_applied": row["times_applied"],
            "success_rate": row["success_rate"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

reasoning_store = ReasoningStore()
