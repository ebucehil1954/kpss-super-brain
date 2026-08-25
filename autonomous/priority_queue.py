"""
KPSS Super-Brain: Dinamik Açgözlü Öncelik Kuyruğu (Hungry Dynamic Priority Queue)
Konu doygunluk derecesine (satiation), sınav çıkma olasılığına ve bilişsel kör noktalara
göre öğrenme hedeflerini dinamik önceliklendirir.
"""
import time
import json
import heapq
from typing import Dict, Any, List, Optional
from datetime import datetime

class DynamicPriorityQueue:
    def __init__(self):
        # Priority heap: elements are (-effective_priority, timestamp, item)
        self._heap = []
        self._counter = 0
        self._topic_satiation: Dict[str, float] = {} # topic -> satiation (0.0 to 1.0)
        self._topic_last_consumed: Dict[str, float] = {}

    def calculate_urgency(
        self,
        lesson: str,
        topic: str,
        exam_probability: float = 0.85,
        current_records_count: int = 0
    ) -> float:
        """
        Doygunluk ve eksikliğe göre öncelik katsayısı hesaplar (0 - 100).
        - Hiç bilinmeyen konu -> En yüksek öncelik
        - Çok bilinen (doymuş) konu -> Düşük öncelik
        - Sınav olasılığı yüksek konu -> Çarpan etkisi
        """
        satiation = min(1.0, current_records_count / 15.0)
        self._topic_satiation[f"{lesson}_{topic}"] = satiation
        
        # Hunger / Urgency formülü
        urgency = (1.0 - satiation * 0.7) * (exam_probability * 100.0)
        return round(urgency, 2)

    def enqueue(
        self,
        source_type: str, # "YOUTUBE", "WEB_ACADEMIC", "PDF_DOCUMENT", "MEVZUAT_GOV", "TUIK"
        lesson: str,
        topic: str,
        payload: Dict[str, Any],
        base_priority: float = 50.0
    ):
        """Kuyruğa yeni bir tüketim görevi ekler."""
        key = f"{lesson}_{topic}"
        satiation = self._topic_satiation.get(key, 0.0)
        
        # Son tüketimden bu yana geçen zaman (Zamanla açlık tekrar artar)
        last_time = self._topic_last_consumed.get(key, 0.0)
        time_diff = time.time() - last_time if last_time > 0 else 3600
        hunger_boost = min(20.0, time_diff / 300.0) # 15 dakikada +20 puan

        effective_priority = base_priority * (1.1 - satiation * 0.5) + hunger_boost

        item = {
            "source_type": source_type,
            "lesson": lesson,
            "topic": topic,
            "payload": payload,
            "enqueued_at": datetime.now().isoformat(),
            "priority": effective_priority
        }

        self._counter += 1
        heapq.heappush(self._heap, (-effective_priority, self._counter, item))

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """En yüksek açlık/öncelik derecesine sahip görevi çeker."""
        if not self._heap:
            return None
        _, _, item = heapq.heappop(self._heap)
        
        key = f"{item['lesson']}_{item['topic']}"
        self._topic_last_consumed[key] = time.time()
        return item

    def peek(self) -> Optional[Dict[str, Any]]:
        if not self._heap:
            return None
        return self._heap[0][2]

    def size(self) -> int:
        return len(self._heap)

    def update_satiation(self, lesson: str, topic: str, new_records_added: int):
        """Konu öğrenildikçe doygunluk skorunu günceller."""
        key = f"{lesson}_{topic}"
        curr = self._topic_satiation.get(key, 0.0)
        self._topic_satiation[key] = min(1.0, curr + (new_records_added * 0.05))

priority_queue = DynamicPriorityQueue()
