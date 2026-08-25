"""
KPSS Super-Brain: Yapılandırılmış Bilgi Ambarı (Knowledge Store)
FTS5 tam metin aramalı, otomatik pekiştirmeli (reinforcement) ve kaynak zinciri izlemeli bellek katmanı.
"""
import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from brain.database import db_session

class KnowledgeStore:
    @staticmethod
    def _generate_record_id(text: str, lesson: str, topic: str) -> str:
        """Metin ve konudan deterministik veya benzersiz ID üretir."""
        norm = f"{lesson}_{topic}_{text.strip().lower()}"
        h = hashlib.md5(norm.encode('utf-8')).hexdigest()[:12]
        return f"kr_{h}"

    @classmethod
    def add_or_reinforce_record(
        cls,
        text: str,
        record_type: str,
        lesson: str,
        topic: str,
        subtopic: str = "",
        confidence: float = 0.95,
        source: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        related_records: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Yeni bir bilgiyi ekler veya aynı/benzer bilgi zaten varsa pekiştirir (reinforce eder).
        """
        text = text.strip()
        record_id = cls._generate_record_id(text, lesson, topic)
        now_str = datetime.now().isoformat()
        tags = tags or []
        related_records = related_records or []
        new_source = source or {"type": "direct_ingest", "date": now_str}

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_records WHERE record_id = ?", (record_id,))
            row = cursor.fetchone()

            if row:
                # Bilgi daha önce öğrenilmiş → Pekiştir (Reinforce)
                existing_sources = json.loads(row["source_chain_json"])
                existing_sources.append(new_source)
                existing_related = list(set(json.loads(row["related_records_json"]) + related_records))
                existing_tags = list(set(json.loads(row["tags_json"]) + tags))
                new_reinforced_count = row["times_reinforced"] + 1
                # Güven skoru her pekiştirmede artar (asemptotik olarak 0.999'a yaklaşır)
                new_confidence = min(0.999, row["confidence"] + (1.0 - row["confidence"]) * 0.2)

                cursor.execute("""
                UPDATE knowledge_records
                SET times_reinforced = ?,
                    confidence = ?,
                    source_chain_json = ?,
                    related_records_json = ?,
                    tags_json = ?,
                    last_reinforced = ?
                WHERE record_id = ?
                """, (
                    new_reinforced_count,
                    new_confidence,
                    json.dumps(existing_sources, ensure_ascii=False),
                    json.dumps(existing_related, ensure_ascii=False),
                    json.dumps(existing_tags, ensure_ascii=False),
                    now_str,
                    record_id
                ))
                
                # FTS güncelle
                cursor.execute("DELETE FROM knowledge_fts WHERE record_id = ?", (record_id,))
                cursor.execute("""
                INSERT INTO knowledge_fts (record_id, text, lesson, topic, subtopic)
                VALUES (?, ?, ?, ?, ?)
                """, (record_id, text, lesson, topic, subtopic))

                return {
                    "record_id": record_id,
                    "action": "reinforced",
                    "times_reinforced": new_reinforced_count,
                    "confidence": new_confidence
                }
            else:
                # Tamamen yeni bilgi kaydı
                sources_list = [new_source]
                cursor.execute("""
                INSERT INTO knowledge_records (
                    record_id, text, record_type, lesson, topic, subtopic,
                    confidence, source_chain_json, related_records_json,
                    times_reinforced, first_learned, last_reinforced, tags_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_id,
                    text,
                    record_type.upper(),
                    lesson.upper(),
                    topic,
                    subtopic,
                    confidence,
                    json.dumps(sources_list, ensure_ascii=False),
                    json.dumps(related_records, ensure_ascii=False),
                    1,
                    now_str,
                    now_str,
                    json.dumps(tags, ensure_ascii=False)
                ))

                # FTS'e ekle
                cursor.execute("""
                INSERT INTO knowledge_fts (record_id, text, lesson, topic, subtopic)
                VALUES (?, ?, ?, ?, ?)
                """, (record_id, text, lesson.upper(), topic, subtopic))

                # Dinamik Ontoloji ve Bilgi Grafiği Genişletme
                try:
                    from brain.deep_ontology import deep_ontology
                    deep_ontology.auto_expand_from_knowledge(text, lesson, topic, subtopic)
                except Exception:
                    pass

                return {
                    "record_id": record_id,
                    "action": "created",
                    "times_reinforced": 1,
                    "confidence": confidence
                }

    @classmethod
    def search(
        cls,
        query: str,
        lesson: Optional[str] = None,
        record_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """FTS5 ve filtrelere göre bilgi arar."""
        with db_session() as conn:
            cursor = conn.cursor()
            
            clean_q = query.replace('"', '').replace("'", "").strip()
            if clean_q:
                # FTS5 Arama
                fts_query = f'"{clean_q}"*'
                sql = """
                SELECT kr.* FROM knowledge_records kr
                JOIN knowledge_fts fts ON kr.record_id = fts.record_id
                WHERE knowledge_fts MATCH ?
                """
                params = [fts_query]
            else:
                sql = "SELECT kr.* FROM knowledge_records kr WHERE 1=1"
                params = []

            if lesson:
                sql += " AND kr.lesson = ?"
                params.append(lesson.upper())
            if record_type:
                sql += " AND kr.record_type = ?"
                params.append(record_type.upper())

            # Truth Gate (P1-10): Doğrulanmamış düşük güvenli kayıtları filtrele
            sql += " AND kr.confidence >= 0.85"

            sql += " ORDER BY kr.confidence DESC, kr.times_reinforced DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [cls._row_to_dict(r) for r in rows]

    @classmethod
    def get_records_by_topic(cls, lesson: str, topic: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Belirli bir ders ve konudaki tüm bilgileri çeker."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM knowledge_records
            WHERE lesson = ? AND topic LIKE ?
            ORDER BY confidence DESC, times_reinforced DESC
            LIMIT ?
            """, (lesson.upper(), f"%{topic}%", limit))
            return [cls._row_to_dict(r) for r in cursor.fetchall()]

    @classmethod
    def get_all_records(cls, limit: int = 2000) -> List[Dict[str, Any]]:
        """Tüm bilgi kayıtlarını döndürür."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_records ORDER BY last_reinforced DESC LIMIT ?", (limit,))
            return [cls._row_to_dict(r) for r in cursor.fetchall()]

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """İstatistikleri ve ders dağılımını hesaplar."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM knowledge_records")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT lesson, COUNT(*) as count FROM knowledge_records GROUP BY lesson")
            by_lesson = {row["lesson"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT record_type, COUNT(*) as count FROM knowledge_records GROUP BY record_type")
            by_type = {row["record_type"]: row["count"] for row in cursor.fetchall()}

            return {
                "total_records": total,
                "by_lesson": by_lesson,
                "by_type": by_type
            }

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        return {
            "record_id": row["record_id"],
            "text": row["text"],
            "record_type": row["record_type"],
            "lesson": row["lesson"],
            "topic": row["topic"],
            "subtopic": row["subtopic"],
            "confidence": row["confidence"],
            "source_chain": json.loads(row["source_chain_json"]),
            "related_records": json.loads(row["related_records_json"]),
            "times_reinforced": row["times_reinforced"],
            "first_learned": row["first_learned"],
            "last_reinforced": row["last_reinforced"],
            "tags": json.loads(row["tags_json"])
        }

    @classmethod
    def add_record(cls, text: str, record_type: str, lesson: str, topic: str, subtopic: str = "", confidence: float = 0.95, source_chain: Optional[List[Dict[str, Any]]] = None, tags: Optional[List[str]] = None, related_records: Optional[List[str]] = None):
        """add_or_reinforce_record için takma ad (alias)."""
        source = source_chain[0] if source_chain else None
        return cls.add_or_reinforce_record(
            text=text,
            record_type=record_type,
            lesson=lesson,
            topic=topic,
            subtopic=subtopic,
            confidence=confidence,
            source=source,
            tags=tags,
            related_records=related_records
        )

    @classmethod
    def search_knowledge(cls, query: str, lesson: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """search için takma ad (alias)."""
        return cls.search(query=query, lesson=lesson, limit=limit)

knowledge_store = KnowledgeStore()
