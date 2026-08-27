"""
OpenManus Tool: YouTube Video Transkript ve Fallback Metin Çıkarıcı
YouTube video URL'sinden Türkçe veya otomatik altyazıyı çeker.
Altyazı bulunamazsa pytube veya HTTPX/BeautifulSoup ile başlık ve açıklamayı fallback olarak döndürür.
"""
from __future__ import annotations

import re
import json
from typing import Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class YouTubeTranscriptTool(BaseTool):
    """
    YouTube video bağlantılarından altyazı veya açıklama metnini çıkaran araç.
    """
    name: str = "youtube_transcript"
    description: str = (
        "YouTube video URL'sinden Türkçe veya İngilizce transkript metnini çeker. "
        "Eğer videoda altyazı yoksa, videonun başlık ve açıklama metnini alternatif kaynak olarak döndürür."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "video_url": {
                "type": "string",
                "description": "(Gerekli) Transkripti çekilecek YouTube video URL'si veya 11 haneli video ID'si."
            }
        },
        "required": ["video_url"]
    }

    @staticmethod
    def extract_video_id(url_or_id: str) -> str:
        """YouTube URL veya kimliğinden 11 haneli video_id'yi ayıklar."""
        clean_input = url_or_id.strip()
        if len(clean_input) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", clean_input):
            return clean_input

        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?]|$)",
            r"(?:embed\/)([0-9A-Za-z_-]{11})",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
            r"(?:shorts\/)([0-9A-Za-z_-]{11})"
        ]
        for pattern in patterns:
            match = re.search(pattern, clean_input)
            if match:
                return match.group(1)
        return clean_input

    async def _fetch_metadata_pytube(self, video_url: str) -> Optional[Dict[str, str]]:
        """Pytube kullanarak video başlığı ve açıklamasını çeker."""
        try:
            from pytube import YouTube
            yt = YouTube(video_url)
            title = yt.title or ""
            desc = yt.description or ""
            if title or desc:
                return {"title": title, "description": desc}
        except Exception as e:
            logger.error(f"Pytube ile metadata çekilemedi: {e}")
        return None

    async def _fetch_metadata_httpx(self, video_id: str) -> Dict[str, str]:
        """HTTPX ve BeautifulSoup ile video başlığı ve açıklamasını çeker."""
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
                resp = await client.get(watch_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = soup.title.string.replace(" - YouTube", "").strip() if soup.title else f"Video {video_id}"
                    
                    desc_meta = soup.find("meta", {"name": "description"})
                    description = desc_meta.get("content", "").strip() if desc_meta else ""
                    
                    return {
                        "title": title,
                        "description": description
                    }
                else:
                    logger.error(f"YouTube sayfası HTTP {resp.status_code} ile yanıt verdi ({watch_url})")
        except Exception as e:
            logger.error(f"HTTPX ile YouTube metadata çekilirken hata oluştu ({video_id}): {e}")

        return {
            "title": f"YouTube Video ({video_id})",
            "description": "Video açıklaması doğrudan çekilemedi."
        }

    async def execute(self, video_url: str) -> ToolResult:
        """
        YouTube videosunun altyazısını çeker, bulamazsa başlık ve açıklamasını fallback olarak alır.
        """
        video_id = self.extract_video_id(video_url)
        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"🎬 [YOUTUBE TOOL] Transkript isteniyor: ID={video_id}, URL={video_url}")

        transcript_text = ""

        # 1. Aşama: youtube_transcript_api ile transkripti çekme
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            try:
                # Doğrudan Türkçe veya İngilizce altyazıyı dene
                transcript_items = YouTubeTranscriptApi.get_transcript(video_id, languages=["tr", "en"])
                text_pieces = [item.get("text", "").strip() for item in transcript_items if item.get("text")]
                transcript_text = " ".join(text_pieces)
            except Exception as direct_err:
                logger.warning(f"Doğrudan get_transcript çekilemedi ({video_id}): {direct_err}. list_transcripts deneniyor.")
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = None
                try:
                    transcript = transcript_list.find_transcript(["tr"])
                except Exception:
                    try:
                        transcript = transcript_list.find_generated_transcript(["tr"])
                    except Exception:
                        for t in transcript_list:
                            transcript = t
                            break

                if transcript:
                    fetched = transcript.fetch()
                    text_pieces = [
                        (item.get("text", "") if isinstance(item, dict) else getattr(item, "text", str(item))).strip()
                        for item in fetched
                    ]
                    transcript_text = " ".join([p for p in text_pieces if p])

            if transcript_text:
                logger.info(f"✅ [YOUTUBE TOOL] Transkript başarıyla çekildi ({len(transcript_text)} karakter)")
                output = (
                    f"=== YOUTUBE VİDEO TRANSKRİPTİ ===\n"
                    f"Video ID: {video_id}\n"
                    f"Kaynak URL: {canonical_url}\n"
                    f"Kelime Sayısı: {len(transcript_text.split())}\n\n"
                    f"TRANSKRİPT METNİ:\n{transcript_text}"
                )
                return ToolResult(output=output)

        except Exception as transcript_err:
            logger.error(f"YouTube transkript API hatası ({video_id}): {transcript_err}")

        # 2. Aşama: Fallback - Pytube veya HTTPX/BeautifulSoup ile Metadata
        logger.warning(f"⚠️ [YOUTUBE TOOL] Transkript bulunamadı ({video_id}). Fallback metadata devreye giriyor.")
        meta = await self._fetch_metadata_pytube(canonical_url)
        if not meta or not meta.get("title"):
            meta = await self._fetch_metadata_httpx(video_id)

        fallback_output = (
            f"=== YOUTUBE VİDEO BİLGİSİ (TRANSKRİPT BULUNAMADI - FALLBACK) ===\n"
            f"Video ID: {video_id}\n"
            f"Kaynak URL: {canonical_url}\n"
            f"Durum: TRANSCRIPT_UNAVAILABLE\n"
            f"Video Başlığı: {meta['title']}\n\n"
            f"Video Açıklaması / Notlar:\n{meta['description']}\n\n"
            f"NOT: Bu video için altyazı mevcut değildir; konu analizi videonun başlığı ve açıklaması üzerinden yürütülmelidir."
        )
        return ToolResult(output=fallback_output)
