"""
KPSS Super-Brain V1.5: Doküman Yöneticisi ve Güvenli Depolama (Document Manager)
SHA-256 idempotency, MIME & extension güvenliği, yol geçişi koruması ve kanonik doküman metaverisi.
"""
import os
import re
import hashlib
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime

from config import super_brain_config
from brain.models import (
    DocumentRecord,
    DocumentSourceType,
    DocumentClassification
)
from brain.database import db_session, initialize_database


class DocumentSecurityError(Exception):
    """Doküman güvenlik ve doğrulama hatası."""
    pass


class DocumentManager:
    """
    V1.5 Doküman Depolama ve Metaveri Yöneticisi.
    Idempotent, güvenli ve değişmez dosya saklama ilkelerine bağlıdır.
    """

    ALLOWED_MIME_TYPES = {
        "application/pdf": [".pdf"],
        "text/plain": [".txt"],
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
        "application/msword": [".doc"]
    }

    MAGIC_SIGNATURES = {
        b"%PDF": "application/pdf",
        b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or (super_brain_config.DATA_DIR / "documents"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        initialize_database()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Dosya adını güvenli hale getirir, dizin geçişlerini (../, /) temizler.
        """
        # Sadece dosya adını al (dizin yolunu at)
        base = os.path.basename(filename)
        # Güvenli olmayan karakterleri temizle
        safe_name = re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', base)
        safe_name = safe_name.strip('. ')
        if not safe_name:
            safe_name = f"document_{uuid.uuid4().hex[:8]}.bin"
        return safe_name

    @staticmethod
    def compute_sha256(content_bytes: bytes) -> str:
        """İçeriğin SHA-256 özetini çıkarır."""
        return hashlib.sha256(content_bytes).hexdigest()

    def validate_file(self, content_bytes: bytes, filename: str, mime_type: Optional[str] = None) -> str:
        """
        Dosya boyutu, uzantı ve sihirli sayı (magic bytes) kontrolü yapar.
        Geçerli MIME türünü döner.
        """
        if not content_bytes:
            raise DocumentSecurityError("Yüklenen dosya içeriği boş olamaz.")

        if len(content_bytes) > self.MAX_FILE_SIZE_BYTES:
            raise DocumentSecurityError(f"Dosya boyutu sınırı aşıldı ({len(content_bytes)} > {self.MAX_FILE_SIZE_BYTES} bytes).")

        ext = Path(filename).suffix.lower()

        # Magic bytes kontrolü
        detected_mime = None
        for magic, m_type in self.MAGIC_SIGNATURES.items():
            if content_bytes.startswith(magic):
                detected_mime = m_type
                break

        if detected_mime is None:
            # Düz metin kontrolü
            try:
                content_bytes[:1024].decode('utf-8')
                detected_mime = "text/plain"
            except UnicodeDecodeError:
                detected_mime = mime_type or "application/octet-stream"

        # MIME ve uzantı uyumu kontrolü
        if detected_mime in self.ALLOWED_MIME_TYPES:
            allowed_exts = self.ALLOWED_MIME_TYPES[detected_mime]
            if ext not in allowed_exts and ext not in ('.pdf', '.txt', '.docx', '.doc'):
                raise DocumentSecurityError(f"MIME türü ({detected_mime}) ile dosya uzantısı ({ext}) uyuşmuyor.")
        elif ext == ".pdf":
            # PDF header kontrolü
            if not content_bytes.startswith(b"%PDF"):
                raise DocumentSecurityError("Geçersiz PDF dosya formatı (PDF başlığı bulunamadı).")
            detected_mime = "application/pdf"
        else:
            raise DocumentSecurityError(f"Desteklenmeyen dosya türü: {ext} / {detected_mime}")

        return detected_mime

    def get_document_by_sha256(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        """SHA-256 ile mevcut dokümanı arar (Idempotency kontrolü)."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM v15_documents WHERE sha256 = ?", (sha256_hash,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """ID ile dokümanı döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM v15_documents WHERE document_id = ?", (document_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def ingest_document(
        self,
        content_bytes: bytes,
        filename: str,
        source_type: DocumentSourceType = DocumentSourceType.UPLOAD_MANUAL,
        authority_level: int = 1,
        exam_code: Optional[str] = None,
        year: Optional[int] = None,
        lesson: str = "UNKNOWN",
        topic_id: str = "UNKNOWN",
        classification: DocumentClassification = DocumentClassification.UNKNOWN,
        mime_type: Optional[str] = None
    ) -> DocumentRecord:
        """
        Dokümanı güvenli ve idempotent şekilde sisteme kaydeder.
        Aynı dosya tekrar yüklendiğinde mevcut kaydı döner.
        """
        sanitized_name = self.sanitize_filename(filename)
        valid_mime = self.validate_file(content_bytes, sanitized_name, mime_type)
        sha256_hash = self.compute_sha256(content_bytes)

        # 1. Idempotency Kontrolü
        existing = self.get_document_by_sha256(sha256_hash)
        if existing:
            # Eğer depolama yolundaki dosya silinmişse (örn: geçici test dizini) yeniden oluştur
            existing_path = existing.get("storage_path", "")
            if not os.path.exists(existing_path):
                doc_id = existing["document_id"]
                storage_filename = f"{doc_id}_{sanitized_name}"
                new_storage_path = str(self.storage_dir / storage_filename)
                with open(new_storage_path, "wb") as f:
                    f.write(content_bytes)
                with db_session() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE v15_documents SET storage_path = ? WHERE document_id = ?", (new_storage_path, doc_id))
                existing["storage_path"] = new_storage_path

            return DocumentRecord(**existing)


        # 2. Güvenli Dosya Depolama
        doc_id = f"doc_{sha256_hash[:12]}"
        storage_filename = f"{doc_id}_{sanitized_name}"
        storage_path = str(self.storage_dir / storage_filename)

        with open(storage_path, "wb") as f:
            f.write(content_bytes)

        now_str = datetime.now().isoformat()
        doc_record = DocumentRecord(
            document_id=doc_id,
            sha256=sha256_hash,
            filename=sanitized_name,
            storage_path=storage_path,
            mime_type=valid_mime,
            file_size=len(content_bytes),
            source_type=source_type,
            authority_level=authority_level,
            exam_code=exam_code,
            year=year,
            lesson=lesson,
            topic_id=topic_id,
            classification=classification,
            parsing_status="PENDING",
            created_at=now_str,
            updated_at=now_str
        )

        # 3. Veritabanı Kaydı
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO v15_documents (
                document_id, sha256, filename, storage_path, mime_type, file_size,
                source_type, authority_level, exam_code, year, lesson, topic_id,
                classification, parsing_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_record.document_id,
                doc_record.sha256,
                doc_record.filename,
                doc_record.storage_path,
                doc_record.mime_type,
                doc_record.file_size,
                doc_record.source_type.value,
                doc_record.authority_level,
                doc_record.exam_code,
                doc_record.year,
                doc_record.lesson,
                doc_record.topic_id,
                doc_record.classification.value,
                doc_record.parsing_status,
                doc_record.created_at,
                doc_record.updated_at
            ))

        return doc_record

    def update_document_status(
        self,
        document_id: str,
        parsing_status: str,
        parsing_error: Optional[str] = None,
        lesson: Optional[str] = None,
        topic_id: Optional[str] = None,
        classification: Optional[DocumentClassification] = None
    ):
        """Doküman ayrıştırma veya sınıflandırma durumunu günceller."""
        now_str = datetime.now().isoformat()
        with db_session() as conn:
            cursor = conn.cursor()
            updates = ["parsing_status = ?", "parsing_error = ?", "updated_at = ?"]
            params = [parsing_status, parsing_error, now_str]

            if lesson is not None:
                updates.append("lesson = ?")
                params.append(lesson)
            if topic_id is not None:
                updates.append("topic_id = ?")
                params.append(topic_id)
            if classification is not None:
                updates.append("classification = ?")
                params.append(classification.value)

            params.append(document_id)
            cursor.execute(f"""
            UPDATE v15_documents
            SET {", ".join(updates)}
            WHERE document_id = ?
            """, tuple(params))


document_manager = DocumentManager()
