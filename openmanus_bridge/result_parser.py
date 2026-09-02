"""
OpenManus Bridge: Sonuç Ayrıştırıcı (Result Parser)
OpenManus ham araç/ajan yanıtlarını doğrulanmış ResearchResult nesnesine dönüştürür.
"""
from typing import Dict, Any, List
import json
from openmanus_bridge.schemas import ResearchResult, DiscoveredVideo, DiscoveredEvidence


class OpenManusResultParser:
    @staticmethod
    def parse_raw_output(task_id: str, query: str, raw_output: Any) -> ResearchResult:
        """Ham arama veya ajan çıktısını şema doğrulamalı ResearchResult'a dönüştürür."""
        if isinstance(raw_output, str):
            try:
                raw_data = json.loads(raw_output)
            except Exception:
                raw_data = {"summary": raw_output, "videos": []}
        elif isinstance(raw_output, dict):
            raw_data = raw_output
        else:
            raw_data = {}

        raw_videos = raw_data.get("videos", [])
        valid_videos = []
        for v in raw_videos:
            try:
                if isinstance(v, dict) and v.get("video_id"):
                    valid_videos.append(DiscoveredVideo(
                        video_id=v["video_id"],
                        url=v.get("url", f"https://www.youtube.com/watch?v={v['video_id']}"),
                        title=v.get("title", "KPSS Dersi"),
                        channel=v.get("channel", "YouTube"),
                        teacher_name=v.get("teacher_name", "Genel"),
                        duration_seconds=int(v.get("duration_seconds", 0) or 0)
                    ))
            except Exception:
                continue

        raw_ev = raw_data.get("raw_evidence", [])
        valid_ev = []
        for e in raw_ev:
            if isinstance(e, dict) and e.get("snippet"):
                valid_ev.append(DiscoveredEvidence(
                    source_url=e.get("source_url", "https://youtube.com"),
                    title=e.get("title", ""),
                    snippet=e["snippet"]
                ))

        status = "SUCCESS" if valid_videos or valid_ev else "DISCOVERY_FAILED"

        return ResearchResult(
            task_id=task_id,
            status=status,
            query=query,
            videos=valid_videos,
            raw_evidence=valid_ev,
            search_summary=raw_data.get("summary", ""),
            total_found=len(valid_videos)
        )
