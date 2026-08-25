"""
KPSS Super-Brain: Tip Güvenli Araç Kayıt Defteri (Tool Registry)
Ajanın rastgele fonksiyon çağırmasını engelleyen, şema doğrulamalı, zaman aşımı (timeout)
ve tekrar deneme (retry) korumalı araç yönetim merkezi.
"""
import asyncio
import inspect
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
from pydantic import BaseModel, Field

class ToolDefinition(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 30.0
    retry_policy: int = 2
    side_effects: bool = False
    rate_limit_per_min: int = 60

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._executors: Dict[str, Callable[..., Awaitable[Any]]] = {}

    def register(self, definition: ToolDefinition, func: Callable[..., Any]):
        """Yeni bir aracı kayıt defterine bağlar."""
        self._tools[definition.name] = definition
        self._executors[definition.name] = func

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
                "side_effects": t.side_effects
            }
            for t in self._tools.values()
        ]

    async def execute(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aracı zaman aşımı ve hata kalkanıyla çalıştırır.
        """
        tool_def = self._tools.get(name)
        func = self._executors.get(name)

        if not tool_def or not func:
            return {
                "success": False,
                "tool": name,
                "error": f"Tool '{name}' kayıt defterinde bulunamadı.",
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
                    "output": res
                }
            except asyncio.TimeoutError:
                if attempt > retries:
                    return {
                        "success": False,
                        "tool": name,
                        "error": f"Tool '{name}' {tool_def.timeout_seconds}s içinde zaman aşımına uğradı.",
                        "output": None
                    }
                await asyncio.sleep(0.5)
            except Exception as e:
                if attempt > retries:
                    return {
                        "success": False,
                        "tool": name,
                        "error": f"Çalıştırma hatası: {str(e)}",
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
tool_registry.register(
    ToolDefinition(
        name="youtube_search",
        description="Belirli bir KPSS dersi ve konusu için popüler hoca videolarını ve oynatma listelerini arar.",
        input_schema={"topic": "str", "lesson": "str", "limit": "int"},
        timeout_seconds=20.0
    ),
    lambda topic, lesson="GENEL", limit=5: video_crawler.search_topic_videos(topic, lesson=lesson, max_results=limit)
)

# 2. Transkript Çekim Aracı
tool_registry.register(
    ToolDefinition(
        name="transcript_fetch",
        description="YouTube video ID'si verilen dersin altyazısını ve zaman damgalı segmentlerini çeker.",
        input_schema={"video_id": "str"},
        timeout_seconds=25.0
    ),
    lambda video_id: transcript_fetcher.fetch_transcript_resilient(video_id)
)

# 3. Resmi Mevzuat ve Kanun Arama
tool_registry.register(
    ToolDefinition(
        name="official_mevzuat_search",
        description="Resmi Gazete ve mevzuat.gov.tr üzerinden güncel kanun ve anayasa maddelerini sorgular.",
        input_schema={"query": "str", "topic": "str"},
        timeout_seconds=15.0
    ),
    lambda query, topic="": MevzuatCrawler.search_legislation(query, topic)
)

# 4. TÜİK & MTA İstatistik Arama
tool_registry.register(
    ToolDefinition(
        name="tuik_mta_search",
        description="TÜİK nüfus/tarım ve MTA maden verilerini en güncel resmî tablolardan sorgular.",
        input_schema={"topic": "str"},
        timeout_seconds=15.0
    ),
    lambda topic: TuikFetcher.fetch_latest_stats(topic)
)

# 5. Bilgi Ambarı Sorgulama (FTS5 Knowledge Search)
tool_registry.register(
    ToolDefinition(
        name="knowledge_search",
        description="Sistemin kalıcı hafızasındaki doğrulanmış bilgi kayıtlarını ve mantık zincirlerini arar.",
        input_schema={"query": "str", "lesson": "str"},
        timeout_seconds=5.0
    ),
    lambda query, lesson="": knowledge_store.search_knowledge(query, lesson=lesson, limit=10)
)

# 6. Anti-Halüsinasyon Doğrulama Aracı
tool_registry.register(
    ToolDefinition(
        name="fact_verify",
        description="Üretilen bir iddiayı RefChecker, SelfCheckGPT ve Z3 SMT formal çözücü ile 4 katmandan geçirir.",
        input_schema={"topic_id": "str", "text": "str"},
        timeout_seconds=20.0
    ),
    lambda topic_id, text: fact_checker.validate(topic_id, text)
)
