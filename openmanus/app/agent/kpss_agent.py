"""
OpenManus Agent: KPSS Otonom Uzman Ajanı (KPSSAgent)
KPSS kaynaklarını (YouTube videoları, resmi mevzuat metinleri, kanonik doğrular) tarar,
çelişkileri çözer, Z3 ve MiniLM ile doğrular ve kanıta dayalı (provenance içeren) yanıtlar üretir.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import Field

from app.agent.manus import Manus
from app.logger import logger
from app.tool import Terminate, ToolCollection
from app.tool.web_search import WebSearch
from app.tool.python_execute import PythonExecute
from app.tool.file_saver import FileSaver
from app.tool.youtube_transcript_tool import YouTubeTranscriptTool
from app.tool.youtube_crawler_tool import YouTubeCrawlerTool
from app.tool.contradiction_checker_tool import ContradictionCheckerTool
from app.tool.ground_truth_tool import GroundTruthTool


class KPSSAgent(Manus):
    """
    KPSS ve resmi mevzuat alanında uzmanlaşmış otonom araştırma ve karar ajanı.
    """
    name: str = "KPSSAgent"
    description: str = (
        "KPSS, vatandaşlık ve anayasa konularında uzman otonom ajan. "
        "YouTube videolarını arar, transkriptlerini inceler, resmi mevzuatı araştırır, "
        "ifadeler arasındaki çelişkileri tespit eder ve kanıta dayalı yanıtlar verir."
    )

    # Kullanıcının şart koştuğu özel sistem talimatı
    system_prompt: str = (
        "Sen bir KPSS Uzmanısın. Verilen kaynakları (YouTube, Mevzuat) tarar, "
        "çelişkileri çözer ve kanıta dayalı cevap verirsin. "
        "Her cevabının sonunda kaynağını (provenance) belirt."
    )

    # Varsayılan araçları koru ve KPSS özel araçlarını ekle
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            WebSearch(),
            FileSaver(),
            PythonExecute(),
            YouTubeCrawlerTool(),
            YouTubeTranscriptTool(),
            ContradictionCheckerTool(),
            GroundTruthTool(),
            Terminate(),
        )
    )

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    def __init__(self, **data):
        """
        KPSSAgent örneğini başlatır ve araç koleksiyonunu yapılandırır.
        """
        super().__init__(**data)
        # __init__ içinde araç koleksiyonunu eksiksiz olarak garantiye alıyoruz
        self.available_tools = ToolCollection(
            WebSearch(),
            FileSaver(),
            PythonExecute(),
            YouTubeTranscriptTool(),
            ContradictionCheckerTool(),
            GroundTruthTool(),
            Terminate(),
        )
        self.special_tool_names = [Terminate().name]
        logger.info(
            f"🎓 [KPSSAgent] Başlatıldı. Yüklenen araçlar: "
            f"{[t.name for t in self.available_tools.tools]}"
        )

    @classmethod
    async def create(cls, **kwargs) -> "KPSSAgent":
        """
        KPSSAgent nesnesini asenkron olarak oluşturur ve hazırlar.
        """
        logger.info("🎓 [KPSSAgent] Asenkron başlatma süreci başladı...")
        try:
            instance = cls(**kwargs)
            await instance.initialize_mcp_servers()
            instance._initialized = True
            logger.info("🎓 [KPSSAgent] Başarıyla hazırlandı.")
            return instance
        except Exception as e:
            logger.error(f"KPSSAgent başlatma hatası: {e}")
            raise e
