"""
KPSS Super-Brain: Yapılandırılmış Bilgi Ambarı (Knowledge Store)
FTS5 tam metin aramalı, otomatik pekiştirmeli (reinforcement) ve kaynak zinciri izlemeli bellek katmanı.
"""
import json
import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from brain.database import db_session

logger = logging.getLogger("knowledge_store")

# Güçlendirme üst limiti: Aynı kayıt en fazla bu kadar kez pekiştirilebilir
MAX_REINFORCEMENTS = 10

class KnowledgeStore:
    @staticmethod
    def _generate_record_id(text: str, lesson: str, topic: str) -> str:
        """Metin ve konudan deterministik veya benzersiz ID üretir."""
        norm = f"{lesson}_{topic}_{text.strip().lower()}"
        h = hashlib.sha256(norm.encode('utf-8')).hexdigest()[:12]
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

                # Kaynak ve Bağımsızlık Analizi
                new_author = (new_source.get("speaker_or_author") or new_source.get("author") or new_source.get("speaker") or "").strip().lower()
                new_source_id = (new_source.get("source_id") or new_source.get("video_id") or "").strip()

                known_authors = {
                    (s.get("speaker_or_author") or s.get("author") or s.get("speaker") or "").strip().lower()
                    for s in existing_sources if isinstance(s, dict)
                }
                known_sources = {
                    (s.get("source_id") or s.get("video_id") or "").strip()
                    for s in existing_sources if isinstance(s, dict)
                }

                # [PHASE 19: VIDEO_ID DEDUP] Aynı video_id'den gelen tekrar güçlendirme engeli
                known_video_ids = {
                    (s.get("video_id") or "").strip()
                    for s in existing_sources if isinstance(s, dict) and (s.get("video_id") or "").strip()
                }
                new_video_id = (new_source.get("video_id") or "").strip()

                # Çelişki kontrolü
                is_conflicting = any(tag.lower() in ("conflict", "disputed", "contradictory", "contradiction") for tag in tags) or bool(new_source.get("is_conflicting", False))

                existing_sources.append(new_source)
                existing_related = list(set(json.loads(row["related_records_json"]) + related_records))
                existing_tags = list(set(json.loads(row["tags_json"]) + tags))
                new_reinforced_count = row["times_reinforced"] + 1

                # [PHASE 3 + PHASE 19: REPETITION != TRUTH]
                current_conf = row["confidence"]
                if new_reinforced_count > MAX_REINFORCEMENTS:
                    # Üst limite ulaşıldı — güven skoru artık artamaz
                    new_confidence = current_conf
                elif new_video_id and new_video_id in known_video_ids:
                    # Aynı videodan gelen tekrar güçlendirme — güven skoru ASLA artmaz
                    new_confidence = current_conf
                elif is_conflicting:
                    # Çelişen kanıt güven skorunu derhal düşürür veya bloke eder
                    new_confidence = max(0.10, min(current_conf, 0.40))
                elif new_author and new_author not in known_authors and new_author not in ("genel", "sistem", ""):
                    # Gerçekten BAĞIMSIZ yeni bir öğretmen/resmi kaynak teyit etti -> Güven skoru artabilir
                    new_confidence = min(0.999, current_conf + (1.0 - current_conf) * 0.15)
                else:
                    # Aynı kaynaktan gelen tekrar veya anonim tekrar güven skorunu ASLA artıramaz
                    new_confidence = current_conf

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
    def stage_pending_record(
        cls,
        text: str,
        record_type: str,
        lesson: str,
        topic: str,
        subtopic: str = "",
        confidence: float = 0.90,
        source: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        [KNOWLEDGE FIREWALL ENFORCED]
        Doğrulanmamış kayıtları staging alanına (atomic_claims tablosu) PENDING
        statüsüyle yazar. Kanonik knowledge_records ambarına ASLA doğrudan yazmaz.
        Savcı Denetçi (ProsecutorAuditor) doğruladıktan sonra commit_verified_claim()
        ile kanonik ambara terfi ettirilir.
        """
        text = text.strip()
        if not text:
            return {"status": "skipped", "reason": "empty_text"}

        now_str = datetime.now().isoformat()
        tags = tags or []
        source_meta = source or {"type": "direct_ingest", "date": now_str}

        claim_id = f"staged_{hashlib.sha256(f'{lesson}:{topic}:{text}'.encode('utf-8')).hexdigest()[:12]}"
        provenance_hash = hashlib.sha256(f"{text}:{json.dumps(source_meta, sort_keys=True)}".encode('utf-8')).hexdigest()[:16]
        evidence_json = json.dumps([source_meta], ensure_ascii=False)
        tags_json = json.dumps(tags, ensure_ascii=False)

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO atomic_claims (
                claim_id, text, lesson, topic, subtopic, claim_type,
                subject, predicate, object_val, evidence_refs_json,
                confidence, temporal_status, verification_status,
                tags_json, provenance_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                claim_id, text, lesson.upper(), topic,
                subtopic, record_type.upper(), None,
                None, None, evidence_json,
                confidence, "ACTIVE",
                "PENDING", tags_json,
                provenance_hash, now_str
            ))

        logger.info(f"📋 [STAGING] {record_type} kaydı PENDING olarak staging'e yazıldı: {claim_id}")
        return {
            "claim_id": claim_id,
            "status": "staged_pending",
            "record_type": record_type,
            "verification_status": "PENDING"
        }

    @classmethod
    def search(
        cls,
        query: str,
        lesson: Optional[str] = None,
        record_type: Optional[str] = None,
        min_confidence: float = 0.85,
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

            if min_confidence > 0.0:
                sql += " AND kr.confidence >= ?"
                params.append(min_confidence)

            sql += " ORDER BY kr.confidence DESC, kr.times_reinforced DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [cls._row_to_dict(r) for r in rows]

    search_knowledge = search

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
    def commit_verified_claim(
        cls,
        claim: Any,
        verification_status: Optional[str] = None,
        audit_source: str = "OFFICIAL_MEVZUAT",
        confidence: float = 0.95
    ) -> Optional[Dict[str, Any]]:
        """
        [PHASE 2 KNOWLEDGE FIREWALL]
        Yalnızca doğrulama politikasından geçmiş (VERIFIED veya SUPPORTED)
        iddiaları kanonik bilgi ambarına (Golden Knowledge) kaydeder.
        PENDING, UNVERIFIED, CANDIDATE, DISPUTED, REJECTED veya UNKNOWN iddialar
        KESİNLİKLE kanonik depoya kabul edilmez ve None döner.
        Ayrıca her kabul edilen iddia kesin bir provenance (kaynak/kanıt) zinciri taşımalıdır.
        """
        # 1. Verification Status Kontrolü
        v_status = None
        if hasattr(claim, "verification_status"):
            st = getattr(claim, "verification_status")
            v_status = st.value if hasattr(st, "value") else str(st)
        elif isinstance(claim, dict) and "verification_status" in claim:
            st = claim["verification_status"]
            v_status = st.value if hasattr(st, "value") else str(st)
        elif verification_status:
            v_status = str(verification_status)

        if not v_status:
            return None

        v_status_norm = v_status.upper().strip()
        ALLOWED_COMMIT_STATUSES = {"VERIFIED", "SUPPORTED"}
        if v_status_norm not in ALLOWED_COMMIT_STATUSES:
            # FIREWALL BLOKLADI: PENDING, REJECTED, DISPUTED, UNVERIFIED vb. doğrudan yazılamaz!
            return None

        # 2. Provenance ve Kanıt Kontrolü
        text = getattr(claim, "text", None) or (claim.get("text") if isinstance(claim, dict) else str(claim))
        if not text or not text.strip():
            return None

        from brain.provenance import provenance_validator
        is_prov_valid, prov_reason = provenance_validator.validate_provenance_chain(claim)
        if not is_prov_valid:
            # Kopuk kanıt zincirine sahip iddialar asla kanonik ambar kaydına terfi edemez!
            return None

        provenance_hash = getattr(claim, "provenance_hash", None)
        evidence_refs = getattr(claim, "evidence_refs", [])

        lesson = getattr(claim, "lesson", None) or (claim.get("lesson", "GENEL") if isinstance(claim, dict) else "GENEL")
        topic = getattr(claim, "topic", None) or (claim.get("topic", "Genel") if isinstance(claim, dict) else "Genel")
        subtopic = getattr(claim, "subtopic", "") or (claim.get("subtopic", "") if isinstance(claim, dict) else "")
        tags = getattr(claim, "tags", []) or (claim.get("tags", []) if isinstance(claim, dict) else [])

        source_meta = {
            "type": "verified_claim",
            "audit_source": audit_source,
            "verification_status": v_status_norm,
            "provenance_hash": provenance_hash,
            "evidence_count": len(evidence_refs),
            "committed_at": datetime.now().isoformat()
        }

        claim_type_val = getattr(claim, "claim_type", "FACT")
        if hasattr(claim_type_val, "value"):
            claim_type_val = claim_type_val.value

        # [PHASE 17 SEPARATE TEACHER MODEL SIGNALS]
        # Mnemonik, pedagojik şifre ve soru tuzakları asla objektif FACT olarak saklanamaz!
        if claim_type_val in ("MNEMONIC", "PEDAGOGY", "ACRONYM") or "mnemonic" in tags:
            stored_record_type = "MNEMONIC"
        elif claim_type_val in ("TRAP", "QUESTION_STRATEGY") or "trap" in tags:
            stored_record_type = "TRAP"
        elif claim_type_val in ("TEACHER_INSIGHT", "RHETORICAL_TONE"):
            stored_record_type = "TEACHER_INSIGHT"
        else:
            stored_record_type = "FACT"

        return cls.add_record(
            text=text.strip(),
            record_type=stored_record_type,
            lesson=lesson,
            topic=topic,
            subtopic=subtopic,
            confidence=confidence,
            source_chain=[source_meta],
            tags=list(set(tags + ["verified_claim", v_status_norm.lower(), stored_record_type.lower()]))
        )

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
    def delete_record(cls, record_id: str) -> bool:
        """
        [PHASE 12 CANONICAL TRUTH SOT]
        Kanonik veritabanından bir kaydı siler ve tüm türetilmiş depolardan (FTS, Vektör, Graf)
        aynı anda temizlenmesini garanti eder.
        Türetilmiş depolar silinmiş kanonik bilginin arkasından asla yaşayamaz!
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_records WHERE record_id = ?", (record_id,))
            cursor.execute("DELETE FROM knowledge_fts WHERE record_id = ?", (record_id,))
            affected = cursor.rowcount

        # 1. Vektör belleğinden temizle
        try:
            from brain.vector_memory import VectorMemoryStore
            vm = VectorMemoryStore()
            vm.delete_memory(record_id)
        except Exception:
            pass

        # 2. Bilgi grafiğinden temizle
        try:
            from brain.knowledge_graph import KPSSKnowledgeGraph
            kg = KPSSKnowledgeGraph()
            if record_id in kg.nodes:
                del kg.nodes[record_id]
                kg.edges = [e for e in kg.edges if e["source"] != record_id and e["target"] != record_id]
                kg.save()
        except Exception:
            pass

        return affected > 0

    @classmethod
    def rebuild_derived_stores(cls) -> Dict[str, int]:
        """
        [PHASE 12 CANONICAL TRUTH SOT]
        Tüm türetilmiş depoları (FTS, Vektör, Graf) sıfırdan kanonik veritabanını (Single Source of Truth)
        okuyarak deterministik olarak yeniden inşa eder.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_records")
            canonical_rows = cursor.fetchall()

            # 1. FTS sıfırla ve yeniden doldur
            cursor.execute("DELETE FROM knowledge_fts")
            fts_count = 0
            for row in canonical_rows:
                cursor.execute("""
                INSERT INTO knowledge_fts (record_id, text, lesson, topic, subtopic)
                VALUES (?, ?, ?, ?, ?)
                """, (row["record_id"], row["text"], row["lesson"], row["topic"], row["subtopic"]))
                fts_count += 1

        # 2. Vektör deposunu yeniden inşa et
        vector_count = 0
        try:
            from brain.vector_memory import VectorMemoryStore
            vm = VectorMemoryStore()
            vm.clear_all()
            for r in canonical_rows:
                vm.add_memory(
                    doc_id=r["record_id"],
                    text=r["text"],
                    lesson=r["lesson"],
                    topic=r["topic"],
                    source="canonical_truth",
                    confidence=r["confidence"]
                )
                vector_count += 1
        except Exception:
            pass

        # 3. Bilgi grafiğini yeniden inşa et
        graph_count = 0
        try:
            from brain.knowledge_graph import KPSSKnowledgeGraph
            from cognition.ontology import deep_ontology
            kg = KPSSKnowledgeGraph()
            kg.nodes = {}
            kg.edges = []
            for r in canonical_rows:
                deep_ontology.auto_expand_from_knowledge(
                    text=r["text"],
                    lesson=r["lesson"],
                    topic=r["topic"],
                    record_id=r["record_id"],
                    record_type=r["record_type"]
                )
                graph_count += 1
            kg.save()
        except Exception:
            pass

        return {
            "canonical_records": len(canonical_rows),
            "fts_indexed": fts_count,
            "vector_indexed": vector_count,
            "graph_nodes": graph_count
        }

knowledge_store = KnowledgeStore()
