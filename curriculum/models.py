"""
KPSS Super-Brain: Müfredat ve Kuyruk Veri Modelleri (Curriculum & Queue Models)
3 KPSS sınavı (Lisans, Ön Lisans, Ortaöğretim) ve tüm ders alanları için tip tanımları.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ExamLevel(str, Enum):
    """KPSS Sınav Düzeyleri"""
    LISANS = "KPSS_LISANS"
    ONLISANS = "KPSS_ONLISANS"
    ORTAOGRETIM = "KPSS_ORTAOGRETIM"
    ALL = "KPSS_ALL"

    @classmethod
    def from_str(cls, value: str) -> "ExamLevel":
        v = value.upper().strip()
        if "LISANS" in v and "ON" not in v:
            return cls.LISANS
        elif "ONLISANS" in v or "ÖNLİSANS" in v or "ON_LISANS" in v:
            return cls.ONLISANS
        elif "ORTA" in v or "LISE" in v:
            return cls.ORTAOGRETIM
        return cls.ALL


class LessonType(str, Enum):
    """KPSS Ders Kategorileri"""
    TARIH = "TARIH"
    COGRAFYA = "COGRAFYA"
    VATANDASLIK = "VATANDASLIK"
    TURKCE = "TURKCE"
    MATEMATIK = "MATEMATIK"
    SOZEL_MANTIK = "SOZEL_MANTIK"
    SAYISAL_MANTIK = "SAYISAL_MANTIK"
    GUNCEL = "GUNCEL"


class MasteryStage(str, Enum):
    """Konu Hakimiyet Düzeyleri (Minimum 3-4 Hoca Kuralı)"""
    UNSTARTED = "UNSTARTED"       # 0 video tüketildi
    STARTED = "STARTED"           # 1 video tüketildi
    DEVELOPING = "DEVELOPING"     # 2 video tüketildi
    SYNTHESIZING = "SYNTHESIZING" # 3 video tüketildi (Çapraz sentez aşaması)
    MASTERED = "MASTERED"         # 4+ video tüketildi ve konsolide edildi

    @classmethod
    def from_str(cls, value: str) -> "MasteryStage":
        v = (value or "").upper()
        if "MASTERED" in v:
            return cls.MASTERED
        elif "SYNTHESIZ" in v or "SENTEZ" in v or "3/4" in v:
            return cls.SYNTHESIZING
        elif "DEVELOP" in v or "GELIS" in v or "2/4" in v:
            return cls.DEVELOPING
        elif "START" in v or "BASLA" in v or "1/4" in v:
            return cls.STARTED
        return cls.UNSTARTED


class QueueStatus(str, Enum):
    """Video ve Görev Kuyruk Durumları"""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    WATCHED = "WATCHED"
    NO_TRANSCRIPT = "NO_TRANSCRIPT"
    FAILED = "FAILED"
    RETRY = "RETRY"


class TopicNode(BaseModel):
    """Müfredat Ağacındaki Tek Bir Konu Düğümü"""
    topic_id: str
    lesson: LessonType
    name: str
    subtopics: List[str] = Field(default_factory=list)
    exam_weights: Dict[str, str] = Field(default_factory=dict) # {"LISANS": "3-4 Soru", ...}
    target_videos_count: int = 4
    consumed_videos_count: int = 0
    distinct_teachers: List[str] = Field(default_factory=list)
    distinct_channels: List[str] = Field(default_factory=list)
    consumed_video_ids: List[str] = Field(default_factory=list)
    facts_count: int = 0
    traps_count: int = 0
    reasoning_count: int = 0
    mnemonics_count: int = 0
    mastery_stage: MasteryStage = MasteryStage.UNSTARTED
    is_mastered: bool = False
    last_digested_at: Optional[str] = None


class ResearchTask(BaseModel):
    """
    OpenManus veya Saha Ajanına İletilecek Yapılandırılmış Araştırma Görevi
    """
    task_id: str
    exam_level: ExamLevel = ExamLevel.ALL
    lesson: LessonType
    topic_id: str
    topic_name: str
    target_teachers: List[str] = Field(default_factory=list)
    target_channels: List[str] = Field(default_factory=list)
    search_queries: List[str] = Field(default_factory=list)
    needed_videos: int = 4
    current_videos: int = 0
    priority: float = 50.0
    reason: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class VideoItem(BaseModel):
    """Kuyruktaki Tek Bir Video Kaydı"""
    video_id: str
    url: str
    title: str = "KPSS Dersi"
    channel: str = "YouTube"
    teacher_name: str = "Genel"
    lesson: str = "GENEL"
    topic: str = "Genel"
    duration_seconds: int = 0
    status: QueueStatus = QueueStatus.PENDING
    priority: int = 10
    retry_count: int = 0
    transcript_length: int = 0
    chunks_extracted: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    watched_at: Optional[str] = None
    error_message: Optional[str] = None
