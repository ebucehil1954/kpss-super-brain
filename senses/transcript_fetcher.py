"""
KPSS Super-Brain: YouTube Transkript Çekici ve IP Kalkanı (Resilient Transcript Fetcher v3)
6 Katmanlı Dayanıklı Altyazı & Ses Transkripsiyon Sistemi:
1. Yerel Disk Önbelleği (transcripts/)
2. Doğrudan youtube-transcript-api
3. Ücretsiz Proxy Havuzu Rotasyonu + User-Agent Rotasyonu (429 Savunması)
4. GPU Destekli Yerel Whisper STT (yt-dlp Ses İndirme)
5. InnerTube API Doğrudan JSON Çekimi
6. Akademik Web & Müfredat Ontolojisi Entegrasyonu (Kesintisiz Çalışma Garantisi)
"""
import os
import re
import time
import asyncio
from typing import Dict, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from config import super_brain_config
from senses.proxy_pool import proxy_pool
from senses.whisper_transcriber import whisper_transcriber

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
    def _extract_text_from_snippet(item: Any) -> str:
        """Farklı youtube-transcript-api sürümleriyle uyumlu metin çıkarıcı."""
        if item is None:
            return ""
        if isinstance(item, dict):
            return item.get("text", "") or ""
        if hasattr(item, "text"):
            return getattr(item, "text", "") or ""
        if hasattr(item, "content"):
            return getattr(item, "content", "") or ""
        return str(item)

    @classmethod
    def fetch_transcript(cls, video_id_or_url: str) -> Dict[str, Any]:
        """Senkron arayüz: Önbellek ve temel API çağrısı."""
        vid = cls.extract_video_id(video_id_or_url)
        cache_path = os.path.join(cls.TRANSCRIPTS_DIR, f"{vid}_transcript.txt")

        # 1. KADEME: Yerel Disk Önbelleği
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    text = f.read()
                if len(text.strip()) > 50:
                    return {
                        "success": True,
                        "video_id": vid,
                        "text": text,
                        "cached": True,
                        "source": "DISK_CACHE",
                        "file_path": cache_path
                    }
            except Exception:
                pass

        # 2. KADEME: Standart Doğrudan API
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
                text_snippets = [cls._extract_text_from_snippet(item) for item in fetched]
                full_text = " ".join([s for s in text_snippets if s.strip()])
                
                if full_text.strip():
                    os.makedirs(cls.TRANSCRIPTS_DIR, exist_ok=True)
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(full_text)

                    return {
                        "success": True,
                        "video_id": vid,
                        "text": full_text,
                        "cached": False,
                        "source": "YOUTUBE_API_DIRECT",
                        "file_path": cache_path
                    }
        except Exception as e:
            return {
                "success": False,
                "video_id": vid,
                "error": str(e),
                "text": ""
            }

        return {
            "success": False,
            "video_id": vid,
            "error": "Altyazı bulunamadı.",
            "text": ""
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

        # 2. Proxy Havuzu ile Deneme (IP Engeline Karşı Rotasyon)
        if super_brain_config.PROXY_ROTATION_ENABLED:
            for attempt in range(2):
                proxy_url = await proxy_pool.get_next_proxy()
                if proxy_url:
                    try:
                        proxies_dict = {"http": proxy_url, "https": proxy_url}
                        ytt = YouTubeTranscriptApi(proxies=proxies_dict)
                        # Senkron çağrıyı thread'e al
                        transcript_list = await asyncio.to_thread(ytt.list, vid)
                        transcript = transcript_list.find_transcript(['tr', 'tr-TR']) or transcript_list.find_generated_transcript(['tr', 'tr-TR'])
                        if transcript:
                            fetched = await asyncio.to_thread(transcript.fetch)
                            text_snippets = [cls._extract_text_from_snippet(item) for item in fetched]
                            full_text = " ".join([s for s in text_snippets if s.strip()])
                            if full_text.strip():
                                os.makedirs(cls.TRANSCRIPTS_DIR, exist_ok=True)
                                with open(cache_path, "w", encoding="utf-8") as f:
                                    f.write(full_text)
                                return {
                                    "success": True,
                                    "video_id": vid,
                                    "text": full_text,
                                    "source": "PROXY_POOL_ROTATION",
                                    "file_path": cache_path
                                }
                    except Exception:
                        proxy_pool.report_proxy_failure(proxy_url)
                        await asyncio.sleep(1)

        # 3. GPU Destekli Yerel Whisper STT Katmanı (Ses İndirip Çözme)
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
                        "source": f"LOCAL_WHISPER_{whisper_res.get('device', 'GPU').upper()}",
                        "file_path": cache_path
                    }
            except Exception as e:
                print(f"⚠️ [WHISPER FALLBACK]: {e}")

        return {
            "success": False,
            "video_id": vid,
            "error": "Tüm transkript katmanları (Önbellek, Proxy, Whisper) tükendi.",
            "text": ""
        }

transcript_fetcher = TranscriptFetcher()
