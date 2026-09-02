"""
KPSS Super-Brain V1.5: Bilgi Grafiği Senkronizasyon ve Türetilmiş Görünüm Motoru (Phase 11)
Tüm doküman, iddia, sınav, soru, kalıp ve tuzak varlıklarını deterministik olarak grafiğe bağlar.
Kural 6: Graf kanonik gerçeğin türetilmiş bir temsilidir; silinip sıfırdan yeniden inşa edilebilir.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Set

from brain.database import db_session
from brain.knowledge_graph import kpss_knowledge_graph, KPSSKnowledgeGraph

logger = logging.getLogger("v15_graph_sync")


class V15GraphSynchronizer:
    """
    V1.5 Doküman ve Sınav Zekası için Bilgi Grafiği Eşzamanlayıcı.
    8 varlık türü (CONCEPT, CLAIM, DOCUMENT, VIDEO, QUESTION, PATTERN, TRAP, TEACHER_INSIGHT)
    ve tipik anlamsal kenarları (RELATES_TO, TESTS, USES_PATTERN, CONFUSED_WITH, EVIDENCED_BY, SOURCE_DOC) yönetir.
    """

    def __init__(self, graph: Optional[KPSSKnowledgeGraph] = None):
        self.graph = graph or kpss_knowledge_graph

    def sync_all_v15_entities(self) -> Dict[str, int]:
        """
        Kanonik SQLite tablolarını tarar ve tüm varlıkları düğüm ve kenar olarak bilgi grafiğine yansıtır.
        Tüm düğüm ve kenarlar bellekte toplanıp tek seferde diske kaydedilir (yüksek performans ve kilit direnci).
        """
        counts = {
            "documents_synced": 0,
            "questions_synced": 0,
            "patterns_synced": 0,
            "traps_synced": 0,
            "claims_synced": 0,
            "edges_added": 0
        }

        with db_session() as conn:
            cursor = conn.cursor()

            # 1. DOKÜMANLAR (DOCUMENT NODES)
            cursor.execute("SELECT document_id, filename, source_type, lesson, topic_id, year, exam_code FROM v15_documents")
            doc_rows = cursor.fetchall()
            for doc in doc_rows:
                node_id = f"doc_{doc['document_id']}"
                self.graph.add_node(
                    node_id=node_id,
                    label=doc["filename"],
                    node_type="DOCUMENT",
                    lesson=doc["lesson"] or "GENEL",
                    properties={
                        "document_id": doc["document_id"],
                        "source_type": doc["source_type"],
                        "topic_id": doc["topic_id"],
                        "year": doc["year"],
                        "exam_code": doc["exam_code"]
                    },
                    auto_save=False
                )
                counts["documents_synced"] += 1

            # 2. SORU KALIPLARI (PATTERN NODES)
            cursor.execute("SELECT pattern_id, pattern_code, pattern_name, description, cognitive_level FROM v15_question_patterns")
            pat_rows = cursor.fetchall()
            for pat in pat_rows:
                node_id = f"pat_{pat['pattern_code'].lower()}"
                self.graph.add_node(
                    node_id=node_id,
                    label=pat["pattern_name"],
                    node_type="PATTERN",
                    lesson="GENEL",
                    properties={
                        "pattern_code": pat["pattern_code"],
                        "cognitive_level": pat["cognitive_level"],
                        "description": pat["description"]
                    },
                    auto_save=False
                )
                counts["patterns_synced"] += 1

            # 3. SORULAR (QUESTION NODES & EDGES)
            cursor.execute("""
            SELECT q.question_id, q.exam_id, q.document_id, q.question_number_in_exam,
                   q.lesson, q.topic_id, q.stem_text, q.is_negative, q.extraction_status
            FROM v15_questions q
            """)
            q_rows = cursor.fetchall()
            for q in q_rows:
                q_node_id = f"q_{q['question_id']}"
                self.graph.add_node(
                    node_id=q_node_id,
                    label=f"Soru {q['question_number_in_exam']}: {q['stem_text'][:60]}...",
                    node_type="QUESTION",
                    lesson=q["lesson"],
                    properties={
                        "question_id": q["question_id"],
                        "exam_id": q["exam_id"],
                        "document_id": q["document_id"],
                        "topic_id": q["topic_id"],
                        "is_negative": bool(q["is_negative"]),
                        "extraction_status": q["extraction_status"]
                    },
                    auto_save=False
                )
                counts["questions_synced"] += 1

                # Kenar: QUESTION -> SOURCE_DOC -> DOCUMENT
                if q["document_id"]:
                    doc_node_id = f"doc_{q['document_id']}"
                    if doc_node_id in self.graph.nodes:
                        self.graph.add_edge(q_node_id, doc_node_id, "SOURCE_DOC", weight=1.0, auto_save=False)
                        counts["edges_added"] += 1

                # Kenar: QUESTION -> TESTS -> CONCEPT (Konu düğümü)
                if q["topic_id"] and q["topic_id"] != "UNKNOWN":
                    c_node_id = f"concept_{q['topic_id'].lower()}"
                    if c_node_id not in self.graph.nodes:
                        self.graph.add_node(
                            node_id=c_node_id,
                            label=q["topic_id"],
                            node_type="CONCEPT",
                            lesson=q["lesson"],
                            properties={"topic_id": q["topic_id"]},
                            auto_save=False
                        )
                    self.graph.add_edge(q_node_id, c_node_id, "TESTS", weight=1.0, auto_save=False)
                    counts["edges_added"] += 1

            # 4. SORU-KALIP BAĞLANTILARI (USES_PATTERN EDGES)
            cursor.execute("""
            SELECT l.question_id, p.pattern_code, l.confidence
            FROM v15_question_pattern_links l
            JOIN v15_question_patterns p ON l.pattern_id = p.pattern_id
            """)
            link_rows = cursor.fetchall()
            for lnk in link_rows:
                q_node_id = f"q_{lnk['question_id']}"
                pat_node_id = f"pat_{lnk['pattern_code'].lower()}"
                if q_node_id in self.graph.nodes and pat_node_id in self.graph.nodes:
                    self.graph.add_edge(q_node_id, pat_node_id, "USES_PATTERN", weight=lnk["confidence"], auto_save=False)
                    counts["edges_added"] += 1

            # 5. TUZAKLAR VE BİLİŞSEL YANILGILAR (TRAP NODES & EDGES)
            cursor.execute("SELECT trap_id, topic_id, target_concept, distractor_concept, trap_type, why_attractive, supporting_questions_json, confidence FROM v15_traps")
            trap_rows = cursor.fetchall()
            for tr in trap_rows:
                trap_node_id = f"trap_{tr['trap_id']}"
                self.graph.add_node(
                    node_id=trap_node_id,
                    label=f"Tuzak: {tr['target_concept']} vs {tr['distractor_concept']}",
                    node_type="TRAP",
                    lesson="GENEL",
                    properties={
                        "trap_id": tr["trap_id"],
                        "topic_id": tr["topic_id"],
                        "target_concept": tr["target_concept"],
                        "distractor_concept": tr["distractor_concept"],
                        "trap_type": tr["trap_type"],
                        "why_attractive": tr["why_attractive"],
                        "confidence": tr["confidence"]
                    },
                    auto_save=False
                )
                counts["traps_synced"] += 1

                # Kenar: TRAP -> CONFUSED_WITH -> CONCEPT
                concept_id = f"concept_{tr['target_concept'].lower().replace(' ', '_')}"
                if concept_id not in self.graph.nodes:
                    self.graph.add_node(
                        node_id=concept_id,
                        label=tr["target_concept"],
                        node_type="CONCEPT",
                        lesson="GENEL",
                        properties={"concept_name": tr["target_concept"]},
                        auto_save=False
                    )
                self.graph.add_edge(trap_node_id, concept_id, "CONFUSED_WITH", weight=tr["confidence"], auto_save=False)
                counts["edges_added"] += 1

                # Kenarlar: Destekleyici sorulara bağla (TRAP -> EXEMPLIFIED_BY -> QUESTION)
                try:
                    sup_questions = json.loads(tr["supporting_questions_json"])
                    for q_id in sup_questions:
                        q_node_id = f"q_{q_id}"
                        if q_node_id in self.graph.nodes:
                            self.graph.add_edge(trap_node_id, q_node_id, "EXEMPLIFIED_BY", weight=1.0, auto_save=False)
                            counts["edges_added"] += 1
                except Exception:
                    pass

            # 6. DOĞRULANMIŞ İDDİALAR (CLAIM NODES & EVIDENCED_BY EDGES)
            cursor.execute("""
            SELECT c.claim_id, c.subject, c.predicate, c.object_val, c.raw_statement,
                   c.topic_id, e.document_id, e.page_number
            FROM v15_candidate_claims c
            LEFT JOIN v15_evidence e ON c.evidence_id = e.evidence_id
            WHERE c.audit_status = 'VERIFIED'
            """)
            claim_rows = cursor.fetchall()
            for clm in claim_rows:
                claim_node_id = f"clm_{clm['claim_id']}"
                self.graph.add_node(
                    node_id=claim_node_id,
                    label=clm["raw_statement"][:60] if clm["raw_statement"] else f"{clm['subject']} {clm['predicate']}",
                    node_type="CLAIM",
                    lesson="GENEL",
                    properties={
                        "claim_id": clm["claim_id"],
                        "subject": clm["subject"],
                        "predicate": clm["predicate"],
                        "object_val": clm["object_val"],
                        "topic_id": clm["topic_id"]
                    },
                    auto_save=False
                )
                counts["claims_synced"] += 1

                # Kenar: CLAIM -> EVIDENCED_BY -> DOCUMENT
                if clm["document_id"]:
                    doc_node_id = f"doc_{clm['document_id']}"
                    if doc_node_id in self.graph.nodes:
                        self.graph.add_edge(claim_node_id, doc_node_id, "EVIDENCED_BY", weight=1.0, auto_save=False)
                        counts["edges_added"] += 1

                # Kenar: CLAIM -> RELATES_TO -> CONCEPT
                if clm["topic_id"] and clm["topic_id"] != "UNKNOWN":
                    c_node_id = f"concept_{clm['topic_id'].lower()}"
                    if c_node_id in self.graph.nodes:
                        self.graph.add_edge(claim_node_id, c_node_id, "RELATES_TO", weight=1.0, auto_save=False)
                        counts["edges_added"] += 1

        self.graph.save(force=True)
        return counts

    def rebuild_graph_from_canonical(self) -> Dict[str, Any]:
        """
        Kural 6: Grafiği tamamen sıfırlar ve temel ontoloji + kanonik tablolardan yeniden inşa eder.
        """
        with self.graph._lock:
            self.graph.nodes.clear()
            self.graph.edges.clear()
            self.graph._seed_default_kpss_ontology()

        counts = self.sync_all_v15_entities()
        return {
            "status": "REBUILT",
            "total_nodes": len(self.graph.nodes),
            "total_edges": len(self.graph.edges),
            "sync_details": counts
        }

    def get_subgraph_neighborhood(self, node_id: str, depth: int = 1) -> Dict[str, Any]:
        """Komşuluk alt grafiğini döner."""
        return self.graph.get_neighborhood(node_id=node_id, depth=depth)


v15_graph_sync = V15GraphSynchronizer()
