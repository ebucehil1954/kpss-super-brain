"""
KPSS Super-Brain: Otonom Vektör Hafızası ve Anlamsal Bellek Deposu
ChromaDB ve TF-IDF/Cosine Cosine hibrit anlamsal arama motoru.
"""
import os
import json
import math
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import super_brain_config

class VectorMemoryStore:
    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or str(super_brain_config.CHROMADB_DIR)
        self.fallback_file = os.path.join(self.persist_dir, "vector_memory_store.json")
        self.documents: List[Dict[str, Any]] = []
        self.chroma_client = None
        self.collection = None
        
        self._init_backend()
        self._load_fallback()

    def _init_backend(self):
        try:
            import chromadb
            os.makedirs(self.persist_dir, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.chroma_client.get_or_create_collection(
                name="kpss_autonomous_brain",
                metadata={"description": "KPSS Otonom Bilgi ve Soru Hafızası"}
            )
        except Exception:
            self.chroma_client = None
            self.collection = None

    def _load_fallback(self):
        if os.path.exists(self.fallback_file):
            try:
                with open(self.fallback_file, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception:
                self.documents = []

    def _save_fallback(self):
        os.makedirs(self.persist_dir, exist_ok=True)
        with open(self.fallback_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)

    def add_memory(
        self,
        doc_id: str,
        text: str,
        lesson: str,
        topic: str,
        source: str,
        confidence: float = 0.95,
        teacher: Optional[str] = None,
        tags: Optional[List[str]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Yeni bir bilgiyi vektör belleğe işler ve kalıcı hafızaya yazar.
        """
        metadata = {
            "lesson": lesson,
            "topic": topic,
            "source": source,
            "confidence": confidence,
            "teacher": teacher or "GENEL",
            "tags": json.dumps(tags or []),
            "created_at": datetime.now().isoformat(),
            **(extra_metadata or {})
        }

        # ChromaDB Ekleme
        if self.collection:
            try:
                self.collection.upsert(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[metadata]
                )
            except Exception:
                pass

        # Fallback JSON Ekleme / Güncelleme
        existing = next((item for item in self.documents if item["id"] == doc_id), None)
        if existing:
            existing.update({"text": text, "metadata": metadata, "updated_at": datetime.now().isoformat()})
        else:
            self.documents.append({
                "id": doc_id,
                "text": text,
                "metadata": metadata,
                "created_at": datetime.now().isoformat()
            })
        
        self._save_fallback()
        return True

    def delete_memory(self, doc_id: str) -> bool:
        """
        [PHASE 12 CANONICAL TRUTH SOT]
        Kanonik veritabanından silinen bir kaydı vektör belleğinden de tamamen siler.
        Vektör deposu silinmiş kanonik bilginin arkasından bağımsız olarak yaşayamaz.
        """
        if self.collection:
            try:
                self.collection.delete(ids=[doc_id])
            except Exception:
                pass

        self.documents = [d for d in self.documents if d["id"] != doc_id]
        self._save_fallback()
        return True

    def clear_all(self) -> None:
        """Vektör deposunu yeniden inşa için tamamen sıfırlar."""
        if self.collection:
            try:
                self.chroma_client.delete_collection(name="kpss_autonomous_brain")
                self.collection = self.chroma_client.get_or_create_collection(name="kpss_autonomous_brain")
            except Exception:
                pass
        self.documents = []
        self._save_fallback()

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b\w+\b', text) if len(w) > 1]

    def search(
        self,
        query: str,
        top_k: int = 5,
        lesson_filter: Optional[str] = None,
        teacher_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Anlamsal arama ve alaka skoru hesaplama.
        """
        # ChromaDB varsa ve çalışıyorsa
        if self.collection:
            try:
                where_clause = {}
                if lesson_filter:
                    where_clause["lesson"] = lesson_filter
                if teacher_filter:
                    where_clause["teacher"] = teacher_filter

                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where_clause if where_clause else None
                )
                
                output = []
                if results and "documents" in results and results["documents"]:
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    ids = results["ids"][0]
                    for doc_id, doc, meta in zip(ids, docs, metas):
                        output.append({
                            "id": doc_id,
                            "text": doc,
                            "metadata": meta,
                            "score": 0.9
                        })
                    return output
            except Exception:
                pass

        # TF-IDF / Cosine fallback hesaplaması
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return []

        scored = []
        for item in self.documents:
            meta = item.get("metadata", {})
            if lesson_filter and meta.get("lesson") != lesson_filter:
                continue
            if teacher_filter and meta.get("teacher") != teacher_filter:
                continue

            doc_tokens = self._tokenize(item.get("text", ""))
            if not doc_tokens:
                continue

            # Jaccard + Frekans bazlı benzerlik skoru
            intersection = query_tokens.intersection(set(doc_tokens))
            score = len(intersection) / (math.sqrt(len(query_tokens)) * math.sqrt(len(doc_tokens)) + 1e-5)
            
            if score > 0:
                scored.append({
                    "id": item["id"],
                    "text": item["text"],
                    "metadata": meta,
                    "score": round(score, 4)
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """
        Hafıza istatistikleri.
        """
        total = len(self.documents)
        by_lesson = {}
        by_teacher = {}
        for item in self.documents:
            meta = item.get("metadata", {})
            l = meta.get("lesson", "DİĞER")
            t = meta.get("teacher", "GENEL")
            by_lesson[l] = by_lesson.get(l, 0) + 1
            by_teacher[t] = by_teacher.get(t, 0) + 1

        return {
            "total_knowledge_chunks": total,
            "by_lesson": by_lesson,
            "by_teacher": by_teacher,
            "backend": "ChromaDB + JSON Hybrid Store"
        }

vector_memory = VectorMemoryStore()
