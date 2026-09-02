"""
KPSS Super-Brain: Resmi YouTube Data API v3 İstemcisi (YouTubeApiClient)
Google Cloud resmi API anahtarı ile video arama, oynatma listesi ve metaveri çekme işlemlerini
sıfır IP engeli ile yüksek hızda gerçekleştirir.
API Anahtarı kod içine ASLA yazılmaz; yalnızca .env / ortam değişkenlerinden okunur.
"""
from __future__ import annotations

import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx

from config import super_brain_config

logger = logging.getLogger("youtube_api_client")


def _parse_iso8601_duration(duration_str: str) -> int:
    """ISO 8601 formatındaki YouTube süresini (PT1H23M45S) saniyeye çevirir."""
    if not duration_str:
        return 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


class YouTubeApiClient:
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    _quota_exhausted_until: float = 0.0
    _search_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
    CACHE_TTL_SECONDS: float = 86400.0  # 24 saat önbellek

    @classmethod
    def is_available(cls) -> bool:
        """API anahtarının tanımlı ve kotanın kullanılabilir olup olmadığını döner."""
        if not super_brain_config.YOUTUBE_API_KEY or not super_brain_config.YOUTUBE_API_KEY.strip():
            return False
        # Eğer kota yakın zamanda tükendiyse bekleme süresine bak
        if time.time() < cls._quota_exhausted_until:
            return False
        return True

    @classmethod
    def mark_quota_exhausted(cls, cooldown_seconds: float = 1800.0):
        """API kotası tükendiğinde (HTTP 429 / quotaExceeded) cooldown başlatır."""
        cls._quota_exhausted_until = time.time() + cooldown_seconds
        logger.warning(
            f"⚠️ [YOUTUBE API KOTA KORUMASI] Arama kotası tükendi. "
            f"{cooldown_seconds / 60:.0f} dakika boyunca alternatif sağlayıcılara (yt-dlp/Playlist) geçiliyor."
        )

    @classmethod
    def _get_masked_key(cls) -> str:
        k = super_brain_config.YOUTUBE_API_KEY
        if len(k) > 8:
            return f"{k[:4]}...{k[-4:]}"
        return "***"

    @classmethod
    def search_videos(
        cls,
        query: str,
        max_results: int = 5,
        channel_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Resmi YouTube Data API v3 ile video araması yapar (Önbellek destekli).
        Arama başına 100 birim kota harcandığı için sonuçlar 24 saat önbelleklenir.
        """
        cache_key = f"{query}_{channel_id}_{max_results}"
        now = time.time()
        if cache_key in cls._search_cache:
            ts, cached_results = cls._search_cache[cache_key]
            if now - ts < cls.CACHE_TTL_SECONDS:
                return cached_results

        if not cls.is_available():
            return []

        try:
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": min(max_results, 25),
                "key": super_brain_config.YOUTUBE_API_KEY
            }
            if channel_id:
                params["channelId"] = channel_id

            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{cls.BASE_URL}/search", params=params)
                if res.status_code == 429 or "quotaExceeded" in res.text:
                    cls.mark_quota_exhausted(cooldown_seconds=1800.0)
                    return []
                elif res.status_code != 200:
                    logger.warning(f"YouTube Data API arama yanıtı ({res.status_code}): {res.text[:120]}")
                    return []

                data = res.json()
                items = data.get("items", [])
                video_ids = [it.get("id", {}).get("videoId") for it in items if it.get("id", {}).get("videoId")]

                # Süre ve detayları çek
                details_map = cls.get_videos_details(video_ids) if video_ids else {}

                results = []
                for it in items:
                    vid = it.get("id", {}).get("videoId")
                    if not vid:
                        continue
                    snippet = it.get("snippet", {})
                    details = details_map.get(vid, {})

                    results.append({
                        "video_id": vid,
                        "url": f"https://www.youtube.com/watch?v={vid}",
                        "title": snippet.get("title", ""),
                        "channel": snippet.get("channelTitle", "YouTube"),
                        "channel_id": snippet.get("channelId", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "duration_seconds": details.get("duration_seconds", 0),
                        "description": snippet.get("description", "")
                    })

                cls._search_cache[cache_key] = (now, results)
                return results

        except Exception as e:
            logger.warning(f"YouTube Data API arama hatası: {e}")
            return []

    @classmethod
    def get_videos_details(cls, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Video ID listesi için süre (contentDetails) ve istatistikleri çeker."""
        if not super_brain_config.YOUTUBE_API_KEY or not video_ids:
            return {}

        try:
            params = {
                "part": "contentDetails,snippet",
                "id": ",".join(video_ids[:50]),
                "key": super_brain_config.YOUTUBE_API_KEY
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{cls.BASE_URL}/videos", params=params)
                if res.status_code != 200:
                    return {}

                data = res.json()
                result_map = {}
                for it in data.get("items", []):
                    vid = it.get("id")
                    cd = it.get("contentDetails", {})
                    duration_str = cd.get("duration", "")
                    duration_sec = _parse_iso8601_duration(duration_str)

                    result_map[vid] = {
                        "duration_seconds": duration_sec,
                        "duration_iso": duration_str
                    }
                return result_map

        except Exception:
            return {}

    @classmethod
    def get_playlist_items(
        cls,
        playlist_id: str,
        max_results: int = 50,
        page_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Bir oynatma listesindeki videoları çeker (1 birim kota harcar).
        Maksimum 50 videoya kadar tek çağrıda alır.
        """
        if not super_brain_config.YOUTUBE_API_KEY:
            return []

        try:
            params = {
                "part": "snippet",
                "playlistId": playlist_id,
                "maxResults": min(max_results, 50),
                "key": super_brain_config.YOUTUBE_API_KEY
            }
            if page_token:
                params["pageToken"] = page_token

            with httpx.Client(timeout=15.0) as client:
                res = client.get(f"{cls.BASE_URL}/playlistItems", params=params)
                if res.status_code == 429 or "quotaExceeded" in res.text:
                    cls.mark_quota_exhausted(cooldown_seconds=1800.0)
                    return []
                elif res.status_code != 200:
                    return []

                data = res.json()
                items = []
                for it in data.get("items", []):
                    snippet = it.get("snippet", {})
                    vid = snippet.get("resourceId", {}).get("videoId")
                    if vid and len(vid) == 11:
                        items.append({
                            "video_id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "title": snippet.get("title", ""),
                            "channel": snippet.get("channelTitle", "YouTube"),
                            "published_at": snippet.get("publishedAt", "")
                        })
                return items

        except Exception as e:
            logger.warning(f"YouTube Playlist çekim hatası: {e}")
            return []


youtube_api_client = YouTubeApiClient()
