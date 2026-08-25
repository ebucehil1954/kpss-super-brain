"""
KPSS Super-Brain: PostgreSQL + pgvector Veri Ambarı ve Vektör Arama Modülü (pg_database.py)
PostgreSQL 16 ve pgvector (vector(384)) kullanarak semantik kosinüs benzerliği araması yapar.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("KPSS_SUPER_BRAIN")

from config import super_brain_config

# PostgreSQL URL yapılandırması
POSTGRES_URL = os.getenv(
    "DATABASE_URL_PG",
    "postgresql://kpss_user:kpss_secret_password_2026@localhost:5432/kpss_brain"
)

class PgVectorDatabase:
    """
    PostgreSQL + pgvector Semantik Arama ve Depolama Yöneticisi.
    """
    def __init__(self, connection_url: str = POSTGRES_URL):
        self.connection_url = connection_url
        self._connected = False

    def is_available(self) -> bool:
        """PostgreSQL + pgvector bağlantısının aktif olup olmadığını kontrol eder."""
        try:
            import psycopg2
            conn = psycopg2.connect(self.connection_url, connect_timeout=1)
            conn.close()
            return True
        except Exception:
            return False

    def insert_knowledge_embedding(
        self,
        record_id: str,
        lesson: str,
        topic: str,
        title: str,
        content: str,
        embedding: List[float],
        source_type: str = "VIDEO",
        source_url: str = "",
        confidence_score: float = 0.90,
        provenance: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Tek bir bilgi parçasını ve 384-boyutlu embedding vektörünü PostgreSQL pgvector'a kaydeder."""
        try:
            import psycopg2
            with psycopg2.connect(self.connection_url) as conn:
                with conn.cursor() as cur:
                    # pgvector format: '[0.1, 0.2, ...]'
                    emb_str = f"[{','.join(str(x) for x in embedding)}]"
                    cur.execute("""
                    INSERT INTO knowledge_embeddings (
                        record_id, lesson, topic, title, content, embedding,
                        source_type, source_url, confidence_score, provenance
                    ) VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s, %s, %s)
                    ON CONFLICT (record_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        confidence_score = EXCLUDED.confidence_score,
                        provenance = EXCLUDED.provenance;
                    """, (
                        record_id, lesson, topic, title, content, emb_str,
                        source_type, source_url, confidence_score, json.dumps(provenance or {})
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL pgvector kaydı başarısız ({e}).")
            return False

    def search_similar_knowledge(
        self,
        query_embedding: List[float],
        lesson: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.70
    ) -> List[Dict[str, Any]]:
        """
        pgvector '<=>' (kosinüs mesafesi) operatörü ile en yakın bilgi kayıtlarını sorgular.
        Similarity = 1.0 - Cosine Distance
        """
        try:
            import psycopg2
            with psycopg2.connect(self.connection_url) as conn:
                with conn.cursor() as cur:
                    emb_str = f"[{','.join(str(x) for x in query_embedding)}]"
                    
                    query = """
                    SELECT record_id, lesson, topic, title, content, source_type,
                           confidence_score, 1 - (embedding <=> %s::vector) AS similarity
                    FROM knowledge_embeddings
                    """
                    params: List[Any] = [emb_str]

                    if lesson:
                        query += " WHERE lesson = %s"
                        params.append(lesson)

                    query += " ORDER BY embedding <=> %s::vector LIMIT %s;"
                    params.extend([emb_str, top_k])

                    cur.execute(query, tuple(params))
                    rows = cur.fetchall()

                    results = []
                    for r in rows:
                        sim = float(r[7])
                        if sim >= min_similarity:
                            results.append({
                                "record_id": r[0],
                                "lesson": r[1],
                                "topic": r[2],
                                "title": r[3],
                                "content": r[4],
                                "source_type": r[5],
                                "confidence_score": float(r[6]),
                                "similarity": sim
                            })
                    return results
        except Exception as e:
            logger.warning(f"PostgreSQL pgvector arama başarısız ({e}).")
            return []

pg_vector_db = PgVectorDatabase()
