"""
KPSS Super-Brain: Konular Arası İlişki ve Ön Koşul Haritalayıcısı (Topic Mapper)
"""
from typing import List, Dict, Any
from brain.knowledge_graph import kpss_knowledge_graph

class TopicMapper:
    @staticmethod
    def get_prerequisites_and_associations(topic_id: str) -> Dict[str, Any]:
        related = kpss_knowledge_graph.get_related_nodes(topic_id)
        return {
            "topic_id": topic_id,
            "related_nodes_count": len(related),
            "related_nodes": related
        }

topic_mapper = TopicMapper()
