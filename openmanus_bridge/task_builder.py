"""
OpenManus Bridge: Görev Oluşturucu (Task Builder)
Supervisor'dan gelen ResearchTask'i OpenManus saha işçisinin anlayacağı
yapılandırılmış komut ve arama talimatlarına dönüştürür.
"""
from typing import Dict, Any, List
from curriculum.models import ResearchTask


class OpenManusTaskBuilder:
    @staticmethod
    def build_research_payload(task: ResearchTask) -> Dict[str, Any]:
        """Araştırma görevini OpenManus formatına dönüştürür."""
        teacher_query = f"{task.target_teachers[0]} " if task.target_teachers else ""
        primary_query = task.search_queries[0] if task.search_queries else f"KPSS {task.lesson.value} {task.topic_name} {teacher_query}"

        return {
            "task_id": task.task_id,
            "goal": f"KPSS {task.lesson.value} - {task.topic_name} ders videolarını ve konu özetlerini araştır.",
            "lesson": task.lesson.value,
            "topic": task.topic_name,
            "primary_query": primary_query.strip(),
            "target_teachers": task.target_teachers,
            "target_channels": task.target_channels,
            "max_videos": task.needed_videos
        }
