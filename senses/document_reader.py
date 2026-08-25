"""
KPSS Super-Brain: Doküman ve Müfredat Okuyucu (Document Reader)
MEB ders kitapları, kanun metinleri ve ders notlarını PDF/TXT formatından okuyup hafızaya aktarır.
"""
import os
from typing import List, Dict, Any, Optional
from PyPDF2 import PdfReader
from config import super_brain_config
from brain.vector_memory import vector_memory
from brain.episodic_memory import episodic_memory

class DocumentReader:
    @classmethod
    def read_pdf(cls, file_path: str) -> str:
        text = ""
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        except Exception as e:
            print(f"PDF Okuma Hatası: {e}")
        return text

    @classmethod
    def chunk_and_ingest_file(
        cls,
        file_path: str,
        lesson: str,
        topic: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> int:
        """
        Dosyayı okur, parçalara böler ve vektör hafızaya ekler.
        """
        if not os.path.exists(file_path):
            return 0

        filename = os.path.basename(file_path)
        content = ""
        if file_path.lower().endswith(".pdf"):
            content = cls.read_pdf(file_path)
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                return 0

        words = content.split()
        if not words:
            return 0

        chunks = []
        step = chunk_size - chunk_overlap
        for i in range(0, len(words), step):
            chunk_text = " ".join(words[i:i + chunk_size])
            if len(chunk_text.strip()) > 30:
                chunks.append(chunk_text)

        ingested = 0
        for idx, chunk in enumerate(chunks):
            doc_id = f"doc_{filename[:15]}_{idx}_{int(os.path.getsize(file_path))}"
            vector_memory.add_memory(
                doc_id=doc_id,
                text=chunk,
                lesson=lesson,
                topic=topic,
                source=f"Doküman ({filename})",
                confidence=0.99,
                tags=["DOCUMENT_READER", lesson, topic, filename]
            )
            ingested += 1

        episodic_memory.record_learning_event(
            event_type="DOCUMENT_INGEST",
            topic=topic,
            lesson=lesson,
            summary=f"'{filename}' dokümanı okundu ve {ingested} bilgi parçası hafızaya işlendi.",
            details={"file_name": filename, "chunks": ingested},
            confidence_gain=0.1
        )

        return ingested

document_reader = DocumentReader()
