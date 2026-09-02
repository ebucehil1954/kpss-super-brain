"""
KPSS Super-Brain: Uçtan Uca Kanıt Zinciri Doğrulayıcı (End-to-End Provenance Validator)
Master Refactor Plan Phase 11 Kapsamı:
Source -> Video/Document -> Raw Segment (timestamp/offset) -> EvidenceRef -> AtomicClaim -> VerificationRecord -> KnowledgeRecord
Zincirdeki herhangi bir halka kopuksa veya eksikse altın bilgiye terfi KESİNLİKLE REDDEDİLİR.
"""
from typing import Tuple, List, Optional, Any
import json
from brain.models import AtomicClaim, EvidenceRef, SourceType


class ProvenanceValidator:
    @staticmethod
    def validate_provenance_chain(claim: Any) -> Tuple[bool, str]:
        """
        Bir atomik iddianın kanıt zincirinin kök kaynağa kadar eksiksiz olup olmadığını doğrular.
        Kopuk halka varsa (False, hata_sebebi) döner.
        """
        if not claim:
            return False, "PROVENANCE_BROKEN: İddia nesnesi boş."

        if isinstance(claim, dict):
            evidence_list = claim.get("evidence_refs") or claim.get("evidence") or claim.get("evidence_refs_json") or []
        else:
            evidence_list = getattr(claim, "evidence_refs", None) or getattr(claim, "evidence", [])

        if isinstance(evidence_list, str):
            try:
                evidence_list = json.loads(evidence_list)
            except Exception:
                evidence_list = []

        if not evidence_list or len(evidence_list) == 0:
            return False, "PROVENANCE_BROKEN: İddiaya bağlı kanıt referansı (EvidenceRef) bulunamadı."

        for idx, ev in enumerate(evidence_list):
            if isinstance(ev, dict):
                source_id = ev.get("source_id")
                source_type = ev.get("source_type")
                snippet = ev.get("snippet", "") or ""
                video_id = ev.get("video_id")
                segment_id = ev.get("segment_id")
                timestamp_str = ev.get("timestamp_str")
            else:
                source_id = getattr(ev, "source_id", None)
                source_type = getattr(ev, "source_type", None)
                snippet = getattr(ev, "snippet", "") or ""
                video_id = getattr(ev, "video_id", None)
                segment_id = getattr(ev, "segment_id", None)
                timestamp_str = getattr(ev, "timestamp_str", None)

            # 1. Kaynak Kimliği Kontrolü
            if not source_id or not str(source_id).strip():
                return False, f"PROVENANCE_BROKEN: {idx}. kanıt referansında kök source_id eksik."

            # 2. Kaynak Türü Kontrolü
            if not source_type:
                return False, f"PROVENANCE_BROKEN: {idx}. kanıt referansında source_type eksik."

            st_val = source_type.value if hasattr(source_type, "value") else str(source_type)

            # 3. Kanıt Metin Parçacığı Kontrolü
            if len(str(snippet).strip()) < 10:
                return False, f"PROVENANCE_BROKEN: {idx}. kanıt parçacığı (snippet) boş veya yetersiz uzunlukta."

            # 4. Video veya Segment Ayrıntısı
            if st_val in ("YOUTUBE_TRANSCRIPT", "YOUTUBE_AUDIO_WHISPER"):
                has_video_id = bool(video_id or (source_id and len(str(source_id)) >= 8))
                if not has_video_id:
                    return False, f"PROVENANCE_BROKEN: Video kaynağı için video_id eksik."
                
                has_segment = bool(segment_id or timestamp_str)
                if not has_segment:
                    return False, f"PROVENANCE_BROKEN: Video transkripti için zaman damgası veya segment_id eksik."

        return True, "PROVENANCE_OK"


provenance_validator = ProvenanceValidator()
