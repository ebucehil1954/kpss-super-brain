"""
KPSS Super-Brain: Kişiselleştirilmiş 30 Günlük Adaptif Çalışma Planı Üreticisi (Study Plan Generator)
"""
from typing import Dict, Any, List
from cognition.prediction_engine import prediction_engine

class StudyPlanGenerator:
    @classmethod
    async def generate_30_day_master_plan(cls) -> Dict[str, Any]:
        predictions = await prediction_engine.generate_live_predictions()
        
        weeks = []
        for i in range(4):
            week_num = i + 1
            focus_topics = predictions[i*2:(i+1)*2] if len(predictions) >= (i+1)*2 else predictions
            
            weeks.append({
                "week": week_num,
                "title": f"{week_num}. Hafta: Yüksek Frekanslı ÖSYM Konuları Kampı",
                "focus_topics": [f"{t.get('lesson')} - {t.get('topic')}" for t in focus_topics],
                "daily_goal": "Günde 80 soru çözümü + 20 adet flashcard tekrarı",
                "milestone": f"{week_num}. Hafta sonu branş denemesi (%85 hedef net)"
            })

        return {
            "title": "2026 KPSS Süper Zeka 30 Günlük Hızlandırılmış Çalışma Planı",
            "duration_days": 30,
            "weeks": weeks
        }

study_plan_generator = StudyPlanGenerator()
