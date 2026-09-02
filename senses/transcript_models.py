"""
KPSS Super-Brain: Transcript Intelligence V1 — Ortak Veri Modelleri ve Kontratlar
Tüm transkript sağlayıcıları (Providers), ağ geçidi (Gateway) ve işleyici (Processor)
bu sağlayıcıdan bağımsız (provider-agnostic) ortak kontratı kullanır.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TranscriptProviderType(str, Enum):
    """Desteklenen transkript sağlayıcı türleri"""
    YOUTUBE_CAPTIONS = "YOUTUBE_CAPTIONS"
    YTDLP_SUBTITLES = "YTDLP_SUBTITLES"
    BROWSER_PLAYWRIGHT = "BROWSER_PLAYWRIGHT"
    LOCAL_WHISPER = "LOCAL_WHISPER"
    DISK_CACHE = "DISK_CACHE"


class TranscriptStatus(str, Enum):
    """Zengin transkript ve altyazı durum taksonomisi"""
    TRANSCRIPT_PENDING = "TRANSCRIPT_PENDING"
    CAPTION_ATTEMPT = "CAPTION_ATTEMPT"
    YTDLP_ATTEMPT = "YTDLP_ATTEMPT"
    BROWSER_ATTEMPT = "BROWSER_ATTEMPT"
    WHISPER_ATTEMPT = "WHISPER_ATTEMPT"
    TRANSCRIPT_ACQUIRED = "TRANSCRIPT_ACQUIRED"
    
    # Hata Durumları
    NO_CAPTION_TRACK = "NO_CAPTION_TRACK"
    CAPTION_FETCH_FAILED = "CAPTION_FETCH_FAILED"
    YTDLP_BLOCKED = "YTDLP_BLOCKED"
    BROWSER_EXTRACTION_FAILED = "BROWSER_EXTRACTION_FAILED"
    AUDIO_DOWNLOAD_FAILED = "AUDIO_DOWNLOAD_FAILED"
    WHISPER_FAILED = "WHISPER_FAILED"
    
    # Video Kısıtlamaları (Kalıcı / Permanent)
    VIDEO_UNAVAILABLE = "VIDEO_UNAVAILABLE"
    VIDEO_PRIVATE = "VIDEO_PRIVATE"
    VIDEO_AGE_RESTRICTED = "VIDEO_AGE_RESTRICTED"
    VIDEO_REGION_RESTRICTED = "VIDEO_REGION_RESTRICTED"
    
    # Yönetimsel Durumlar
    TRANSCRIPT_FAILED_TEMPORARY = "TRANSCRIPT_FAILED_TEMPORARY"
    UNKNOWN_TRANSCRIPT_ERROR = "UNKNOWN_TRANSCRIPT_ERROR"
    TRANSCRIPT_DEFERRED = "TRANSCRIPT_DEFERRED"


class TranscriptSegment(BaseModel):
    """Zaman damgalı tekil transkript segmenti"""
    segment_id: str
    video_id: str
    start_seconds: float
    end_seconds: float
    text: str
    segment_hash: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.segment_hash:
            raw = f"{self.video_id}:{self.start_seconds}:{self.end_seconds}:{self.text.strip()}"
            self.segment_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class TranscriptDiagnostics(BaseModel):
    """Her sağlayıcı denemesinin adli teşhis kaydı"""
    video_id: str
    provider: TranscriptProviderType
    attempt_number: int = 1
    status: TranscriptStatus
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: int = 0


class TranscriptResult(BaseModel):
    """
    Standartlaştırılmış ortak transkript sonucu.
    TranscriptProcessor sağlayıcıların iç yapısını bilmez, sadece bu modeli tüketir.
    """
    video_id: str
    success: bool
    provider: Optional[TranscriptProviderType] = None
    language: str = "tr"
    is_generated: bool = False
    segments: List[TranscriptSegment] = Field(default_factory=list)
    confidence: float = 0.95
    full_text: str = ""
    cached: bool = False
    error: Optional[str] = None
    status: TranscriptStatus = TranscriptStatus.TRANSCRIPT_PENDING
    diagnostics: List[TranscriptDiagnostics] = Field(default_factory=list)
    attempts: int = 0

    def model_post_init(self, __context: Any) -> None:
        if not self.full_text and self.segments:
            self.full_text = " ".join(s.text for s in self.segments if s.text).strip()


class TranscriptProvider(ABC):
    """Tüm transkript sağlayıcıları için ortak arayüz kontratı"""

    @property
    @abstractmethod
    def provider_type(self) -> TranscriptProviderType:
        """Sağlayıcı tipini döndürür"""
        pass

    @abstractmethod
    def supports(self, video_id: str) -> bool:
        """Bu sağlayıcının verilen videoyu destekleyip desteklemediğini kontrol eder"""
        pass

    @abstractmethod
    async def attempt(self, video_id: str, **kwargs) -> TranscriptResult:
        """Transkript çekme denemesi yapar ve standart TranscriptResult döndürür"""
        pass
