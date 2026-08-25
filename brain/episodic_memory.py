"""
KPSS Super-Brain: Otonom Epizodik Bellek (Episodic Memory & Session Journal)
Ajanın ne zaman, hangi kaynaktan ne öğrendiğini, hangi hipotezleri kurup test ettiğini kaydeder.
"""
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import super_brain_config

class EpisodicMemory:
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or str(super_brain_config.EPISODIC_LOG_FILE)
        self.episodes: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    self.episodes = json.load(f)
            except Exception:
                self.episodes = []

    def _save(self):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.episodes, f, ensure_ascii=False, indent=2)

    def record_learning_event(
        self,
        event_type: str, # "YOUTUBE_WATCH", "WEB_RESEARCH", "QUESTION_SOLVE", "PATTERN_DISCOVERY", "EXAM_PREDICTION"
        topic: str,
        lesson: str,
        summary: str,
        details: Dict[str, Any],
        confidence_gain: float = 0.05
    ) -> Dict[str, Any]:
        """
        Yeni bir öğrenme olayını epizodik hafızaya kaydeder.
        """
        episode = {
            "id": f"ep_{int(datetime.now().timestamp()*1000)}",
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "lesson": lesson,
            "topic": topic,
            "summary": summary,
            "confidence_gain": confidence_gain,
            "details": details
        }
        self.episodes.append(episode)
        self._save()
        return episode

    def get_recent_episodes(self, limit: int = 20, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        filtered = self.episodes
        if event_type:
            filtered = [e for e in filtered if e.get("event_type") == event_type]
        return list(reversed(filtered[-limit:]))

    def get_summary_statistics(self) -> Dict[str, Any]:
        total = len(self.episodes)
        event_counts = {}
        lessons_learned = {}
        for ep in self.episodes:
            et = ep.get("event_type", "OTHER")
            ls = ep.get("lesson", "OTHER")
            event_counts[et] = event_counts.get(et, 0) + 1
            lessons_learned[ls] = lessons_learned.get(ls, 0) + 1

        return {
            "total_learning_episodes": total,
            "event_counts": event_counts,
            "lessons_learned": lessons_learned,
            "last_active": self.episodes[-1]["timestamp"] if self.episodes else None
        }

    def get_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Ajanın aldığı bilinçli kararları (CoT) listeler."""
        return self.get_recent_episodes(limit=limit, event_type="CONSCIOUS_DECISION_COT")

episodic_memory = EpisodicMemory()
