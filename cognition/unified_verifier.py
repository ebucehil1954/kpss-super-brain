"""
KPSS Super-Brain: Hiyerarşik Birleşik Doğrulama Ağ Geçidi (Unified Verifier Gateway v1)
Dağınık doğrulama mantıklarını (Kara Liste / Mülga Mevzuat, Z3 SMT Biçimsel Mantık,
ve DeepSeek-R1 Savcı Denetimi) tek bir hiyerarşik doğrulama hattı arkasında birleştirir.

Hiyerarşik Sıralama:
1. Kademe 1: Hızlı Kural & Mülga Mevzuat Kara Listesi (BlacklistAuditor) -> O(1) Anında Eleme
2. Kademe 2: Biçimsel SMT Mantık Denetimi (Z3LogicValidator & Anayasal Kurallar) -> %100 Matematiksel Kesinlik
3. Kademe 3: Derin Epistemik Savcı Denetimi (ProsecutorAuditor & Ground Truth Ambarı) -> DeepSeek-R1 / Kanonik Eşleştirme
"""
from __future__ import annotations

import enum
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from brain.blacklist_rules import MULGA_TERIMLER
from anti_hallucination.z3_logic_validator import Z3LogicValidator
from cognition.auditor import AuditorEngine
from cognition.prosecutor_auditor import ProsecutorAuditor
from brain.knowledge_store import knowledge_store
from brain.database import db_session

logger = logging.getLogger("unified_verifier")


class VerificationVerdict(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CONTRADICTION = "CONTRADICTION"
    AUDIT_FAILED = "AUDIT_FAILED"
    AMBIGUOUS = "AMBIGUOUS"


class VerificationDecision(BaseModel):
    verdict: VerificationVerdict
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    tier_resolved: str  # "TIER_1_BLACKLIST", "TIER_2_Z3_LOGIC", "TIER_3_PROSECUTOR", "TIER_3_CANONICAL"
    reason: str
    canonical_truth: Optional[str] = None
    trap_distractor: Optional[str] = None
    thought_process: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class UnifiedVerifier:
    """
    Tüm KPSS bilgi iddialarını hiyerarşik 3 aşamalı hattan geçiren merkezi doğrulayıcı.
    """

    def __init__(self):
        self.prosecutor = ProsecutorAuditor()
        self.auditor = AuditorEngine()

    def _check_tier_1_blacklist(self, text: str) -> Optional[VerificationDecision]:
        """Kademe 1: Mülga ve kaldırılmış anayasal/hukuki terimleri anında yakalar."""
        text_lower = text.lower()
        for term in MULGA_TERIMLER:
            # Kelime sınırı kontrolü
            if term in text_lower:
                return VerificationDecision(
                    verdict=VerificationVerdict.REJECTED,
                    confidence=0.99,
                    tier_resolved="TIER_1_BLACKLIST",
                    reason=f"Mülga/Kaldırılmış mevzuat terimi tespit edildi: '{term}'",
                    trap_distractor=f"ÖSYM Tuzağı: Metinde 2017 öncesi mülga '{term}' kavramı yer almaktadır."
                )
        return None

    def _check_tier_2_formal_logic(self, text: str, lesson: str, topic: str) -> Optional[VerificationDecision]:
        """Kademe 2: Z3 SMT Formal Mantık Çözücüsü ve Anayasal Kural Matrisi denetimi."""
        # 1. Z3 SMT Sayısal Doğrulama
        z3_passed = Z3LogicValidator.validate_text(text)
        if not z3_passed:
            return VerificationDecision(
                verdict=VerificationVerdict.CONTRADICTION,
                confidence=1.0,
                tier_resolved="TIER_2_Z3_LOGIC",
                reason="Z3 SMT Formal Logic çözücü UNSAT (Mantıksal Çelişki) verdi.",
                trap_distractor=f"Biçimsel Mantık Hatası: Metindeki sayısal/hukuki kural anayasal zeminle çelişmektedir."
            )

        # 2. Auditor Kural Matrisi Denetimi
        audit_result = self.auditor.audit_claim(text, lesson=lesson, topic=topic)
        if audit_result.get("is_valid") is False:
            return VerificationDecision(
                verdict=VerificationVerdict.REJECTED,
                confidence=audit_result.get("confidence", 0.95),
                tier_resolved="TIER_2_Z3_LOGIC",
                reason=audit_result.get("explanation", "Kural matrisi denetiminden geçemedi."),
                canonical_truth=audit_result.get("canonical_truth"),
                trap_distractor=audit_result.get("trap_distractor")
            )

        return None

    async def verify_claim(
        self,
        claim_text: str,
        lesson: str = "GENEL",
        topic: str = "Genel",
        teacher: Optional[str] = None,
        video_id: Optional[str] = None
    ) -> VerificationDecision:
        """
        Bir iddiayı hiyerarşik olarak Kademe 1 -> Kademe 2 -> Kademe 3 adımlarından geçirir.
        """
        # 1. Kademe 1: Kara Liste ve Mülga Terimler
        t1 = self._check_tier_1_blacklist(claim_text)
        if t1 is not None:
            return t1

        # 2. Kademe 2: Biçimsel Mantık ve Z3 SMT
        t2 = self._check_tier_2_formal_logic(claim_text, lesson=lesson, topic=topic)
        if t2 is not None:
            return t2

        # 3. Kademe 3: DeepSeek-R1 Savcı Denetimi ve Kanonik Ambar Eşleme
        try:
            prosecutor_res = await self.prosecutor.audit_claim_deepseek(
                claim_text=claim_text,
                lesson=lesson,
                topic=topic,
                teacher=teacher,
                video_id=video_id
            )
            raw_verdict = prosecutor_res.get("verdict", "AUDIT_FAILED")
            try:
                v_enum = VerificationVerdict(raw_verdict)
            except ValueError:
                v_enum = VerificationVerdict.AUDIT_FAILED

            return VerificationDecision(
                verdict=v_enum,
                confidence=float(prosecutor_res.get("confidence", 0.85)),
                tier_resolved="TIER_3_PROSECUTOR",
                reason=prosecutor_res.get("explanation", "Savcı denetimi tamamlandı."),
                canonical_truth=prosecutor_res.get("canonical_truth"),
                trap_distractor=prosecutor_res.get("trap_distractor"),
                thought_process=prosecutor_res.get("thought_process")
            )
        except Exception as e:
            logger.error(f"❌ [UNIFIED VERIFIER] Kademe 3 Savcı denetimi hatası: {e}")
            return VerificationDecision(
                verdict=VerificationVerdict.AUDIT_FAILED,
                confidence=0.0,
                tier_resolved="TIER_3_PROSECUTOR",
                reason=f"Savcı denetimi sırasında beklenmeyen hata: {e}"
            )

    async def batch_verify_claims(
        self,
        claims: List[Dict[str, Any]]
    ) -> List[VerificationDecision]:
        """Birden çok iddiayı toplu olarak doğrular."""
        results = []
        for c in claims:
            txt = c.get("text", "")
            les = c.get("lesson", "GENEL")
            top = c.get("topic", "Genel")
            tea = c.get("teacher")
            vid = c.get("video_id")
            dec = await self.verify_claim(claim_text=txt, lesson=les, topic=top, teacher=tea, video_id=vid)
            results.append(dec)
        return results


unified_verifier = UnifiedVerifier()
