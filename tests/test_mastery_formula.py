"""
Forensic Audit P1-3 Regresyon Testleri:
Mastery formülünün DynamicWeightOptimizer ile entegrasyonunu doğrular:
- DynamicWeightOptimizer ağırlıkları kullanılmalı
- 5 fact ile MASTERED olunamamalı (minimum mastery_score >= 0.85 gerekli)
"""
import pytest
import inspect
from brain.mastery import dynamic_weight_optimizer


class TestMasteryFormula:
    """Mastery hesaplama mantığı testleri (P1-3)."""

    def test_dynamic_weight_optimizer_is_called_in_queue(self):
        """queue.py'deki mastery hesaplaması DynamicWeightOptimizer'ı kullanmalı."""
        from curriculum.queue import CurriculumQueue
        source_code = inspect.getsource(CurriculumQueue.mark_video_watched)

        assert "dynamic_weight_optimizer" in source_code, \
            "mark_video_watched() DynamicWeightOptimizer'ı kullanmıyor!"
        assert "mastery_score" in source_code, \
            "mark_video_watched() mastery_score hesaplamıyor!"

    def test_dynamic_weight_optimizer_returns_valid_weights(self):
        """DynamicWeightOptimizer geçerli ağırlıklar döndürmeli."""
        weights = dynamic_weight_optimizer.get_optimal_weights()

        required_keys = [
            "source_coverage", "evidence_density", "verification_score",
            "cross_teacher_agreement", "concept_coverage", "freshness"
        ]
        for key in required_keys:
            assert key in weights, f"Ağırlık '{key}' eksik!"
            assert 0.0 <= weights[key] <= 1.0, f"Ağırlık '{key}' geçersiz aralıkta: {weights[key]}"

        # Ağırlıklar toplamı yaklaşık 1.0 olmalı
        total = sum(weights.values())
        assert 0.95 <= total <= 1.05, f"Ağırlık toplamı ~1.0 olmalı, ama {total}"

    def test_low_facts_cannot_be_mastered(self):
        """Sadece 5 fact ile mastery_score >= 0.85 OLAMAMALI."""
        weights = dynamic_weight_optimizer.get_optimal_weights()

        # Simüle: 4 video, 2 hoca, sadece 5 fact, 0 çelişki
        count = 4
        target = 4
        total_facts = 5
        teachers_count = 2
        unresolved_cnt = 0

        source_coverage = min(1.0, count / max(target, 1))      # 1.0
        evidence_density = min(1.0, total_facts / 20.0)          # 0.25
        verification_score = 1.0 if unresolved_cnt == 0 else 0.0  # 1.0
        cross_teacher = min(1.0, teachers_count / 3.0)           # 0.67
        concept_cov = min(1.0, total_facts / 15.0)               # 0.33
        freshness = 1.0

        mastery_score = (
            weights["source_coverage"] * source_coverage +
            weights["evidence_density"] * evidence_density +
            weights["verification_score"] * verification_score +
            weights["cross_teacher_agreement"] * cross_teacher +
            weights["concept_coverage"] * concept_cov +
            weights["freshness"] * freshness
        )

        # 5 fact ile mastery_score 0.85'i geçmemeli (eski formülde geçiyordu)
        assert mastery_score < 0.85, \
            f"Sadece 5 fact ile mastery_score {mastery_score:.3f} >= 0.85 olmamalı!"

    def test_high_quality_topic_can_be_mastered(self):
        """Yeterli derinlikte bir konu MASTERED olabilmeli."""
        weights = dynamic_weight_optimizer.get_optimal_weights()

        # Simüle: 5 video, 3 hoca, 25 fact, 0 çelişki
        count = 5
        target = 4
        total_facts = 25
        teachers_count = 3
        unresolved_cnt = 0

        source_coverage = min(1.0, count / max(target, 1))       # 1.0
        evidence_density = min(1.0, total_facts / 20.0)           # 1.0
        verification_score = 1.0                                   # 1.0
        cross_teacher = min(1.0, teachers_count / 3.0)            # 1.0
        concept_cov = min(1.0, total_facts / 15.0)                # 1.0
        freshness = 1.0

        mastery_score = (
            weights["source_coverage"] * source_coverage +
            weights["evidence_density"] * evidence_density +
            weights["verification_score"] * verification_score +
            weights["cross_teacher_agreement"] * cross_teacher +
            weights["concept_coverage"] * concept_cov +
            weights["freshness"] * freshness
        )

        assert mastery_score >= 0.85, \
            f"Yeterli derinlikteki konu mastery_score {mastery_score:.3f} >= 0.85 olmalı!"
