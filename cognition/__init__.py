"""
KPSS Super-Brain: Bilişsel ve Zihin Modelleme Katmanı (Cognition)
"""
from .teacher_learner import teacher_learner, TeacherLearner
from .cross_teacher_analyzer import cross_teacher_analyzer, CrossTeacherAnalyzer
from .reasoning_engine import reasoning_engine, ReasoningEngine
from .topic_linker import topic_linker, TopicLinker
from .pattern_learner import pattern_learner, PatternLearner
from .self_tester import self_tester, SelfTester
from .analyst import cognitive_analyst, CognitiveAnalyst
from .correlation_engine import correlation_engine, CorrelationEngine
from .auditor import auditor_engine, AuditorEngine
from .prosecutor_auditor import prosecutor_auditor, ProsecutorAuditor

__all__ = [
    "teacher_learner",
    "TeacherLearner",
    "cross_teacher_analyzer",
    "CrossTeacherAnalyzer",
    "reasoning_engine",
    "ReasoningEngine",
    "topic_linker",
    "TopicLinker",
    "pattern_learner",
    "PatternLearner",
    "self_tester",
    "SelfTester",
    "cognitive_analyst",
    "CognitiveAnalyst",
    "correlation_engine",
    "CorrelationEngine",
    "auditor_engine",
    "AuditorEngine",
    "prosecutor_auditor",
    "ProsecutorAuditor"
]
