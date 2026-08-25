"""
KPSS Super-Brain: Orkestratör Köprüsü (Master Orchestrator Bridge)
Yeni 7 katmanlı otonom mimari ile eski arayüzler arasındaki uyumluluk köprüsüdür.
"""
from autonomous.learning_loop import learning_loop, ContinuousLearningLoop

SuperBrainOrchestrator = ContinuousLearningLoop

__all__ = ["SuperBrainOrchestrator"]
