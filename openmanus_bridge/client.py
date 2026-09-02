"""
OpenManus Bridge: İstemci ve Sınır Koruyucu (Client & Boundary Guard)
OpenManus saha işçisini çalıştırır ve salt araştırma sonucu (ResearchResult) döner.
KURAL: OpenManus bu köprü üzerinden asla doğrudan veritabanına kanonik bilgi yazamaz
veya güven skorunu manipüle edemez.
"""
from typing import Dict, Any, Optional
import asyncio
from curriculum.models import ResearchTask
from openmanus_bridge.schemas import ResearchResult
from openmanus_bridge.task_builder import OpenManusTaskBuilder
from openmanus_bridge.result_parser import OpenManusResultParser


class OpenManusBridgeClient:
    """
    OpenManus Araştırma Köprüsü:
    Saha işçisini çağırır, sonuçları şemalandırır ve Supervisor/Auditor katmanına teslim eder.
    """

    async def execute_research(self, task: ResearchTask) -> ResearchResult:
        """Araştırma görevini yürütür ve doğrulanmış ResearchResult döner."""
        payload = OpenManusTaskBuilder.build_research_payload(task)
        query = payload["primary_query"]

        # 1. YouTube ve Web Arama Simülasyonu / Entegrasyonu
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
                search_target = f"ytsearch{min(payload.get('max_videos', 4), 5)}:{query}"
                res = ydl.extract_info(search_target, download=False)
                entries = res.get("entries", []) if res else []
                for entry in entries:
                    if entry and entry.get("id") and len(entry.get("id")) == 11:
                        videos.append({
                            "video_id": entry["id"],
                            "url": f"https://www.youtube.com/watch?v={entry['id']}",
                            "title": entry.get("title", ""),
                            "channel": entry.get("channel") or entry.get("uploader", "YouTube"),
                            "teacher_name": payload.get("target_teachers", ["Genel"])[0] if payload.get("target_teachers") else "Genel",
                            "duration_seconds": int(entry.get("duration", 0) or 0)
                        })
        except Exception:
            pass

        raw_result = {
            "summary": f"'{query}' için arama tamamlandı. {len(videos)} video bulundu.",
            "videos": videos,
            "raw_evidence": []
        }

        return OpenManusResultParser.parse_raw_output(
            task_id=task.task_id,
            query=query,
            raw_output=raw_result
        )

    def commit_knowledge_forbidden(self) -> None:
        """KURAL İHLALİ KORUMASI: OpenManus doğrudan bilgi ambarına yazamaz."""
        raise PermissionError("OpenManus köprüsü doğrudan kanonik bilgi yazma veya güven skoru değiştirme yetkisine sahip değildir!")


openmanus_bridge_client = OpenManusBridgeClient()
