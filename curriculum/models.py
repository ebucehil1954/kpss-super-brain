"""
KPSS Super-Brain: Müfredat ve Kuyruk Veri Modelleri (Curriculum & Queue Models)
3 KPSS sınavı (Lisans, Ön Lisans, Ortaöğretim) ve tüm ders alanları için tip tanımları.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, model_validator
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
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_str(cls, raw: Optional[str]) -> "LessonType":
        """
        [PHASE 8 SAFE LESSON RESOLVER]
        Çözümleme zinciri:
        EXACT -> ALIAS -> SEMANTIC -> UNKNOWN
        KURAL: Bilinmeyen veya belirsiz ders ASLA TARIH'e düşürülemez!
        """
        if not raw or not isinstance(raw, str):
            return cls.UNKNOWN

        clean = raw.strip().upper()
        # 1. Exact match
        for member in cls:
            if clean == member.value:
                return member

        # 2. Alias match
        ALIASES = {
            cls.TARIH: ["TARİH", "HISTORY", "INKILAP", "İNKILAP", "OSMANLI", "SELÇUKLU", "SELCUKLU"],
            cls.COGRAFYA: ["COĞRAFYA", "GEOGRAPHY", "YER SEKILLERI", "HARITA", "TÜRKİYE COĞRAFYASI", "TURKIYE COGRAFYASI"],
            cls.VATANDASLIK: ["VATANDAŞLIK", "CITIZENSHIP", "ANAYASA", "HUKUK", "IDARE HUKUKU", "İDARE HUKUKU", "YARGI", "YASAMA", "YÜRÜTME", "YURUTME"],
            cls.TURKCE: ["TÜRKÇE", "TURKISH", "DIL BILGISI", "DİL BİLGİSİ", "PARAGRAF", "SOZCUKTE ANLAM", "SÖZCÜKTE ANLAM"],
            cls.MATEMATIK: ["MATEMATİK", "MATH", "GEOMETRI", "GEOMETRİ", "SAYILAR", "PROBLEMLER", "CEBIR"],
            cls.SOZEL_MANTIK: ["SÖZEL MANTIK", "SOZEL MANTIK", "VERBAL LOGIC"],
            cls.SAYISAL_MANTIK: ["SAYISAL MANTIK", "NUMERICAL LOGIC"],
            cls.GUNCEL: ["GÜNCEL", "GENEL KÜLTÜR", "GENEL KULTUR", "CURRENT"]
        }

        for lesson_type, alias_list in ALIASES.items():
            if clean in alias_list or any(a in clean for a in alias_list):
                return lesson_type

        # 3. Bilinmeyen dersler kesinlikle UNKNOWN döner (Asla TARIH olmaz!)
        return cls.UNKNOWN


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
    TRANSCRIPT_PENDING = "TRANSCRIPT_PENDING"
    TRANSCRIPT_ACQUIRED = "TRANSCRIPT_ACQUIRED"
    TRANSCRIPT_DEFERRED = "TRANSCRIPT_DEFERRED"
    TRANSCRIPT_FAILED_TEMPORARY = "TRANSCRIPT_FAILED_TEMPORARY"
    NO_CAPTION_TRACK = "NO_CAPTION_TRACK"
    CAPTION_FETCH_FAILED = "CAPTION_FETCH_FAILED"
    YTDLP_BLOCKED = "YTDLP_BLOCKED"
    BROWSER_EXTRACTION_FAILED = "BROWSER_EXTRACTION_FAILED"
    AUDIO_DOWNLOAD_FAILED = "AUDIO_DOWNLOAD_FAILED"
    WHISPER_FAILED = "WHISPER_FAILED"
    VIDEO_UNAVAILABLE = "VIDEO_UNAVAILABLE"
    VIDEO_PRIVATE = "VIDEO_PRIVATE"
    VIDEO_AGE_RESTRICTED = "VIDEO_AGE_RESTRICTED"
    DISCOVERY_FAILED = "DISCOVERY_FAILED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class FailureClass(str, Enum):
    """[PHASE 13] Hata Sınıflandırması ve Yeniden Deneme Politikası"""
    TRANSIENT = "TRANSIENT"               # Geçici ağ hatası, timeout (Yeniden denenir)
    PERMANENT = "PERMANENT"               # Video silinmiş, gizli, 404 (ASLA yeniden denenmez)
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION" # Bozuk veri şeması (Doğrudan Dead-Letter)
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"   # API kotası doldu (Geciktirmeli yeniden deneme)
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


class TaskType(str, Enum):
    """Sistemdeki Bağımsız Görev Tipleri Sözleşmesi (Task Contracts)"""
    RESEARCH = "RESEARCH"
    VIDEO = "VIDEO"
    INGESTION = "INGESTION"
    ANALYSIS = "ANALYSIS"
    VERIFICATION = "VERIFICATION"


class ResearchTask(BaseModel):
    """
    OpenManus veya Saha Ajanına İletilecek Konu Keşif Görevi.
    KURAL: Asla doğrudan video yürütücüsüne iletilemez (VideoTask değildir).
    """
    task_type: TaskType = TaskType.RESEARCH
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


class VideoTask(BaseModel):
    """
    Keşfedilmiş ve doğrulanmış tek bir YouTube videosunun işlenme görevi.
    KURAL: Geçerli gerçek bir video_id zorunludur.
    """
    task_type: TaskType = TaskType.VIDEO
    task_id: str
    video_id: str
    url: str
    title: str = "KPSS Dersi"
    teacher_name: str = "Genel"
    lesson: str = "GENEL"
    topic: str = "Genel"
    duration_seconds: int = 0
    priority: int = 10
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @model_validator(mode="after")
    def validate_video_identity(self) -> "VideoTask":
        vid = (self.video_id or "").strip()
        if not vid or len(vid) < 6 or vid.startswith(("fake_", "test_fake_", "mock_fake_")):
            raise ValueError(f"Geçersiz VideoTask payload'ı: '{vid}' geçerli bir video_id olamaz!")
        return self


class IngestionTask(BaseModel):
    """Transkript ve altyazı çekme görevi"""
    task_type: TaskType = TaskType.INGESTION
    task_id: str
    video_id: str
    lesson: str
    topic: str


class AnalysisTask(BaseModel):
    """Transkriptten bilişsel iddia çıkarma görevi"""
    task_type: TaskType = TaskType.ANALYSIS
    task_id: str
    video_id: str
    transcript_text: str
    lesson: str
    topic: str
    teacher_name: str = "Genel"


class VerificationTask(BaseModel):
    """Aday iddiayı Z3 ve kanonik gerçeklikle doğrulama görevi"""
    task_type: TaskType = TaskType.VERIFICATION
    task_id: str
    claim_id: str
    claim_text: str
    lesson: str
    topic: str


def validate_task_contract(task_payload: Any, expected_type: TaskType) -> bool:
    """
    Bir görev nesnesinin beklenen tip sözleşmesine uyup uymadığını denetler.
    Örn: Bir ResearchTask asla VideoTask olarak kabul edilemez.
    """
    if not task_payload:
        return False
    
    t_type = getattr(task_payload, "task_type", None)
    if not t_type and isinstance(task_payload, dict):
        t_type = task_payload.get("task_type")

    if not t_type:
        # Eski modeller için duck typing kontrolü
        if expected_type == TaskType.VIDEO and hasattr(task_payload, "video_id") and not hasattr(task_payload, "search_queries"):
            return True
        if expected_type == TaskType.RESEARCH and hasattr(task_payload, "search_queries"):
            return True
        return False

    t_type_str = t_type.value if hasattr(t_type, "value") else str(t_type)
    return t_type_str.upper() == expected_type.value.upper()


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
