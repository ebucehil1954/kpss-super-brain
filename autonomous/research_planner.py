"""
KPSS Super-Brain: Hedefe Yönelik Araştırma Planlayıcısı (Targeted Research Planner v6)
GapReport çıktısını deterministik olarak tüketip dinamik ve önceliklendirilmiş
ResearchPlan (Arama sorguları, resmî mevzuat ve eğitmen çeşitlendirme eylemleri) üretir.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from brain.models import ContradictionSeverity

class TargetedResearchPlanner:
    """
    Eksik ve boşluk raporunu (GapReport) analiz ederek hedefe yönelik,
    önceliklendirilmiş araştırma planı (ResearchPlan) üreten planlayıcı.
    """

    @classmethod
    def create_research_plan(
        cls,
        lesson: str,
        topic: str,
        gap_report: Dict[str, Any],
        iteration: int = 1
    ) -> Dict[str, Any]:
        """
        GapReport verisinden deterministik ResearchPlan üretir.
        """
        has_gaps = gap_report.get("has_material_gaps", False)
        gap_status = gap_report.get("gap_status", "NO_MATERIAL_GAPS")
        
        missing_concepts = gap_report.get("missing_concepts", [])
        unresolved_contradictions = gap_report.get("unresolved_contradictions", [])
        weak_claims = gap_report.get("weak_claims", [])
        single_source = gap_report.get("single_source_claims", [])
        missing_diversity = gap_report.get("missing_teacher_diversity", False)

        # 1. Boşluk Yoksa Ek Araştırma Gerekmez
        if not has_gaps or gap_status == "NO_MATERIAL_GAPS":
            return {
                "priority": "NONE",
                "requires_additional_research": False,
                "queries": [],
                "target_actions": [],
                "strategy": "Tüm kavramlar doğrulanmış, kaynak çeşitliliği sağlanmış ve çözümlenmemiş çelişki bulunmamaktadır. Ek araştırma gerekmez."
            }

        queries: List[str] = []
        target_actions: List[Dict[str, Any]] = []
        priority = "MEDIUM"
        strategy_parts: List[str] = []

        # 2. Öncelik 1: Çözümlenmemiş Yüksek Öncelikli Çelişkiler (HIGH / CRITICAL)
        if unresolved_contradictions:
            priority = "HIGH"
            strategy_parts.append(f"{len(unresolved_contradictions)} adet çözümlenmemiş çelişki için resmî mevzuat ve anayasa taraması")
            for contra in unresolved_contradictions:
                q = f"{topic} Resmî Mevzuat Anayasa Kanun {contra[:40]}"
                queries.append(q)
                target_actions.append({
                    "action_type": "official_mevzuat_search",
                    "query": q,
                    "target_gap": "contradiction_resolution"
                })

        # 3. Öncelik 2: Kritik Eksik Kavramlar (HIGH)
        if missing_concepts:
            if priority != "HIGH":
                priority = "HIGH"
            strategy_parts.append(f"{len(missing_concepts)} eksik kavram için hedefli YouTube ve müfredat taraması")
            for mc in missing_concepts:
                q_yt = f"{topic} {mc} KPSS konu anlatımı"
                q_mev = f"{lesson} {topic} {mc}"
                queries.append(q_yt)
                target_actions.append({
                    "action_type": "youtube_search",
                    "query": q_yt,
                    "target_gap": f"concept_{mc}"
                })
                target_actions.append({
                    "action_type": "official_mevzuat_search",
                    "query": q_mev,
                    "target_gap": f"concept_{mc}"
                })

        # 4. Öncelik 3: Eğitmen Çeşitliliği Eksikliği (MEDIUM)
        if missing_diversity or single_source:
            if priority not in ["HIGH", "CRITICAL"]:
                priority = "MEDIUM"
            strategy_parts.append("Öğretmen çeşitliliğini artırmak için farklı kanal ve eğitmenlerin videolarını tarama")
            q_div = f"{topic} KPSS farklı hoca ders notları soru çözümü"
            queries.append(q_div)
            target_actions.append({
                "action_type": "youtube_search",
                "query": q_div,
                "target_gap": "teacher_diversity"
            })

        # 5. Öncelik 4: Zayıf Kanıtlar (MEDIUM/LOW)
        if weak_claims and not missing_concepts and not unresolved_contradictions:
            if priority not in ["HIGH", "CRITICAL"]:
                priority = "LOW"
            strategy_parts.append(f"{len(weak_claims)} zayıf kanıtlı iddiayı derinleştirmek için detaylı transkript analizi")
            for wc in weak_claims[:3]:
                q_wc = f"{topic} {wc[:35]} detay"
                queries.append(q_wc)

        # Sorguları tekilleştir
        unique_queries = list(dict.fromkeys(queries))

        return {
            "priority": priority,
            "requires_additional_research": True,
            "queries": unique_queries,
            "target_actions": target_actions,
            "strategy": f"İterasyon {iteration} Araştırma Planı: " + "; ".join(strategy_parts)
        }

research_planner = TargetedResearchPlanner()
