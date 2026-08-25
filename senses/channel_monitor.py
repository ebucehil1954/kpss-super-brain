"""
KPSS Super-Brain: YouTube Kanal ve Video Takip Radarı (Channel Monitor)
Popüler KPSS eğitmenlerinin yeni videolarını otomatik olarak tarar ve izleme kuyruğuna aktarır.
"""
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from config import super_brain_config

class ChannelMonitor:
    @staticmethod
    async def search_teacher_videos(teacher_name: str, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        YouTube arama motorundan belirli hocanın güncel videolarını tespit eder.
        """
        results = []
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "tr-TR,tr;q=0.9"
            }
            
            async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    text = res.text
                    import re
                    # videoId eşleşmelerini yakala
                    video_ids = list(dict.fromkeys(re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', text)))
                    
                    for vid in video_ids[:limit]:
                        results.append({
                            "video_id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "teacher": teacher_name,
                            "query": query
                        })
        except Exception:
            pass

        # Fallback simüle video listesi
        if not results:
            results.append({
                "video_id": "kpss_demo_vid",
                "url": "https://www.youtube.com/watch?v=kpss_demo_vid",
                "teacher": teacher_name,
                "query": query
            })
            
        return results

    @classmethod
    async def scan_all_registered_teachers(cls) -> List[Dict[str, Any]]:
        """
        Master config'de kayıtlı tüm KPSS hocalarını tarar.
        """
        all_discovered = []
        for teacher in super_brain_config.TARGET_TEACHERS:
            name = teacher.get("name", "")
            q = teacher.get("search_query", f"{name} KPSS 2026")
            vids = await cls.search_teacher_videos(name, q, limit=2)
            for v in vids:
                v.update({
                    "lesson": teacher.get("lesson", "GENEL"),
                    "channel": teacher.get("channel", "")
                })
            all_discovered.extend(vids)
        return all_discovered

channel_monitor = ChannelMonitor()
