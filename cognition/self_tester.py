"""
KPSS Super-Brain: Otonom Zeka Müfredat Sağlığı ve Konu Hakimiyet Analizi (Curriculum Health Engine)
"Yapay olgunluk puanları yerine gerçek müfredat derinliğini (her konu için en az 3-4 video) ölçer."
"""
from typing import Dict, Any, List
from brain.knowledge_store import knowledge_store
from brain.database import db_session

class SelfTester:
    @classmethod
    def evaluate_knowledge_health(cls) -> Dict[str, Any]:
        """
        Resmi ÖSYM müfredatına göre gerçek konu hakimiyet durumunu hesaplar.
        """
        from brain.curriculum_matrix import curriculum_matrix
        matrix_report = curriculum_matrix.get_curriculum_mastery_report()
        stats = knowledge_store.get_stats()
        
        total_topics = matrix_report["total_official_topics"]
        fully_mastered = matrix_report["fully_mastered_count"]
        synthesizing = matrix_report["synthesizing_count"]
        in_progress = matrix_report["in_progress_count"]
        unstarted = matrix_report["unstarted_count"]

        # Gerçek Müfredat Kapsam Skoru (0-100%)
        coverage_score = matrix_report["mastery_percentage"]

        if coverage_score >= 90:
            status_text = "KPSS BAŞUZMANI (TÜM MÜFREDAT TAM HAKİMİYET)"
        elif coverage_score >= 60:
            status_text = "İLERİ DÜZEY ÖĞRETMEN SEVİYESİ"
        elif coverage_score >= 30:
            status_text = "ÇOKLU HOCA SENTEZ AŞAMASINDA"
        elif in_progress > 0 or synthesizing > 0:
            status_text = "AKTİF VİDEO SİNDİRİMİ DEVAM EDİYOR"
        else:
            status_text = "MÜFREDAT KEŞİF VE BAŞLANGIÇ AŞAMASINDA"

        # Kritik Eksikler (0 veya 1 video izlenmiş konular)
        critical_gaps = []
        for t in matrix_report["topics"]:
            if t["consumed_videos_count"] < t["target_videos_count"]:
                critical_gaps.append({
                    "lesson": t["lesson"],
                    "topic": t["topic_name"],
                    "consumed_videos": t["consumed_videos_count"],
                    "target_videos": t["target_videos_count"],
                    "teachers_count": len(t["distinct_teachers"]),
                    "status": "KRİTİK_EKSİK (0 Video)" if t["consumed_videos_count"] == 0 else f"GELİŞTİRİLMELİ ({t['consumed_videos_count']}/{t['target_videos_count']} Video)"
                })

        return {
            "maturity_score": int(coverage_score), # Geriye dönük API uyumluluğu için gerçek kapsam yüzdesi
            "curriculum_coverage_pct": coverage_score,
            "total_official_topics": total_topics,
            "fully_mastered_count": fully_mastered,
            "synthesizing_count": synthesizing,
            "in_progress_count": in_progress,
            "unstarted_count": unstarted,
            "total_records": stats.get("total_records", 0),
            "gaps_count": len(critical_gaps),
            "critical_gaps": critical_gaps,
            "by_lesson": matrix_report["by_lesson"],
            "status": status_text
        }

    @classmethod
    async def auto_repair_gaps(cls) -> int:
        """Kritik eksik tespit edilen konular için Manus YouTube Keşif Ajanını tetikler."""
        from senses.youtube_crawler_agent import youtube_crawler_agent
        res = await youtube_crawler_agent.run_manus_style_deep_discovery(force_all_topics=False)
        return res.get("videos_queued", 0)

self_tester = SelfTester()
