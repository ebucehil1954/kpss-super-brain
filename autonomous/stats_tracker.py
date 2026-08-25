"""
KPSS Super-Brain: Canlı Öğrenme ve Bellek İstatistik Takipçisi (Stats Tracker)
7/24 otonom döngü süresince izlenen video hızını, ambar büyümesini ve bilişsel olgunluk metriklerini izler.
"""
from typing import Dict, Any
from datetime import datetime
from brain.knowledge_store import knowledge_store
from brain.reasoning_store import reasoning_store
from brain.database import db_session
from cognition.self_tester import self_tester

class StatsTracker:
    _start_time = datetime.now()

    @classmethod
    def get_live_metrics(cls) -> Dict[str, Any]:
        """Tüm sistemin canlı çalışma ve bilişsel öğrenme istatistiklerini hesaplar."""
        now = datetime.now()
        uptime_seconds = int((now - cls._start_time).total_seconds())
        
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        uptime_formatted = f"{hours} sa {minutes} dk {seconds} sn"

        # Veritabanı metrikleri
        k_stats = knowledge_store.get_stats()
        health = self_tester.evaluate_knowledge_health()

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM video_queue WHERE status = 'WATCHED'")
            watched_count = cursor.fetchone()["c"]
            
            cursor.execute("SELECT COUNT(*) as c FROM video_queue WHERE status = 'PENDING'")
            pending_count = cursor.fetchone()["c"]
            
            cursor.execute("SELECT COUNT(*) as c FROM teacher_profiles")
            teachers_count = cursor.fetchone()["c"]
            
            cursor.execute("SELECT COUNT(*) as c FROM reasoning_chains")
            chains_count = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM learning_events")
            events_count = cursor.fetchone()["c"]

        return {
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": uptime_formatted,
            "started_at": cls._start_time.isoformat(),
            "total_knowledge_records": k_stats.get("total_records", 0),
            "records_by_lesson": k_stats.get("by_lesson", {}),
            "records_by_type": k_stats.get("by_type", {}),
            "total_videos_watched": watched_count,
            "total_videos_pending": pending_count,
            "total_teachers_modeled": teachers_count,
            "total_reasoning_chains": chains_count,
            "total_learning_episodes": events_count,
            "maturity_score": health.get("maturity_score", 0),
            "intellectual_status": health.get("status", "ÖĞRENİYOR"),
            "critical_gaps_count": health.get("gaps_count", 0)
        }

stats_tracker = StatsTracker()
