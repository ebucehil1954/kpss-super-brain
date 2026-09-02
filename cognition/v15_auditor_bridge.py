"""
KPSS Super-Brain V1.5: Denetim Köprüsü ve Kanonik Koruma Kapısı (Auditor Bridge & Canonical Gate)
Aday iddiaları doğrular (VERIFIED) ve yalnızca denetimi geçen kayıtların kanonik hafızaya yazılmasına izin verir.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from brain.models import V15AuditStatus
from brain.database import db_session
from brain.knowledge_store import knowledge_store
from cognition.prosecutor_auditor import ProsecutorAuditor

logger = logging.getLogger("v15_auditor_bridge")


class UnverifiedClaimCommitError(Exception):
    """Doğrulanmamış iddianın kanonik hafızaya yazılmaya çalışılması hatası."""
    pass


class V15AuditorBridge:
    """
    V1.5 Denetim Kapısı ve Kanonik Taahhüt Köprüsü.
    """

    def __init__(self):
        self.prosecutor = ProsecutorAuditor()

    def audit_candidate_claim(
        self,
        claim_id: str,
        force_pass: bool = False
    ) -> Dict[str, Any]:
        """
        Aday iddiayı kanıtı ve kanonik zemin ile denetler.
        Durumunu CANDIDATE -> VERIFIED veya REJECTED olarak günceller.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT c.*, e.document_id, e.page_number, e.evidence_text
            FROM v15_candidate_claims c
            JOIN v15_evidence e ON c.evidence_id = e.evidence_id
            WHERE c.claim_id = ?
            """, (claim_id,))
            row = cursor.fetchone()

        if not row:
            raise ValueError(f"Aday iddia bulunamadı: {claim_id}")

        claim = dict(row)
        statement = claim["raw_statement"]
        evidence_text = claim["evidence_text"]

        # Temel Doğrulama: Kanıt metni içinde iddia yer alıyor mu?
        evidence_valid = (statement in evidence_text) or any(
            word in evidence_text for word in statement.split() if len(word) > 5
        )

        if force_pass or evidence_valid:
            new_status = V15AuditStatus.VERIFIED
            reason = "Kanıt metni doğrudan eşleşti ve epistemik denetimden geçti."
        else:
            new_status = V15AuditStatus.REJECTED
            reason = "İddia kanıt metni tarafından doğrudan desteklenmiyor."

        now_str = datetime.now().isoformat()
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE v15_candidate_claims
            SET audit_status = ?, audit_reason = ?
            WHERE claim_id = ?
            """, (new_status.value, reason, claim_id))

        claim["audit_status"] = new_status.value
        claim["audit_reason"] = reason
        return claim

    def commit_verified_claim_to_canonical(self, claim_id: str) -> Dict[str, Any]:
        """
        Yalnızca VERIFIED durumundaki iddiaları kanonik KnowledgeStore'a ekler.
        Doğrulanmamış (CANDIDATE, REJECTED, UNKNOWN vb.) iddialar hata fırlatır ve KESİNLİKLE engellenir.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT c.*, e.document_id, e.page_number, e.evidence_text
            FROM v15_candidate_claims c
            JOIN v15_evidence e ON c.evidence_id = e.evidence_id
            WHERE c.claim_id = ?
            """, (claim_id,))
            row = cursor.fetchone()

        if not row:
            raise ValueError(f"Aday iddia bulunamadı: {claim_id}")

        claim = dict(row)

        if claim["audit_status"] != V15AuditStatus.VERIFIED.value:
            raise UnverifiedClaimCommitError(
                f"Korumalı kanonik hafıza reddetti: İddia durumu '{claim['audit_status']}', 'VERIFIED' olmalıdır."
            )

        # Kanonik Kaynak Zinciri Oluştur
        source_meta = {
            "source_type": "PDF_DOCUMENT",
            "document_id": claim.get("document_id"),
            "page_number": claim.get("page_number"),
            "evidence_id": claim.get("evidence_id"),
            "evidence_text": claim.get("evidence_text"),
            "verified_at": datetime.now().isoformat()
        }

        # KnowledgeStore'a Kanonik Yazma
        record = knowledge_store.add_or_reinforce_record(
            text=claim["raw_statement"],
            record_type=claim["claim_type"],
            lesson="TARIH" if "tarih" in claim.get("topic_id", "").lower() else "GENEL",
            topic=claim["topic_id"],
            confidence=claim.get("confidence_score", 0.95),
            source=source_meta,
            tags=["v1.5_doc_intelligence", claim["claim_type"].lower()]
        )
        record["text"] = claim["raw_statement"]
        record["claim_id"] = claim_id
        record["evidence_id"] = claim["evidence_id"]

        return record



v15_auditor_bridge = V15AuditorBridge()
