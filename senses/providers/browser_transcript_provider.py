"""
KPSS Super-Brain: Tarayıcı / Sayfa Kazıma Altyazı Sağlayıcısı (Provider 3)
Doğrudan YouTube video izleme sayfasındaki `ytInitialPlayerResponse` veya
`captionTracks` JSON verisini çözümleyerek altyazı akışını çeker (Playwright / HTTP Scraper).
"""
from __future__ import annotations

import re
import json
import time
import httpx
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Optional

from senses.transcript_models import (
    TranscriptProvider, TranscriptProviderType, TranscriptResult,
    TranscriptSegment, TranscriptStatus, TranscriptDiagnostics
)

logger = logging.getLogger("browser_transcript_provider")


class BrowserTranscriptProvider(TranscriptProvider):
    """HTML / Player Response veya Headless Tarayıcı üzerinden altyazı çıkaran 3. Kademe Sağlayıcı"""

    @property
    def provider_type(self) -> TranscriptProviderType:
        return TranscriptProviderType.BROWSER_PLAYWRIGHT

    def supports(self, video_id: str) -> bool:
        return bool(video_id and len(video_id) >= 3)

    async def attempt(self, video_id: str, **kwargs) -> TranscriptResult:
        start_time = time.time()
        start_iso = datetime.now().isoformat()

        result = await self._fetch_via_watch_page(video_id)

        duration_ms = int((time.time() - start_time) * 1000)
        diag = TranscriptDiagnostics(
            video_id=video_id,
            provider=self.provider_type,
            attempt_number=1,
            status=result.status,
            error_code=result.error if not result.success else None,
            error_message=result.error if not result.success else None,
            started_at=start_iso,
            finished_at=datetime.now().isoformat(),
            duration_ms=duration_ms
        )
        result.diagnostics.append(diag)
        result.attempts = 1
        return result

    async def _fetch_via_watch_page(self, video_id: str) -> TranscriptResult:
        from config import super_brain_config
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        cookie_jar = None
        if super_brain_config.youtube_cookies_available:
            try:
                import http.cookiejar
                jar = http.cookiejar.MozillaCookieJar(str(super_brain_config.YOUTUBE_COOKIES_FILE))
                jar.load(ignore_discard=True, ignore_expires=True)
                cookie_jar = jar
            except Exception:
                pass

        try:
            async with httpx.AsyncClient(timeout=25.0, follow_redirects=True, cookies=cookie_jar) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return TranscriptResult(
                        video_id=video_id,
                        success=False,
                        provider=self.provider_type,
                        status=TranscriptStatus.BROWSER_EXTRACTION_FAILED,
                        error=f"HTTP_STATUS_{resp.status_code}: Sayfa yüklenemedi."
                    )

                html = resp.text

                # Video durum kontrolleri
                if '"status":"LOGIN_REQUIRED"' in html or "Sign in to confirm your age" in html:
                    return TranscriptResult(
                        video_id=video_id,
                        success=False,
                        provider=self.provider_type,
                        status=TranscriptStatus.VIDEO_AGE_RESTRICTED,
                        error="VIDEO_AGE_RESTRICTED: Yaş kısıtlaması veya giriş zorunluluğu var."
                    )
                if '"status":"UNPLAYABLE"' in html or "This video is private" in html:
                    return TranscriptResult(
                        video_id=video_id,
                        success=False,
                        provider=self.provider_type,
                        status=TranscriptStatus.VIDEO_PRIVATE,
                        error="VIDEO_PRIVATE: Video gizli veya oynatılamaz."
                    )

                # captionTracks JSON verisini ara
                match = re.search(r'"captionTracks":\s*(\[.*?\])', html)
                if not match:
                    return TranscriptResult(
                        video_id=video_id,
                        success=False,
                        provider=self.provider_type,
                        status=TranscriptStatus.NO_CAPTION_TRACK,
                        error="NO_CAPTION_TRACK: Sayfa HTML içinde captionTracks bulunamadı."
                    )

                try:
                    caption_tracks = json.loads(match.group(1))
                except Exception:
                    return TranscriptResult(
                        video_id=video_id,
                        success=False,
                        provider=self.provider_type,
                        status=TranscriptStatus.BROWSER_EXTRACTION_FAILED,
                        error="JSON_PARSE_ERROR: captionTracks bloğu ayrıştırılamadı."
                    )

                if not caption_tracks:
                    return TranscriptResult(
                        video_id=video_id,
                        success=False,
                        provider=self.provider_type,
                        status=TranscriptStatus.NO_CAPTION_TRACK,
                        error="NO_CAPTION_TRACK: captionTracks listesi boş."
                    )

                # Tercihen Türkçe kanalı seç
                selected_track = caption_tracks[0]
                for track in caption_tracks:
                    lang_code = track.get("languageCode", "").lower()
                    if "tr" in lang_code:
                        selected_track = track
                        break

                base_url = selected_track.get("baseUrl")
                if not base_url:
                    return TranscriptResult(
                        video_id=video_id,
                        success=False,
                        provider=self.provider_type,
                        status=TranscriptStatus.BROWSER_EXTRACTION_FAILED,
                        error="MISSING_BASE_URL: Altyazı baseUrl adresi bulunamadı."
                    )

                # Altyazı XML/JSON içeriğini çek
                sub_resp = await client.get(base_url, headers=headers)
                if sub_resp.status_code != 200:
                    return TranscriptResult(
                        video_id=video_id,
                        success=False,
                        provider=self.provider_type,
                        status=TranscriptStatus.BROWSER_EXTRACTION_FAILED,
                        error=f"SUBTITLE_HTTP_{sub_resp.status_code}: Altyazı URL'sinden veri alınamadı."
                    )

                segments = self._parse_xml_captions(sub_resp.text, video_id)
                if not segments:
                    return TranscriptResult(
                        video_id=video_id,
                        success=False,
                        provider=self.provider_type,
                        status=TranscriptStatus.NO_CAPTION_TRACK,
                        error="EMPTY_CAPTIONS: Çekilen XML içinde geçerli segment bulunamadı."
                    )

                return TranscriptResult(
                    video_id=video_id,
                    success=True,
                    provider=self.provider_type,
                    language=selected_track.get("languageCode", "tr"),
                    is_generated=bool(selected_track.get("kind") == "asr"),
                    segments=segments,
                    status=TranscriptStatus.TRANSCRIPT_ACQUIRED,
                    confidence=0.90
                )

        except httpx.TimeoutException:
            return TranscriptResult(
                video_id=video_id,
                success=False,
                provider=self.provider_type,
                status=TranscriptStatus.TRANSCRIPT_FAILED_TEMPORARY,
                error="TIMEOUT: Sayfa kazıma istek zaman aşımına uğradı."
            )
        except Exception as e:
            return TranscriptResult(
                video_id=video_id,
                success=False,
                provider=self.provider_type,
                status=TranscriptStatus.BROWSER_EXTRACTION_FAILED,
                error=f"BROWSER_SCRAPER_ERROR: {str(e)}"
            )

    @classmethod
    def _parse_xml_captions(cls, xml_text: str, video_id: str) -> List[TranscriptSegment]:
        segments: List[TranscriptSegment] = []
        try:
            root = ET.fromstring(xml_text)
            for idx, elem in enumerate(root.findall(".//text")):
                txt = (elem.text or "").strip()
                if txt:
                    # XML entity temizleme (&amp; &#39; vb.)
                    txt = txt.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
                    start = float(elem.attrib.get("start", 0.0))
                    dur = float(elem.attrib.get("dur", 0.0))
                    end = round(start + dur, 2)
                    start = round(start, 2)

                    segments.append(TranscriptSegment(
                        segment_id=f"browser_{video_id}_{idx}",
                        video_id=video_id,
                        start_seconds=start,
                        end_seconds=end,
                        text=txt
                    ))
        except Exception as e:
            logger.warning(f"XML parse error for {video_id}: {e}")
        return segments
