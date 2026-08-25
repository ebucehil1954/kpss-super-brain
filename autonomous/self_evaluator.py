"""
KPSS Super-Brain: Öz-Değerlendirme ve Zayıflık Kapatma Motoru (Self Evaluator)
Yapay zeka kendi ürettiği ve çıkmış soruları çözer, kendi başarısını ölçer ve zayıf konularını tespit edip öğrenme kuyruğuna ekler.
"""
from typing import Dict, Any, List
from cognition.prediction_engine import prediction_engine
from anti_hallucination.adversarial_solver import adversarial_solver
from brain.episodic_memory import episodic_memory

class SelfEvaluator:
    @classmethod
    async def evaluate_knowledge_accuracy(cls, sample_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Soru havuzu üzerinde bağımsız hakem çözümü yaparak sistemin genel doğruluk oranını ölçer.
        """
        total = len(sample_questions)
        if total == 0:
            return {"accuracy_rate": 1.0, "tested_count": 0, "weak_spots": []}

        correct_count = 0
        weak_spots = []

        for q in sample_questions:
            is_valid, msg = await adversarial_solver.audit_generated_question(q)
            if is_valid:
                correct_count += 1
            else:
                weak_spots.append({
                    "lesson": q.get("lesson"),
                    "topic": q.get("topic"),
                    "reason": msg
                })

        accuracy = round(correct_count / total, 2)

        episodic_memory.record_learning_event(
            event_type="SELF_EVALUATION",
            topic="Genel Doğruluk ve Zayıflık Taraması",
            lesson="TÜMÜ",
            summary=f"Sistem {total} adet soru üzerinde öz-değerlendirme yaptı. Doğruluk: %{int(accuracy*100)}, Zayıf Noktalar: {len(weak_spots)}",
            details={"accuracy": accuracy, "weak_spots": weak_spots},
            confidence_gain=0.03
        )

        return {
            "accuracy_rate": accuracy,
            "tested_count": total,
            "correct_count": correct_count,
            "weak_spots": weak_spots
        }

self_evaluator = SelfEvaluator()
