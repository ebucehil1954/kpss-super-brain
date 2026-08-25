"""
KPSS Super-Brain: Öğrenme Hızı ve Bilişsel İvme Takipçisi (Learning Rate Tracker v3)
Ajanın saatlik ve günlük bilgi tüketim hızını, hangi hocadan ne kadar verim aldığını
ve ders bazlı ivmesini hesaplar.
"""
import time
from typing import Dict, Any, List
from datetime import datetime
from brain.knowledge_store import knowledge_store

class LearningRateTracker:
    def __init__(self):
        self._start_time = time.time()
        self._history = []

    def get_velocity_metrics(self) -> Dict[str, Any]:
        """Anlık bilgi tüketim hızını hesaplar."""
        stats = knowledge_store.get_stats()
        total = stats.get("total_records", 0)
        elapsed_seconds = max(1.0, time.time() - self._start_time)
        hours = elapsed_seconds / 3600.0

        records_per_hour = round(total / hours, 1) if hours > 0 else total

        return {
            "total_knowledge_records": total,
            "elapsed_seconds": int(elapsed_seconds),
            "records_per_hour": records_per_hour,
            "consumption_status": "AÇGÖZLÜ HIZLI TÜKETİM (SUPER-CHARGED)" if records_per_hour > 10 else "DENGELİ"
        }

learning_rate_tracker = LearningRateTracker()
