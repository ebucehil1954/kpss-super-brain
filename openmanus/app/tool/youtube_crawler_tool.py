"""
OpenManus Tool: YouTube Video ve Kanal Keşif Aracı (YouTubeCrawlerTool)
YouTube üzerinde KPSS ders videolarını, oynatma listelerini ve hoca anlatımlarını arar.
Video ID, başlık, kanal adı, süre ve URL bilgilerini yapılandırılmış JSON olarak döndürür.
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class YouTubeCrawlerTool(BaseTool):
    """
    YouTube üzerinde ders videoları arayan ve video metaverilerini toplayan araç.
    """
    name: str = "youtube_crawler"
    description: str = (
        "YouTube üzerinde KPSS ders videoları, oynatma listeleri ve hoca anlatımlarını arar. "
        "Belirtilen arama sorgusuna en uygun video ID'si, başlığı, kanalı, süresi ve URL'sini "
        "yapılandırılmış bir liste olarak döndürür."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(Gerekli) YouTube'da aranacak terim. Örn: 'KPSS Lisans Coğrafya Bayram Meral yer şekilleri'"
            },
            "teacher_name": {
                "type": "string",
                "description": "(İsteğe bağlı) Hedef eğitmen adı. Örn: 'Bayram Meral'"
            },
            "lesson": {
                "type": "string",
                "description": "(İsteğe bağlı) KPSS dersi. Örn: 'COGRAFYA', 'TARIH', 'VATANDASLIK'"
            },
            "max_results": {
                "type": "integer",
                "description": "(İsteğe bağlı) Döndürülecek maksimum video sayısı. Varsayılan: 5",
                "default": 5
            }
        },
        "required": ["query"]
    }

    async def execute(
        self,
        query: str,
        teacher_name: Optional[str] = None,
        lesson: Optional[str] = None,
        max_results: int = 5
    ) -> ToolResult:
        """YouTube aramasını gerçekleştirir ve sonuçları döner."""
        if not query or not query.strip():
            return ToolResult(error="Arama sorgusu (query) boş olamaz.")

        clean_query = query.strip()
        limit = max(1, min(max_results or 5, 20))
        logger.info(f"🔍 [YOUTUBE CRAWLER] Aranıyor: '{clean_query}' (Limit: {limit})")

        videos = []
        try:
            import yt_dlp
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_target = f"ytsearch{limit}:{clean_query}"
                res = ydl.extract_info(search_target, download=False)
                entries = res.get("entries", []) if res else []

                for entry in entries:
                    if not entry:
                        continue
                    vid = entry.get("id")
                    title = entry.get("title", "")
                    if not vid or len(vid) != 11:
                        continue

                    duration = entry.get("duration", 0) or 0
                    channel = entry.get("channel") or entry.get("uploader", "YouTube")

                    videos.append({
                        "video_id": vid,
                        "url": f"https://www.youtube.com/watch?v={vid}",
                        "title": title,
                        "channel": channel,
                        "teacher_name": teacher_name or "Genel",
                        "lesson": lesson or "GENEL",
                        "duration_seconds": int(duration)
                    })

        except Exception as e:
            logger.warning(f"⚠️ [YOUTUBE CRAWLER] yt_dlp arama hatası: {e}")
            return ToolResult(
                error=f"YouTube araması sırasında hata oluştu: {str(e)}"
            )

        output_data = {
            "query": clean_query,
            "total_found": len(videos),
            "videos": videos
        }
        return ToolResult(output=json.dumps(output_data, ensure_ascii=False, indent=2))
