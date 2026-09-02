"""
OpenManus Bridge: Şemalar ve Veri Sözleşmeleri (Schemas & Contracts)
OpenManus saha işçisinin ürettiği arama ve araştırma sonuçlarının doğrulanmış şeması.
KURAL: Bu şema ve nesneler asla doğrudan kanonik veritabanı yazma yetkisine sahip değildir.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class DiscoveredVideo(BaseModel):
    """OpenManus tarafından keşfedilen aday video metaverisi"""
    video_id: str
    url: str
    title: str
    channel: str = "YouTube"
    teacher_name: str = "Genel"
    duration_seconds: int = 0

    @field_validator("video_id")
    @classmethod
    def validate_video_id(cls, v: str) -> str:
        clean_id = (v or "").strip()
        if not clean_id or len(clean_id) < 6 or clean_id.startswith(("fake_", "test_fake_")):
            raise ValueError(f"Geçersiz video_id: '{clean_id}'")
        return clean_id


class DiscoveredEvidence(BaseModel):
    """Arama ve sayfa taraması sırasında bulunan ham kanıt parçacığı"""
    source_url: str
    title: str = ""
    snippet: str
    timestamp_range: Optional[str] = None
    discovered_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ResearchResult(BaseModel):
    """
    OpenManus Araştırma Görevinin Çıktısı (Immutable Contract)
    KURAL: OpenManus bu çıktıyı teslim eder; doğrulama ve ambar kaydı Auditor tarafından yapılır.
    """
    task_id: str
    status: str = "SUCCESS" # SUCCESS, PARTIAL, DISCOVERY_FAILED, ERROR
    query: str
    videos: List[DiscoveredVideo] = Field(default_factory=list)
    raw_evidence: List[DiscoveredEvidence] = Field(default_factory=list)
    search_summary: str = ""
    total_found: int = 0
    executed_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def can_commit_directly(self) -> bool:
        """OpenManus asla doğrudan kanonik veritabanına yazamaz."""
        return False

    def can_modify_trust(self) -> bool:
        """OpenManus asla güven skoru değiştiremez."""
        return False
