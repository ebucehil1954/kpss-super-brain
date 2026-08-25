"""
KPSS Super-Brain: Tip Güvenli ve Hız Korumalı Araç Kayıt Defteri (Tool Registry v5)
Pydantic v2 şema doğrulamalı, token bucket hız sınırlayıcılı (rate limiter),
zaman aşımı (timeout) ve hata sınıflandırmalı araç yönetim merkezi.
"""
from __future__ import annotations

import asyncio
import inspect
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable, Type
from pydantic import BaseModel, Field, ValidationError
from brain.errors import ToolError, ErrorSeverity, ErrorRetryability

class ToolDefinition(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str
    input_model: Optional[Type[BaseModel]] = None
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 30.0
    retry_policy: int = 2
    side_effects: bool = False
    rate_limit_per_min: int = 60

class ToolRateLimiter:
    """Sliding window tabanlı basit ve etkin hız sınırlayıcı."""
    def __init__(self, max_per_min: int = 60):
        self.max_per_min = max_per_min
        self.timestamps: List[float] = []

    def acquire(self) -> bool:
        now = time.time()
        # 60 saniyeden eski zaman damgalarını temizle
        self.timestamps = [t for t in self.timestamps if now - t < 60.0]
        if len(self.timestamps) >= self.max_per_min:
            return False
        self.timestamps.append(now)
        return True

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._executors: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self._limiters: Dict[str, ToolRateLimiter] = {}

    def register(self, definition: ToolDefinition, func: Callable[..., Any]):
        """Yeni bir aracı kayıt defterine bağlar."""
        self._tools[definition.name] = definition
        self._executors[definition.name] = func
        self._limiters[definition.name] = ToolRateLimiter(max_per_min=definition.rate_limit_per_min)

    def get_tool_definition(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Mevcut tüm araçların şema ve açıklamalarını listeler."""
        return [
            {
                "name": t.name,
                "version": t.version,
                "description": t.description,
                "input_schema": t.input_schema,
                "side_effects": t.side_effects,
                "rate_limit_per_min": t.rate_limit_per_min
            }
            for t in self._tools.values()
        ]

    async def execute(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aracı Pydantic şema doğrulaması, hız sınırı, zaman aşımı ve hata kalkanıyla çalıştırır.
        """
        tool_def = self._tools.get(name)
        func = self._executors.get(name)
        limiter = self._limiters.get(name)

        if not tool_def or not func:
            return {
                "success": False,
                "tool": name,
                "error": f"Tool '{name}' kayıt defterinde bulunamadı.",
                "retryable": False,
                "output": None
            }

        # 1. Hız Sınırı Denetimi (Rate Limit)
        if limiter and not limiter.acquire():
            return {
                "success": False,
                "tool": name,
                "error": f"Tool '{name}' hız sınırı aşıldı ({tool_def.rate_limit_per_min} istek/dk).",
                "retryable": True,
                "output": None
            }

        # 2. Pydantic Model Doğrulaması (Varsa)
        if tool_def.input_model:
            try:
                validated_obj = tool_def.input_model(**params)
                params = validated_obj.model_dump()
            except ValidationError as ve:
                return {
                    "success": False,
                    "tool": name,
                    "error": f"Geçersiz girdi parametreleri: {str(ve)}",
                    "retryable": False,
                    "output": None
                }

        start_t = time.time()
        retries = tool_def.retry_policy

        for attempt in range(1, retries + 2):
            try:
                if inspect.iscoroutinefunction(func):
                    res = await asyncio.wait_for(func(**params), timeout=tool_def.timeout_seconds)
                else:
                    res = await asyncio.to_thread(func, **params)

                duration_ms = round((time.time() - start_t) * 1000, 2)
                return {
                    "success": True,
                    "tool": name,
                    "duration_ms": duration_ms,
                    "attempt": attempt,
                    "retryable": False,
                    "output": res
                }
            except asyncio.TimeoutError:
                if attempt > retries:
                    return {
                        "success": False,
                        "tool": name,
                        "error": f"Tool '{name}' {tool_def.timeout_seconds}s içinde zaman aşımına uğradı.",
                        "retryable": True,
                        "output": None
                    }
                await asyncio.sleep(0.5)
            except Exception as e:
                if attempt > retries:
                    return {
                        "success": False,
                        "tool": name,
                        "error": f"Çalıştırma hatası: {str(e)}",
                        "retryable": False,
                        "output": None
                    }
                await asyncio.sleep(0.5)

# Global Kayıt Defteri Örneği
tool_registry = ToolRegistry()

# ==========================================
# TEMEL KPSS ARAŞTIRMA ARAÇLARININ ENTEGRASYONU
# ==========================================
from senses.video_crawler import video_crawler
from senses.transcript_fetcher import transcript_fetcher
from senses.mevzuat_crawler import mevzuat_crawler, MevzuatCrawler
from senses.tuik_fetcher import tuik_fetcher, TuikMtaFetcher
from anti_hallucination.fact_checker import fact_checker
from brain.knowledge_store import knowledge_store

# 1. YouTube Video Keşif Aracı
class YouTubeSearchInput(BaseModel):
    topic: str
    lesson: str = "GENEL"
    limit: int = Field(default=5, ge=1, le=50)

tool_registry.register(
    ToolDefinition(
        name="youtube_search",
        description="Belirli bir KPSS dersi ve konusu için popüler hoca videolarını ve oynatma listelerini arar.",
        input_model=YouTubeSearchInput,
        input_schema={"topic": "str", "lesson": "str", "limit": "int"},
        timeout_seconds=20.0,
        rate_limit_per_min=120
    ),
    lambda topic, lesson="GENEL", limit=5: video_crawler.search_topic_videos(topic, lesson=lesson, max_results=limit)
)

# 2. Transkript Çekim Aracı
class TranscriptFetchInput(BaseModel):
    video_id: str

tool_registry.register(
    ToolDefinition(
        name="transcript_fetch",
        description="YouTube video ID'si verilen dersin altyazısını ve zaman damgalı segmentlerini çeker.",
        input_model=TranscriptFetchInput,
        input_schema={"video_id": "str"},
        timeout_seconds=25.0,
        rate_limit_per_min=100
    ),
    lambda video_id: transcript_fetcher.fetch_transcript_resilient(video_id)
)

# 3. Resmi Mevzuat ve Kanun Arama
tool_registry.register(
    ToolDefinition(
        name="official_mevzuat_search",
        description="Resmi Gazete ve mevzuat.gov.tr üzerinden güncel kanun ve anayasa maddelerini sorgular.",
        input_schema={"query": "str", "topic": "str"},
        timeout_seconds=15.0,
        rate_limit_per_min=60
    ),
    lambda query, topic="": MevzuatCrawler.search_legislation(query, topic)
)

# 4. TÜİK & MTA İstatistik Arama
tool_registry.register(
    ToolDefinition(
        name="tuik_mta_search",
        description="TÜİK nüfus/tarım ve MTA maden verilerini en güncel resmî tablolardan sorgular.",
        input_schema={"topic": "str"},
        timeout_seconds=15.0,
        rate_limit_per_min=60
    ),
    lambda topic: TuikMtaFetcher.fetch_latest_stats(topic)
)

# 5. Bilgi Ambarı Sorgulama (FTS5 Knowledge Search)
tool_registry.register(
    ToolDefinition(
        name="knowledge_search",
        description="Sistemin kalıcı hafızasındaki doğrulanmış bilgi kayıtlarını ve mantık zincirlerini arar.",
        input_schema={"query": "str", "lesson": "str"},
        timeout_seconds=5.0,
        rate_limit_per_min=200
    ),
    lambda query, lesson="": knowledge_store.search_knowledge(query, lesson=lesson, limit=10)
)

# 6. Anti-Halüsinasyon Doğrulama Aracı
tool_registry.register(
    ToolDefinition(
        name="fact_verify",
        description="Üretilen bir iddiayı RefChecker, SelfCheckGPT ve Z3 SMT formal çözücü ile 4 katmandan geçirir.",
        input_schema={"topic_id": "str", "text": "str"},
        timeout_seconds=20.0,
        rate_limit_per_min=100
    ),
    lambda topic_id, text: fact_checker.validate(topic_id, text)
)
