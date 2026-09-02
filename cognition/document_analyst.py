"""
KPSS Super-Brain V1.5: Doküman Kanıt ve Pedagojik İddia Analisti (Document Analyst)
12 temel iddia türü ayrıştırma, kanıt-öncelikli şemalama ve aday iddia havuzu oluşturma.
"""
import re
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from brain.models import (
    V15EvidenceRecord,
    V15CandidateClaimRecord,
    V15AuditStatus
)
from brain.database import db_session


class DocumentAnalyst:
    """
    V1.5 Doküman Sayfalarından Kanıt ve Aday İddia (Candidate Claim) Çıkarıcı.
    Asla doğrudan kanonik bilgiye yazmaz; önce kanıt oluşturur, ardından aday havuzuna aktarır.
    """

    CLAIM_PATTERNS = [
        # 1. TANIM (DEFINITION)
        (r"([^.]+?\s+(?:denir|olarak adlandırılır|anlamına gelir|tanımlanır)\.)", "DEFINITION"),
        # 2. İSTİSNA (EXCEPTION)
        (r"([^.]+?\s+(?:hariçtir|istisnadır|kapsamı dışındadır|yer almaz|aykırıdır)\.)", "EXCEPTION"),
        # 3. SEBEP-SONUÇ (CAUSE_EFFECT)
        (r"([^.]+?\s+(?:sonucunda|nedeniyle|sebebiyle|yol açmıştır|ortam hazırlamıştır)\.)", "CAUSE_EFFECT"),
        # 4. TARİH / ZAMAN (DATE)
        (r"([^.]+?\s+(?:\d{4}\s*yılında|\d{1,2}\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+\s+\d{4}|tarihinde)\s+[^.]+?\.)", "DATE"),
        # 5. SAYISAL / ORAN (NUMBER)
        (r"([^.]+?\s+(?:\d+\s+kişi|%[0-9]+|\d+\s+yıl|\d+\s+üye|çoğunluğu)\s+[^.]+?\.)", "NUMBER"),
        # 6. KARŞILAŞTIRMA (COMPARISON)
        (r"([^.]+?\s+(?:aksine|farklı olarak|daha önemlidir|kıyasla|benzer şekilde)\s+[^.]+?\.)", "COMPARISON"),
        # 7. SÜREÇ (PROCESS)
        (r"([^.]+?\s+(?:önce|sonra|sırasıyla|aşamasında|yoluyla gerçekleşir)\.)", "PROCESS"),
        # 8. KURAL / HUKUK (RULE)
        (r"([^.]+?\s+(?:şarttır|zorunludur|yasaktır|hükmü amirdir|hakkına sahiptir)\.)", "RULE"),
        # 9. HOCA İPUCU / DERS NOTU (TEACHING_INSIGHT)
        (r"([^.]+?\s+(?:dikkat|şifresi|unutmayın|sınavda çıkar|kodlama|taktiği)\s*[:\-]\s*[^.]+?\.)", "TEACHING_INSIGHT"),
    ]

    def create_evidence(
        self,
        document_id: str,
        page_number: int,
        evidence_text: str,
        section_id: Optional[str] = None
    ) -> V15EvidenceRecord:
        """
        Doküman sayfası metninden benzersiz ve kalıcı bir kanıt kaydı oluşturur.
        """
        now_str = datetime.now().isoformat()
        evidence_id = f"ev_doc_{document_id}_p{page_number}_{uuid.uuid4().hex[:6]}"
        record = V15EvidenceRecord(
            evidence_id=evidence_id,
            source_type="DOCUMENT",
            document_id=document_id,
            page_number=page_number,
            section_id=section_id or f"sec_p{page_number}",
            evidence_text=evidence_text.strip(),
            created_at=now_str
        )

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO v15_evidence (
                evidence_id, source_type, document_id, page_number, section_id,
                evidence_text, content_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.evidence_id,
                record.source_type,
                record.document_id,
                record.page_number,
                record.section_id,
                record.evidence_text,
                record.content_hash,
                record.created_at
            ))

        return record

    def extract_candidate_claims_from_page(
        self,
        document_id: str,
        page_number: int,
        page_text: str,
        topic_id: str = "UNKNOWN"
    ) -> List[V15CandidateClaimRecord]:
        """
        Sayfa metnini analiz eder, kanıt kaydı açar ve aday iddiaları çıkararak
        v15_candidate_claims tablosuna CANDIDATE durumunda ekler.
        """
        if not page_text or len(page_text.strip()) < 10:
            return []

        # 1. Sayfa Kanıtını Oluştur
        evidence = self.create_evidence(
            document_id=document_id,
            page_number=page_number,
            evidence_text=page_text
        )

        claims: List[V15CandidateClaimRecord] = []
        sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', page_text) if len(s.strip()) > 15]

        now_str = datetime.now().isoformat()

        for sentence in sentences:
            detected_type = "FACT"
            for pattern, c_type in self.CLAIM_PATTERNS:
                if re.search(pattern, sentence, re.IGNORECASE):
                    detected_type = c_type
                    break

            # Basit özne / yüklem ayrımı (veya tam ifade)
            claim_id = f"clm_{uuid.uuid4().hex[:12]}"
            candidate = V15CandidateClaimRecord(
                claim_id=claim_id,
                evidence_id=evidence.evidence_id,
                claim_type=detected_type,
                subject=sentence[:40].strip(),
                predicate="ASSERTED",
                object_val=sentence.strip(),
                raw_statement=sentence.strip(),
                topic_id=topic_id,
                confidence_score=0.70 if detected_type != "FACT" else 0.60,
                audit_status=V15AuditStatus.CANDIDATE,
                audit_reason="Doküman ayrıştırıcı tarafından otomatik aday iddia olarak üretildi.",
                created_at=now_str
            )
            claims.append(candidate)

        # 2. Aday İddiaları Veritabanına Yaz
        with db_session() as conn:
            cursor = conn.cursor()
            for c in claims:
                cursor.execute("""
                INSERT INTO v15_candidate_claims (
                    claim_id, evidence_id, claim_type, subject, predicate, object_val,
                    raw_statement, topic_id, confidence_score, audit_status,
                    audit_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    c.claim_id,
                    c.evidence_id,
                    c.claim_type,
                    c.subject,
                    c.predicate,
                    c.object_val,
                    c.raw_statement,
                    c.topic_id,
                    c.confidence_score,
                    c.audit_status.value,
                    c.audit_reason,
                    c.created_at
                ))

        return claims

    def get_candidate_claims(self, status: Optional[V15AuditStatus] = None) -> List[Dict[str, Any]]:
        """Aday iddiaları filtreleyerek döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM v15_candidate_claims WHERE audit_status = ?", (status.value,))
            else:
                cursor.execute("SELECT * FROM v15_candidate_claims")
            return [dict(r) for r in cursor.fetchall()]


document_analyst = DocumentAnalyst()
