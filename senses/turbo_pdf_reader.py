"""
KPSS Super-Brain: Turbo PDF, Kitap ve Belge Sindirici (Turbo PDF & Book Ingestion Studio v3)
MEB ders kitapları, KPSS konu anlatımı fasikülleri, kanun metinleri ve çıkmış soru PDF'lerini
sayfa sayfa okur, bölümlere ayırır, 9 katmanlı kalkanla doğrular ve bilgi ambarına işler.
"""
import os
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import super_brain_config
from brain.knowledge_store import knowledge_store
from brain.deep_ontology import deep_ontology
from brain.episodic_memory import episodic_memory
from anti_hallucination.fact_checker import fact_checker

class TurboPDFReader:
    UPLOADS_DIR = str(super_brain_config.PDF_UPLOADS_DIR)

    @classmethod
    def read_pdf(cls, file_path: str) -> Dict[str, Any]:
        """PDF dosyasını PyPDF2 veya fitz ile hızlıca okur ve metin çıkarır."""
        if not os.path.exists(file_path):
            return {"success": False, "error": "Dosya bulunamadı", "pages": []}

        pages_text = []
        full_text = ""

        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_p = len(reader.pages)
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text() or ""
                    clean_t = cls._clean_text(t)
                    if clean_t:
                        pages_text.append({"page_number": idx + 1, "text": clean_t})
                        full_text += f"\n--- SAYFA {idx+1} ---\n" + clean_t
            return {
                "success": True,
                "file_path": file_path,
                "total_pages": len(pages_text),
                "pages": pages_text,
                "full_text": full_text
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"PDF okuma hatası: {str(e)}",
                "pages": []
            }

    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Gereksiz satır sonlarını ve boşlukları temizler."""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @classmethod
    async def ingest_book_or_document(
        cls,
        pdf_path: str,
        lesson: str,
        topic: str,
        source_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bir PDF kitabını okur, olguları 9 katmanlı kalkanla doğrular ve bilgi ambarına & derin ontolojiye işler.
        """
        source_name = source_title or os.path.basename(pdf_path)
        is_txt = pdf_path.lower().endswith(".txt")

        pages = []
        if is_txt:
            try:
                with open(pdf_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                pages = [{"page_number": 1, "text": cls._clean_text(content)}]
            except Exception as e:
                return {"success": False, "error": f"TXT okuma hatası: {e}"}
        else:
            res = cls.read_pdf(pdf_path)
            if not res.get("success"):
                return {"success": False, "ingested_chunks": 0, "error": res.get("error")}
            pages = res.get("pages", [])

        ingested = 0
        violations_count = 0
        now_str = datetime.now().isoformat()

        for p in pages:
            text = p.get("text", "")
            if len(text) < 30:
                continue

            # Paragraflara böl (400-600 karakter)
            paragraphs = [text[i:i+600] for i in range(0, len(text), 500)]
            for para in paragraphs:
                if len(para.strip()) < 25:
                    continue

                # 9 Katmanlı Kalkan Denetimi
                is_clean, violation_reason = fact_checker.verify_content(para, topic=topic, lesson=lesson)
                if is_clean:
                    knowledge_store.add_or_reinforce_record(
                        text=para,
                        record_type="FACT",
                        lesson=lesson,
                        topic=topic,
                        subtopic=f"{source_name} - Sayfa {p['page_number']}",
                        confidence=0.99,
                        source={
                            "type": "book_or_pdf",
                            "file": source_name,
                            "page": p["page_number"],
                            "date": now_str
                        },
                        tags=["BOOK_INGEST", "PDF_DOCUMENT", lesson, topic]
                    )
                    ingested += 1
                else:
                    violations_count += 1

        # Epizodik hafızaya kitap sindirme günlüğü yaz
        episodic_memory.record_learning_event(
            event_type="BOOK_INGESTION",
            topic=topic,
            lesson=lesson,
            summary=f"'{source_name}' belgesi sindirildi. {ingested} doğrulanmış bilgi parçacığı hafızaya alındı. {violations_count} mülga/hatalı kısım elendi.",
            details={"file": source_name, "pages": len(pages), "ingested_chunks": ingested, "filtered_violations": violations_count},
            confidence_gain=0.15
        )

        return {
            "success": True,
            "file": source_name,
            "total_pages": len(pages),
            "ingested_chunks": ingested,
            "filtered_violations": violations_count,
            "message": f"'{source_name}' başarıyla sindirildi! +{ingested} doğrulanmış bilgi ambarına mühürlendi."
        }

    @classmethod
    def get_ingested_history(cls) -> List[Dict[str, Any]]:
        """Daha önce yüklenmiş ve sindirilmiş belgelerin geçmişini döner."""
        episodes = episodic_memory.get_recent_episodes(limit=30, event_type="BOOK_INGESTION")
        return [
            {
                "timestamp": ep["timestamp"],
                "lesson": ep["lesson"],
                "topic": ep["topic"],
                "summary": ep["summary"],
                "details": ep.get("details", {})
            }
            for ep in episodes
        ]

turbo_pdf_reader = TurboPDFReader()
