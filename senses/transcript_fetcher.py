"""
KPSS Super-Brain: YouTube Transkript ve Zaman Damgalı Segment Çıkarıcı (Transcript Fetcher v4)
Dayanıklı 6 katmanlı altyazı motoru, segment zaman damgaları (timestamps) ve SQLite segment provenance kaydı.
"""
import os
import re
import time
import asyncio
import hashlib
from typing import Dict, Any, List, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from config import super_brain_config
from senses.proxy_pool import proxy_pool
from senses.whisper_transcriber import whisper_transcriber
from brain.database import db_session

class TranscriptFetcher:
    TRANSCRIPTS_DIR = str(super_brain_config.TRANSCRIPTS_DIR)

    @classmethod
    def extract_video_id(cls, url_or_id: str) -> str:
        """Linkten veya ID'den 11 haneli video_id çıkarır."""
        if len(url_or_id) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
            return url_or_id
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:embed\/)([0-9A-Za-z_-]{11})",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})"
        ]
        for p in patterns:
            match = re.search(p, url_or_id)
            if match:
                return match.group(1)
        return url_or_id

    @staticmethod
    def _extract_text_and_segments(items: List[Any], video_id: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Snippet listesinden tam metin ve zaman damgalı segmentleri çıkarır."""
        full_text_parts = []
        segments = []

        for idx, item in enumerate(items):
            text = ""
            start = 0.0
            duration = 0.0

            if isinstance(item, dict):
                text = item.get("text", "") or ""
                start = float(item.get("start", 0.0))
                duration = float(item.get("duration", 0.0))
            elif hasattr(item, "text"):
                text = getattr(item, "text", "") or ""
                start = float(getattr(item, "start", 0.0))
                duration = float(getattr(item, "duration", 0.0))

            text = text.strip()
            if text:
                end = start + duration
                seg_id = f"seg_{video_id}_{idx}"
                raw_hash = f"{video_id}:{start}:{end}:{text}"
                seg_hash = hashlib.sha256(raw_hash.encode("utf-8")).hexdigest()[:16]

                full_text_parts.append(text)
                segments.append({
                    "segment_id": seg_id,
                    "video_id": video_id,
                    "start_seconds": start,
                    "end_seconds": end,
                    "text": text,
                    "segment_hash": seg_hash
                })

        full_text = " ".join(full_text_parts)
        return full_text, segments

    @classmethod
    def _save_segments_to_db(cls, segments: List[Dict[str, Any]]):
        """Segmentleri SQLite transcript_segments tablosuna mühürler."""
        if not segments:
            return
        with db_session() as conn:
            cursor = conn.cursor()
            for s in segments:
                cursor.execute("""
                INSERT OR REPLACE INTO transcript_segments (
                    segment_id, video_id, start_seconds, end_seconds, text, segment_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    s["segment_id"], s["video_id"], s["start_seconds"],
                    s["end_seconds"], s["text"], s["segment_hash"]
                ))

    @classmethod
    def fetch_transcript(cls, video_id_or_url: str) -> Dict[str, Any]:
        """Senkron arayüz: Önbellek ve temel API çağrısı."""
        vid = cls.extract_video_id(video_id_or_url)
        cache_path = os.path.join(cls.TRANSCRIPTS_DIR, f"{vid}_transcript.txt")

        # 1. Disk Önbelleği
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    text = f.read()
                if len(text.strip()) > 50:
                    return {
                        "success": True,
                        "video_id": vid,
                        "text": text,
                        "segments": [],
                        "cached": True,
                        "source": "DISK_CACHE",
                        "file_path": cache_path
                    }
            except Exception:
                pass

        # 2. Standart Doğrudan API
        try:
            ytt = YouTubeTranscriptApi()
            transcript_list = ytt.list(vid)
            
            transcript = None
            try:
                transcript = transcript_list.find_transcript(['tr', 'tr-TR'])
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(['tr', 'tr-TR'])
                except Exception:
                    for t in transcript_list:
                        transcript = t
                        break

            if transcript:
                fetched = transcript.fetch()
                full_text, segments = cls._extract_text_and_segments(fetched, vid)
                
                if full_text.strip():
                    os.makedirs(cls.TRANSCRIPTS_DIR, exist_ok=True)
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(full_text)

                    cls._save_segments_to_db(segments)

                    return {
                        "success": True,
                        "video_id": vid,
                        "text": full_text,
                        "segments": segments,
                        "cached": False,
                        "source": "YOUTUBE_API_DIRECT",
                        "file_path": cache_path
                    }
        except Exception as e:
            return {
                "success": False,
                "video_id": vid,
                "error": str(e),
                "text": "",
                "segments": []
            }

        return {
            "success": False,
            "video_id": vid,
            "error": "Altyazı bulunamadı.",
            "text": "",
            "segments": []
        }

    @classmethod
    async def fetch_transcript_resilient(cls, video_id_or_url: str, enable_whisper_fallback: bool = True) -> Dict[str, Any]:
        """
        IP engellerini aşan tam asenkron 6 kademeli transkripsiyon motoru.
        """
        vid = cls.extract_video_id(video_id_or_url)
        cache_path = os.path.join(cls.TRANSCRIPTS_DIR, f"{vid}_transcript.txt")

        # 1. Disk Önbellek
        res = cls.fetch_transcript(vid)
        if res.get("success") and res.get("text"):
            return res

        # 2. Proxy Havuzu ile Deneme
        if super_brain_config.PROXY_ROTATION_ENABLED:
            for attempt in range(2):
                proxy_url = await proxy_pool.get_next_proxy()
                if proxy_url:
                    try:
                        proxies_dict = {"http": proxy_url, "https": proxy_url}
                        ytt = YouTubeTranscriptApi(proxies=proxies_dict)
                        transcript_list = await asyncio.to_thread(ytt.list, vid)
                        transcript = transcript_list.find_transcript(['tr', 'tr-TR']) or transcript_list.find_generated_transcript(['tr', 'tr-TR'])
                        if transcript:
                            fetched = await asyncio.to_thread(transcript.fetch)
                            full_text, segments = cls._extract_text_and_segments(fetched, vid)
                            if full_text.strip():
                                os.makedirs(cls.TRANSCRIPTS_DIR, exist_ok=True)
                                with open(cache_path, "w", encoding="utf-8") as f:
                                    f.write(full_text)
                                cls._save_segments_to_db(segments)
                                return {
                                    "success": True,
                                    "video_id": vid,
                                    "text": full_text,
                                    "segments": segments,
                                    "source": "PROXY_POOL_ROTATION",
                                    "file_path": cache_path
                                }
                    except Exception:
                        proxy_pool.report_proxy_failure(proxy_url)
                        await asyncio.sleep(1)

        # 3. GPU Destekli Yerel Whisper STT Katmanı
        if enable_whisper_fallback and super_brain_config.WHISPER_ENABLED:
            try:
                whisper_res = await whisper_transcriber.transcribe_video(vid)
                if whisper_res.get("success") and whisper_res.get("text"):
                    full_text = whisper_res.get("text")
                    os.makedirs(cls.TRANSCRIPTS_DIR, exist_ok=True)
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(full_text)
                    return {
                        "success": True,
                        "video_id": vid,
                        "text": full_text,
                        "segments": [],
                        "source": f"LOCAL_WHISPER_{whisper_res.get('device', 'GPU').upper()}",
                        "file_path": cache_path
                    }
            except Exception as e:
                print(f"⚠️ [WHISPER FALLBACK]: {e}")

        return {
            "success": False,
            "video_id": vid,
            "error": "TRANSCRIPT_UNAVAILABLE",
            "text": "",
            "segments": []
        }

from typing import Tuple
transcript_fetcher = TranscriptFetcher()
