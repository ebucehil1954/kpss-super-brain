"""
KPSS Super-Brain: Üst-Biliş ve Stratejik Karar Motoru (Meta-Cognition v3)
"Ben neyi iyi biliyorum, hangi konuda zayıfım, sınavda en yüksek puanı getirecek
ve en hızlı kapatabileceğim eksik hangisi?"
Otonom ajanın kendi öğrenme rotasını belirleyen üst akıl katmanı.
"""
from typing import Dict, Any, List, Optional
from cognition.self_tester import self_tester
from cognition.prediction_engine import prediction_engine
from brain.knowledge_store import knowledge_store

class MetaCognitionEngine:
    @classmethod
    def analyze_learning_strategy(cls) -> Dict[str, Any]:
        """
        Bilişsel sağlık durumunu, tahmin radarını ve kaynak verimliliğini
        harmanlayarak en yüksek getirili (ROI) sonraki eylemi belirler.
        """
        health = self_tester.evaluate_knowledge_health()
        critical_gaps = health.get("critical_gaps", [])
        predictions = prediction_engine.HIGH_PROBABILITY_TOPIC_TARGETS

        strategy_actions = []

        for gap in critical_gaps:
            lesson = gap["lesson"]
            topic = gap["topic"]
            curr_recs = gap["current_records"]

            # Bu konunun sınavda çıkma olasılığını bul
            exam_prob = 0.7
            for p in predictions:
                if p.get("lesson") == lesson and (p.get("topic") in topic or topic in p.get("topic")):
                    exam_prob = p.get("probability", 0.9)
                    break

            # ROI (Return on Investment) Skoru = (1 - doygunluk) * Sınav Ağırlığı
            urgency_score = round((1.0 - (curr_recs / 10.0)) * exam_prob * 100, 1)

            strategy_actions.append({
                "lesson": lesson,
                "topic": topic,
                "urgency_score": urgency_score,
                "current_records": curr_recs,
                "recommended_action": "YOUTUBE_DEEP_SEARCH" if curr_recs == 0 else "WEB_RESEARCH_CONSOLIDATE"
            })

        # Önceliğe göre sırala
        strategy_actions.sort(key=lambda x: x["urgency_score"], reverse=True)

        # Bilinç Motoru Deliberasyonu (CoT)
        from autonomous.consciousness import consciousness
        deliberation = consciousness.deliberate_next_step()

        best_target = {
            "lesson": deliberation.get("target_lesson"),
            "topic": deliberation.get("target_topic"),
            "urgency_score": 95.0,
            "recommended_action": deliberation.get("action_type"),
            "teacher": deliberation.get("recommended_teacher"),
            "chain_of_thought": deliberation.get("chain_of_thought")
        }

        return {
            "maturity_score": health.get("maturity_score", 0),
            "status": health.get("status", "BİLİNÇLİ DERİN ÖĞRENME"),
            "top_priority_target": best_target,
            "all_gap_strategies": strategy_actions[:5],
            "consciousness_deliberation": deliberation
        }

metacognition = MetaCognitionEngine()
