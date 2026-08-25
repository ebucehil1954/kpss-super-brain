"""
KPSS Super-Brain: Yerel Vektör Hafızası
"""
import os
import json
from typing import List, Dict, Any

class LocalVectorMemory:
    def __init__(self, persist_dir: str = "./data/chroma_db"):
        self.persist_dir = persist_dir
        self.chroma_client = None
        self.collection = None
        self.fallback_storage: List[Dict[str, Any]] = []
        self._init_client()

    def _init_client(self):
        try:
            import chromadb
            os.makedirs(self.persist_dir, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.chroma_client.get_or_create_collection(
                name="kpss_super_brain_kb",
                metadata={"description": "Doğrulanmış KPSS Hafızası"}
            )
        except ImportError:
            os.makedirs(self.persist_dir, exist_ok=True)
            self.fallback_path = os.path.join(self.persist_dir, "fallback_memory.json")
            if os.path.exists(self.fallback_path):
                with open(self.fallback_path, "r", encoding="utf-8") as f:
                    self.fallback_storage = json.load(f)

    def add_knowledge_chunk(self, doc_id: str, text: str, metadata: dict):
        if self.collection:
            self.collection.add(ids=[doc_id], documents=[text], metadatas=[metadata])
        else:
            self.fallback_storage.append({"id": doc_id, "text": text, "metadata": metadata})
            with open(self.fallback_path, "w", encoding="utf-8") as f:
                json.dump(self.fallback_storage, f, ensure_ascii=False, indent=2)

vector_memory = LocalVectorMemory()
