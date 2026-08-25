"""
KPSS Super-Brain: Gerçek Eksik ve Boşluk Analiz Motoru (Real Gap Analyzer v6)
Hedef kavram doluluğu, alt başlıklar, tek kaynaklı iddialar, zayıf kanıtlar,
çözümlenmemiş çelişkiler ve öğretmen çeşitliliğini deterministik olarak ölçer.
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Set
from brain.models import VerificationStatus
from cognition.contradiction_engine import contradiction_engine
from cognition.teacher_identity import teacher_identity

class GapAnalyzer:
    """
    KPSS bilgi madenciliği sürecindeki gerçek eksikleri (material gaps)
    7 bağımsız boyutta deterministik olarak analiz eden motor.
    """

    @classmethod
    def analyze_gaps(
        cls,
        lesson: str,
        topic: str,
        target_concepts: List[str],
        claims: List[Dict[str, Any]],
        teachers: Optional[List[str]] = None,
        subtopics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Kapsamlı ve deterministik gap analizi gerçekleştirir.
        """
        missing_concepts: List[str] = []
        weak_claims: List[str] = []
        single_source_claims: List[str] = []
        unverified_claims: List[str] = []
        recommended_queries: List[str] = []

        # 1. Target Concept & Subtopic Coverage
        verified_texts = [
            str(c.get("text", "")).lower()
            for c in claims
            if c.get("verification_status") in [VerificationStatus.VERIFIED, "VERIFIED"]
        ]
        all_texts = [str(c.get("text", "")).lower() for c in claims]

        for concept in target_concepts:
            concept_terms = [t for t in re.split(r"\s+", concept.lower()) if len(t) > 2]
            # Kavramın doğrulanmış iddialarda en az 1 anahtar kelime ile temsil edilip edilmediği
            is_covered = any(
                all(term in v_txt for term in concept_terms[:2])
                for v_txt in verified_texts
            ) if concept_terms else False

            if not is_covered:
                missing_concepts.append(concept)
                recommended_queries.append(f"{topic} {concept}")

        # 2. Missing Subtopics (varsa)
        if subtopics:
            for sub in subtopics:
                sub_clean = sub.lower()
                if not any(sub_clean in txt for txt in verified_texts):
                    if sub not in missing_concepts:
                        missing_concepts.append(sub)
                        recommended_queries.append(f"{topic} {sub}")

        # 3. Unverified & Weak Evidence Claims
        for c in claims:
            cid = c.get("claim_id", "unknown")
            text = c.get("text", "")
            status = c.get("verification_status")
            refs = c.get("evidence_refs", [])

            if status not in [VerificationStatus.VERIFIED, "VERIFIED"]:
                unverified_claims.append(f"[{cid}] {text[:80]} (Durum: {status})")

            # Zayıf kanıt kontrolü: snippet kısa veya yok
            is_weak = False
            if not refs:
                is_weak = True
            else:
                for r in refs:
                    snip = r.get("snippet", "") if isinstance(r, dict) else getattr(r, "snippet", "")
                    if len(str(snip).strip()) < 15:
                        is_weak = True
            if is_weak:
                weak_claims.append(f"[{cid}] {text[:80]}")

        # 4. Single-Source Claims (Yalnızca 1 gayriresmî hocaya dayanan kritik iddialar)
        for c in claims:
            cid = c.get("claim_id", "unknown")
            src = c.get("source", "")
            is_official = any(kw in src.lower() for kw in ["mevzuat", "resmi", "anayasa", "kanun"])
            if not is_official:
                # İddianın metnine benzer başka iddia var mı
                c_text = str(c.get("text", "")).lower()
                supporting_teachers = set()
                for other in claims:
                    o_text = str(other.get("text", "")).lower()
                    if c_text[:30] in o_text or o_text[:30] in c_text:
                        t_name = other.get("speaker_or_author") or other.get("source")
                        if t_name:
                            supporting_teachers.add(teacher_identity.normalize(t_name))
                if len(supporting_teachers) <= 1:
                    single_source_claims.append(f"[{cid}] {c.get('text', '')[:80]} (Tek Eğitmen: {list(supporting_teachers) or src})")

        # 5. Unresolved Contradictions (Gerçek DB kayıtları)
        unresolved_recs = contradiction_engine.get_unresolved_contradictions(lesson)
        unresolved_descriptions: List[str] = []
        for ur in unresolved_recs:
            u_topic = ur.get("topic", "")
            if u_topic == topic or u_topic == "GENEL" or not topic:
                desc = f"Çelişki [{ur.get('contradiction_id')}]: {ur.get('claim_a_text', '')[:50]} VS {ur.get('claim_b_text', '')[:50]}"
                unresolved_descriptions.append(desc)
                recommended_queries.append(f"{topic} Resmî Mevzuat {ur.get('claim_a_text', '')[:30]}")

        # 6. Missing Teacher Diversity
        distinct_teachers: Set[str] = set()
        if teachers:
            for t in teachers:
                distinct_teachers.add(teacher_identity.normalize(t))
        for c in claims:
            spk = c.get("speaker_or_author") or c.get("source")
            if spk and not any(kw in str(spk).lower() for kw in ["mevzuat", "resmi"]):
                distinct_teachers.add(teacher_identity.normalize(spk))

        missing_teacher_diversity = len(distinct_teachers) < 2

        # 7. Deterministik Karar (MATERIAL_GAPS vs NO_MATERIAL_GAPS)
        has_material_gaps = (
            len(missing_concepts) > 0
            or len(unresolved_descriptions) > 0
            or len(unverified_claims) > 0
            or len(single_source_claims) > 0
            or missing_teacher_diversity
        )

        gap_status = "MATERIAL_GAPS" if has_material_gaps else "NO_MATERIAL_GAPS"

        # Tekilleştirilmiş önerilen arama sorguları
        unique_queries = list(dict.fromkeys(recommended_queries))

        return {
            "gap_status": gap_status,
            "has_material_gaps": has_material_gaps,
            "missing_concepts": missing_concepts,
            "weak_claims": weak_claims,
            "single_source_claims": single_source_claims,
            "unverified_claims": unverified_claims,
            "unresolved_contradictions": unresolved_descriptions,
            "distinct_teachers_count": len(distinct_teachers),
            "missing_teacher_diversity": missing_teacher_diversity,
            "recommended_queries": unique_queries
        }

gap_analyzer = GapAnalyzer()
