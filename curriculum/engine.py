"""
KPSS Super-Brain: Müfredat ve Eksiklik Radarı Motoru (Curriculum & Gap Radar Engine)
3 KPSS sınavı için tüm konuları yönetir, canlı video hakimiyet durumunu izler ve
OpenManus için en yüksek öncelikli araştırma görevlerini (ResearchTask) üretir.
"""
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

from curriculum.models import (
    ExamLevel,
    LessonType,
    MasteryStage,
    TopicNode,
    ResearchTask
)
from curriculum.sources import (
    get_teachers_for_lesson,
    generate_search_queries,
    GOLD_STANDARD_CHANNELS
)
from brain.database import db_session
from brain.curriculum_matrix import CurriculumMatrixEngine


class CurriculumEngine:
    """
    KPSS Lisans, Ön Lisans ve Ortaöğretim müfredatını yöneten merkezi motor.
    """

    def __init__(self):
        self.raw_curriculum = CurriculumMatrixEngine.OFFICIAL_CURRICULUM

    def get_all_topics(self, lesson_filter: Optional[LessonType] = None) -> List[TopicNode]:
        """Tüm müfredat konularını TopicNode nesneleri olarak döner."""
        nodes = []
        for l_key, topics in self.raw_curriculum.items():
            try:
                l_type = LessonType(l_key)
            except ValueError:
                continue

            if lesson_filter and l_type != lesson_filter:
                continue

            for t_key, t_data in topics.items():
                node = TopicNode(
                    topic_id=f"{l_key}_{t_key}",
                    lesson=l_type,
                    name=t_data.get("name", t_key),
                    subtopics=t_data.get("subtopics", []),
                    exam_weights={"GENEL": t_data.get("exam_question_weight", "1-2 Soru")},
                    target_videos_count=t_data.get("target_videos", 4)
                )
                nodes.append(node)
        return nodes

    def sync_with_db(self):
        """Müfredat konularını SQLite topic_mastery tablosu ile eşitler."""
        all_topics = self.get_all_topics()
        now_str = datetime.now().isoformat()

        with db_session() as conn:
            cursor = conn.cursor()
            for topic in all_topics:
                cursor.execute("""
                INSERT INTO topic_mastery (
                    topic_id, lesson, topic_name, target_videos_count,
                    consumed_videos_count, distinct_teachers_json, distinct_channels_json,
                    consumed_video_ids_json, facts_count, traps_count,
                    reasoning_count, mnemonics_count, mastery_stage,
                    is_mastered, updated_at
                ) VALUES (?, ?, ?, ?, 0, '[]', '[]', '[]', 0, 0, 0, 0, 'UNSTARTED', 0, ?)
                ON CONFLICT(topic_id) DO NOTHING
                """, (
                    topic.topic_id,
                    topic.lesson.value,
                    topic.name,
                    topic.target_videos_count,
                    now_str
                ))

    def get_live_mastery_status(self) -> List[TopicNode]:
        """Veritabanındaki canlı video izlenme ve hoca çeşitliliği metriklerini döner."""
        self.sync_with_db()
        nodes = []

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM topic_mastery
            ORDER BY consumed_videos_count ASC, topic_id ASC
            """)
            rows = cursor.fetchall()

            for row in rows:
                r = dict(row)
                try:
                    l_type = LessonType(r["lesson"])
                except ValueError:
                    l_type = LessonType.TARIH

                teachers = json.loads(r.get("distinct_teachers_json", "[]"))
                channels = json.loads(r.get("distinct_channels_json", "[]"))
                video_ids = json.loads(r.get("consumed_video_ids_json", "[]"))
                stage = MasteryStage.from_str(r.get("mastery_stage", "UNSTARTED"))

                node = TopicNode(
                    topic_id=r["topic_id"],
                    lesson=l_type,
                    name=r["topic_name"],
                    target_videos_count=r.get("target_videos_count", 4),
                    consumed_videos_count=r.get("consumed_videos_count", 0),
                    distinct_teachers=teachers,
                    distinct_channels=channels,
                    consumed_video_ids=video_ids,
                    facts_count=r.get("facts_count", 0),
                    traps_count=r.get("traps_count", 0),
                    reasoning_count=r.get("reasoning_count", 0),
                    mnemonics_count=r.get("mnemonics_count", 0),
                    mastery_stage=stage,
                    is_mastered=bool(r.get("is_mastered", 0)),
                    last_digested_at=r.get("last_digested_at")
                )
                nodes.append(node)

        return nodes

    def get_gap_analysis(self, exam_level: ExamLevel = ExamLevel.ALL) -> Dict[str, Any]:
        """
        Müfredat kapsamı ve eksik video radar raporunu hesaplar.
        """
        nodes = self.get_live_mastery_status()
        total_topics = len(nodes)
        unstarted = sum(1 for n in nodes if n.mastery_stage == MasteryStage.UNSTARTED)
        started = sum(1 for n in nodes if n.mastery_stage == MasteryStage.STARTED)
        developing = sum(1 for n in nodes if n.mastery_stage == MasteryStage.DEVELOPING)
        synthesizing = sum(1 for n in nodes if n.mastery_stage == MasteryStage.SYNTHESIZING)
        mastered = sum(1 for n in nodes if n.mastery_stage == MasteryStage.MASTERED)

        total_videos_consumed = sum(n.consumed_videos_count for n in nodes)
        total_target_videos = sum(n.target_videos_count for n in nodes)
        coverage_pct = round((total_videos_consumed / total_target_videos * 100), 1) if total_target_videos > 0 else 0.0

        lesson_stats: Dict[str, Any] = {}
        for n in nodes:
            l_name = n.lesson.value
            if l_name not in lesson_stats:
                lesson_stats[l_name] = {"total_topics": 0, "consumed_videos": 0, "target_videos": 0, "mastered_topics": 0}
            lesson_stats[l_name]["total_topics"] += 1
            lesson_stats[l_name]["consumed_videos"] += n.consumed_videos_count
            lesson_stats[l_name]["target_videos"] += n.target_videos_count
            if n.is_mastered:
                lesson_stats[l_name]["mastered_topics"] += 1

        return {
            "exam_level": exam_level.value,
            "total_topics": total_topics,
            "coverage_percentage": coverage_pct,
            "total_videos_consumed": total_videos_consumed,
            "total_target_videos": total_target_videos,
            "stages": {
                "UNSTARTED (0 Video)": unstarted,
                "STARTED (1 Video)": started,
                "DEVELOPING (2 Video)": developing,
                "SYNTHESIZING (3 Video)": synthesizing,
                "MASTERED (4+ Video)": mastered
            },
            "by_lesson": lesson_stats
        }

    def generate_next_research_tasks(
        self,
        count: int = 5,
        exam_level: ExamLevel = ExamLevel.ALL,
        lesson_filter: Optional[LessonType] = None
    ) -> List[ResearchTask]:
        """
        OpenManus veya otonom crawler için en acil video ihtiyacı olan konulardan
        hazır görev paketleri (ResearchTask) üretir.
        """
        nodes = self.get_live_mastery_status()
        
        # Filtreleme
        if lesson_filter:
            nodes = [n for n in nodes if n.lesson == lesson_filter]

        # Eksiklik ve öncelik sıralaması (En az videosu olan ve hedefi yüksek olanlar önce)
        def priority_key(node: TopicNode) -> float:
            needed = max(0, node.target_videos_count - node.consumed_videos_count)
            # Eğer hiç başlanmamışsa en yüksek öncelik
            base = needed * 20.0
            # Hoca çeşitliliği azsa ek puan
            if len(node.distinct_teachers) < 2:
                base += 15.0
            return base

        sorted_nodes = sorted(nodes, key=priority_key, reverse=True)
        tasks = []

        for idx, node in enumerate(sorted_nodes[:count], start=1):
            needed = max(0, node.target_videos_count - node.consumed_videos_count)
            if needed == 0:
                continue

            teachers = get_teachers_for_lesson(node.lesson)
            # Henüz dinlenmemiş hocaları önceliklendir
            consumed_teachers = set(node.distinct_teachers)
            target_teachers = [t["name"] for t in teachers if t["name"] not in consumed_teachers]
            if not target_teachers:
                target_teachers = [t["name"] for t in teachers]

            queries = generate_search_queries(
                lesson=node.lesson,
                topic_name=node.name,
                exam_level=exam_level
            )

            task = ResearchTask(
                task_id=f"TASK_{node.topic_id}_{idx}",
                exam_level=exam_level,
                lesson=node.lesson,
                topic_id=node.topic_id,
                topic_name=node.name,
                target_teachers=target_teachers[:3],
                target_channels=GOLD_STANDARD_CHANNELS[:3],
                search_queries=queries,
                needed_videos=needed,
                current_videos=node.consumed_videos_count,
                priority=priority_key(node),
                reason=f"Müfredat eksiği: {node.consumed_videos_count}/{node.target_videos_count} video izlendi."
            )
            tasks.append(task)

        return tasks


curriculum_engine = CurriculumEngine()
