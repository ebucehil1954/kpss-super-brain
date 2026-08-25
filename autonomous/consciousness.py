"""
KPSS Super-Brain: Otonom Bilinç ve Düşünce Günlüğü Motoru (Consciousness & CoT Engine v3)
"Bilinçli ilerlesin, nerede ne yaptığını ve neden yaptığını bilsin."
Ajanın neden bir konuyu seçtiğini, hangi pedagojik gerekçeyle öğrendiğini ve müfredat yol haritasında
nerede olduğunu adım adım (Chain-of-Thought) akıl yürüterek kaydeder ve yönetir.
"""
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import super_brain_config
from brain.episodic_memory import episodic_memory
from brain.knowledge_store import knowledge_store
from brain.deep_ontology import deep_ontology
from cognition.prediction_engine import prediction_engine
from cognition.self_tester import self_tester

class ConsciousnessEngine:
    def __init__(self):
        self.current_focus: Optional[Dict[str, Any]] = None
        self.learning_trajectory: List[Dict[str, Any]] = []

    def deliberate_next_step(self) -> Dict[str, Any]:
        """
        Üst-akıl deliberasyon süreci (Chain of Thought):
        1. Bilişsel boşlukları tara (SelfTester)
        2. 2026 KPSS soru tahmin radarını incele (PredictionEngine)
        3. Bilgi grafiğindeki önkoşul hiyerarşisini kontrol et (DeepOntology)
        4. En yüksek katma değerli (ROI) ve bilinçli öğrenme kararını üret ve gerekçelendir.
        """
        now_str = datetime.now().isoformat()
        health = self_tester.evaluate_knowledge_health()
        critical_gaps = health.get("critical_gaps", [])
        predictions = prediction_engine.HIGH_PROBABILITY_TOPIC_TARGETS
        stats_info = knowledge_store.get_stats()

        cot_reasoning_steps = []
        
        # 1. Adım: Durum Muhakemesi
        total_records = stats_info.get("total_records", 0)
        cot_reasoning_steps.append(f"1. [DURUM BİLİNCİ] Zihin ambarında toplam {total_records} doğrulanmış bilgi var. Bilişsel olgunluk skoru: %{health.get('maturity_score', 0)}.")

        # 2. Adım: Kritik Boşluk Analizi
        if critical_gaps:
            top_gap = critical_gaps[0]
            lesson = top_gap["lesson"]
            topic = top_gap["topic"]
            current_records = top_gap.get("current_records", 0)
            cot_reasoning_steps.append(f"2. [EKSİK TESPİTİ] '{lesson}' dersinin '{topic}' konusunda sadece {current_records} kayıt tespit edildi. Bu konu kritik bir kör nokta.")
        else:
            # Tahmin motorundan yüksek olasılıklı konuyu seç
            import random
            pred = random.choice(predictions)
            lesson = pred.get("lesson", "VATANDASLIK")
            topic = pred.get("topic", "1982 Anayasası Temel Haklar")
            cot_reasoning_steps.append(f"2. [RADAR ODAĞI] 2026 KPSS Tahmin Radarında %{int(pred.get('probability', 0.9)*100)} olasılıkla çıkacak olan '{lesson} - {topic}' konusuna odaklanılıyor.")

        # 3. Adım: Eğitmen ve Kaynak Stratejisi Belirleme
        teacher_match = "Genel Müfredat"
        for t in super_brain_config.TARGET_TEACHERS:
            if t["lesson"] == lesson:
                teacher_match = t["name"]
                break

        cot_reasoning_steps.append(f"3. [PEDAGOJİK TERCİH] Bu konuda en yetkin KPSS eğitmeni olarak '{teacher_match}' hocanın ders anlatımları ve hafıza şifreleri incelenecek.")

        # 4. Adım: Eylem ve Nihai Karar
        action_type = "YOUTUBE_DEEP_INGEST" if current_records == 0 else "CROSS_CHECK_AND_MINT"
        cot_reasoning_steps.append(f"4. [EYLEM PLANI] Seçilen Strateji: {action_type}. Transkriptler ve mevzuat ambarı çapraz doğrulanarak kalıcı hafızaya işlenecek.")

        decision = {
            "decision_id": f"dec_{int(time.time()*1000)}",
            "timestamp": now_str,
            "target_lesson": lesson,
            "target_topic": topic,
            "recommended_teacher": teacher_match,
            "action_type": action_type,
            "chain_of_thought": cot_reasoning_steps,
            "rationale": " | ".join(cot_reasoning_steps)
        }

        self.current_focus = decision
        self.learning_trajectory.append(decision)

        # Epizodik hafızaya bilinçli karar kaydı düş
        episodic_memory.record_learning_event(
            event_type="CONSCIOUS_DECISION_COT",
            topic=topic,
            lesson=lesson,
            summary=f"Ajan bilinçli bir akıl yürütme ile '{lesson} - {topic}' konusunu öğrenme kararı aldı.",
            details=decision,
            confidence_gain=0.05
        )

        return decision

    def get_current_consciousness_state(self) -> Dict[str, Any]:
        """Ajanın şu anki zihinsel odağını ve yol haritası ilerlemesini döner."""
        curriculum_stats = deep_ontology.get_curriculum_statistics()
        return {
            "active_focus": self.current_focus,
            "curriculum_coverage": curriculum_stats,
            "total_deliberations": len(self.learning_trajectory),
            "recent_decisions": self.learning_trajectory[-5:]
        }

consciousness = ConsciousnessEngine()
