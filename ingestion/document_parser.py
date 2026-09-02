"""
KPSS Super-Brain V1.5: Çok Katmanlı Doküman Ayrıştırıcı (Document Parser)
Sayfa segmentasyonu, metin normalizasyonu, OCR tespiti ve hata kalıcılığı.
"""
import os
import re
import io
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from pypdf import PdfReader

from brain.models import DocumentPageRecord
from brain.database import db_session
from ingestion.document_manager import document_manager

logger = logging.getLogger("document_parser")


class DocumentParsingError(Exception):
    """Doküman ayrıştırma hatası."""
    pass


class DocumentParser:
    """
    V1.5 Doküman Ayrıştırma ve Sayfa Segmentasyon Motoru.
    Her sayfanın kaynak numarasını (1-indexed), ham ve normalize metnini kalıcı olarak saklar.
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Metin normalizasyonu: Çift boşlukları, anlamsız kontrol karakterlerini temizler,
        fakat noktalama ve paragrafları korur.
        """
        if not text:
            return ""
        # Kontrol karakterlerini temizle (satır sonu ve tab hariç)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # Çoklu boşlukları teke indir
        text = re.sub(r'[ \t]+', ' ', text)
        # Çoklu boş satırları sınırla
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def parse_pdf(self, file_path: str, document_id: str) -> List[DocumentPageRecord]:
        """
        PDF dosyasını sayfa sayfa okur ve DocumentPageRecord listesi üretir.
        """
        if not os.path.exists(file_path):
            raise DocumentParsingError(f"Dosya bulunamadı: {file_path}")

        pages_records: List[DocumentPageRecord] = []

        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)

            if total_pages == 0:
                raise DocumentParsingError("PDF belgesi hiçbir sayfa içermiyor.")

            now_str = datetime.now().isoformat()

            for idx, page in enumerate(reader.pages):
                page_num = idx + 1  # 1-indexed
                raw_text = page.extract_text() or ""
                cleaned = self.normalize_text(raw_text)

                # OCR İhtiyacı / Tespiti: Eğer sayfada metin yoksa veya çok azsa
                is_ocr = False
                ocr_confidence = None
                if len(cleaned.strip()) < 20 and len(page.images) > 0:
                    is_ocr = True
                    ocr_confidence = 0.0  # Tesseract/Vision entegrasyonu olmadığında 0.0
                    cleaned = f"[Taranmış Görsel Sayfa - OCR Gerekli (Sayfa {page_num})]"

                page_id = f"dp_{document_id}_{page_num}"
                record = DocumentPageRecord(
                    page_id=page_id,
                    document_id=document_id,
                    page_number=page_num,
                    raw_text=raw_text,
                    cleaned_text=cleaned,
                    is_ocr=is_ocr,
                    ocr_confidence=ocr_confidence,
                    char_count=len(cleaned),
                    created_at=now_str
                )
                pages_records.append(record)

            return pages_records

        except Exception as e:
            logger.error(f"PDF ayrıştırma hatası ({document_id}): {e}")
            raise DocumentParsingError(f"PDF okuma hatası: {str(e)}")

    def parse_plain_text(self, file_path: str, document_id: str) -> List[DocumentPageRecord]:
        """Düz metin dosyalarını sayfalara (veya tek sayfaya) böler."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        now_str = datetime.now().isoformat()
        cleaned = self.normalize_text(content)
        page_id = f"dp_{document_id}_1"
        return [
            DocumentPageRecord(
                page_id=page_id,
                document_id=document_id,
                page_number=1,
                raw_text=content,
                cleaned_text=cleaned,
                is_ocr=False,
                ocr_confidence=None,
                char_count=len(cleaned),
                created_at=now_str
            )
        ]

    def parse_and_persist(self, document_id: str) -> List[DocumentPageRecord]:
        """
        Dokümanı depolarından okur, ayrıştırır ve v15_document_pages tablosuna yazar.
        Hata durumunda dokümanın durumunu FAILED olarak işaretler ve hatayı kaydeder.
        """
        doc = document_manager.get_document_by_id(document_id)
        if not doc:
            raise DocumentParsingError(f"Belirtilen doküman bulunamadı: {document_id}")

        storage_path = doc["storage_path"]
        mime_type = doc["mime_type"]

        try:
            if mime_type == "application/pdf" or storage_path.lower().endswith(".pdf"):
                pages = self.parse_pdf(storage_path, document_id)
            else:
                pages = self.parse_plain_text(storage_path, document_id)

            # Veritabanına Sayfaları Yaz
            with db_session() as conn:
                cursor = conn.cursor()
                for p in pages:
                    cursor.execute("""
                    INSERT INTO v15_document_pages (
                        page_id, document_id, page_number, raw_text, cleaned_text,
                        is_ocr, ocr_confidence, char_count, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(document_id, page_number) DO UPDATE SET
                        raw_text = excluded.raw_text,
                        cleaned_text = excluded.cleaned_text,
                        is_ocr = excluded.is_ocr,
                        ocr_confidence = excluded.ocr_confidence,
                        char_count = excluded.char_count
                    """, (
                        p.page_id,
                        p.document_id,
                        p.page_number,
                        p.raw_text,
                        p.cleaned_text,
                        1 if p.is_ocr else 0,
                        p.ocr_confidence,
                        p.char_count,
                        p.created_at
                    ))

            document_manager.update_document_status(
                document_id=document_id,
                parsing_status="PARSED",
                parsing_error=None
            )
            return pages

        except Exception as e:
            error_msg = str(e)
            document_manager.update_document_status(
                document_id=document_id,
                parsing_status="FAILED",
                parsing_error=error_msg
            )
            raise DocumentParsingError(f"Doküman ayrıştırma başarısız: {error_msg}")

    def get_document_pages(self, document_id: str) -> List[Dict[str, Any]]:
        """Ayrıştırılmış dokümanın tüm sayfalarını sırayla döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM v15_document_pages
            WHERE document_id = ?
            ORDER BY page_number ASC
            """, (document_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]


document_parser = DocumentParser()
