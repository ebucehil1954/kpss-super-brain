"""
KPSS Super-Brain: Soru Zorluk Derecesi ve Çeldirici Güç Tahmincisi (Difficulty Estimator)
"""
from typing import Dict, Any

class DifficultyEstimator:
    @staticmethod
    def estimate_difficulty(stem: str, options: Dict[str, str], pattern_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sorunun ÖSYM zorluk derecesini (KOLAY, ORTA, ZOR, ÇOK_ZOR) ve tahmini ayırt ediciliğini hesaplar.
        """
        score = 0.5
        
        # Olumsuz kök veya öncüllü ise zorluk artar
        if pattern_info.get("is_negative"):
            score += 0.15
        if pattern_info.get("is_premise"):
            score += 0.20
        if pattern_info.get("is_chronology"):
            score += 0.15

        # Şık uzunlukları ve çeldirici yakınlığı
        opt_lengths = [len(v) for v in options.values()]
        if opt_lengths and max(opt_lengths) - min(opt_lengths) < 15:
            score += 0.10  # Şıklar homojense ayırt edicilik yüksek

        level = "ORTA"
        if score < 0.4:
            level = "KOLAY"
        elif score >= 0.75:
            level = "ZOR"
        elif score >= 0.90:
            level = "ÇOK_ZOR"

        return {
            "score": round(min(score, 1.0), 2),
            "level": level,
            "discrimination_index": round(0.4 + (score * 0.4), 2)
        }

difficulty_estimator = DifficultyEstimator()
