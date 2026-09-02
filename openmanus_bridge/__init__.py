"""
OpenManus Bridge Paketi
Saha işçisi OpenManus ile KPSS Super-Brain orkestratörü arasındaki sıkı sözleşme katmanı.
"""
from openmanus_bridge.schemas import ResearchResult, DiscoveredVideo, DiscoveredEvidence
from openmanus_bridge.task_builder import OpenManusTaskBuilder
from openmanus_bridge.result_parser import OpenManusResultParser
from openmanus_bridge.client import OpenManusBridgeClient, openmanus_bridge_client

__all__ = [
    "ResearchResult",
    "DiscoveredVideo",
    "DiscoveredEvidence",
    "OpenManusTaskBuilder",
    "OpenManusResultParser",
    "OpenManusBridgeClient",
    "openmanus_bridge_client"
]
