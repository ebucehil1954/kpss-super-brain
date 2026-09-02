"""
KPSS Super-Brain: YouTube Altyazı Sağlayıcısı (Provider 1)
youtube_transcript_api kütüphanesini kullanarak resmi ve otomatik oluşturulmuş
altyazı parçalarını çeker ve zaman damgalı TranscriptSegment dizisine dönüştürür.
"""
from __future__ import annotations

import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from youtube_transcript_api import YouTubeTranscriptApi

from senses.transcript_models import (
    TranscriptProvider, TranscriptProviderType, TranscriptResult,
    TranscriptSegment, TranscriptStatus, TranscriptDiagnostics
)
from senses.proxy_pool import proxy_pool
from config import super_brain_config

logger = logging.getLogger("youtube_caption_provider")


class YouTubeCaptionProvider(TranscriptProvider):
    """YouTube resmi / otomatik altyazılarını çeken 1. Kademe Sağlayıcı"""

    @property
    def provider_type(self) -> TranscriptProviderType:
        return TranscriptProviderType.YOUTUBE_CAPTIONS

    def supports(self, video_id: str) -> bool:
        return bool(video_id and len(video_id) >= 3)

    async def attempt(self, video_id: str, **kwargs) -> TranscriptResult:
        start_time = time.time()
        start_iso = datetime.now().isoformat()
        
        # 1. Doğrudan API Çağrısı (Asenkron iş parçacığında)
        direct_result = await asyncio.to_thread(self._fetch_captions_direct, video_id)
        if direct_result.success:
            duration_ms = int((time.time() - start_time) * 1000)
            diag = TranscriptDiagnostics(
                video_id=video_id,
                provider=self.provider_type,
                attempt_number=1,
                status=TranscriptStatus.TRANSCRIPT_ACQUIRED,
                started_at=start_iso,
                finished_at=datetime.now().isoformat(),
                duration_ms=duration_ms
            )
            direct_result.diagnostics.append(diag)
            direct_result.attempts = 1
            return direct_result

        # 2. Proxy Havuzu ile Rotasyon (Aktifse ve geçerli/yapılandırılmış proxy varsa)
        if super_brain_config.PROXY_ROTATION_ENABLED and proxy_pool.has_configured_proxies():
            proxy_url = await proxy_pool.get_next_proxy()
            if proxy_url:
                proxy_result = await asyncio.to_thread(self._fetch_captions_proxy, video_id, proxy_url)
                if proxy_result.success:
                    duration_ms = int((time.time() - start_time) * 1000)
                    diag = TranscriptDiagnostics(
                        video_id=video_id,
                        provider=self.provider_type,
                        attempt_number=2,
                        status=TranscriptStatus.TRANSCRIPT_ACQUIRED,
                        started_at=start_iso,
                        finished_at=datetime.now().isoformat(),
                        duration_ms=duration_ms
                    )
                    proxy_result.diagnostics.append(diag)
                    proxy_result.attempts = 2
                    return proxy_result
                else:
                    proxy_pool.report_proxy_failure(proxy_url)

        # Başarısızlık Teşhisi
        duration_ms = int((time.time() - start_time) * 1000)
        status = direct_result.status
        diag = TranscriptDiagnostics(
            video_id=video_id,
            provider=self.provider_type,
            attempt_number=1,
            status=status,
            error_code=direct_result.error or "CAPTION_FETCH_FAILED",
            error_message=direct_result.error or "Altyazı çekilemedi.",
            started_at=start_iso,
            finished_at=datetime.now().isoformat(),
            duration_ms=duration_ms
        )
        direct_result.diagnostics.append(diag)
        direct_result.attempts = 1
        return direct_result

    def _fetch_captions_direct(self, video_id: str) -> TranscriptResult:
        try:
            cookies_arg = str(super_brain_config.YOUTUBE_COOKIES_FILE) if super_brain_config.youtube_cookies_available else None
            if cookies_arg:
                ytt = YouTubeTranscriptApi(cookies=cookies_arg)
            else:
                ytt = YouTubeTranscriptApi()
            transcript_list = ytt.list(video_id)
            return self._extract_best_transcript(transcript_list, video_id)
        except Exception as e:
            return self._classify_exception(video_id, e)

    def _fetch_captions_proxy(self, video_id: str, proxy_url: str) -> TranscriptResult:
        try:
            from youtube_transcript_api.proxies import GenericProxyConfig
            proxy_cfg = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
            cookies_arg = str(super_brain_config.YOUTUBE_COOKIES_FILE) if super_brain_config.youtube_cookies_available else None
            if cookies_arg:
                ytt = YouTubeTranscriptApi(proxy_config=proxy_cfg, cookies=cookies_arg)
            else:
                ytt = YouTubeTranscriptApi(proxy_config=proxy_cfg)
            transcript_list = ytt.list(video_id)
            return self._extract_best_transcript(transcript_list, video_id)
        except Exception as e:
            return self._classify_exception(video_id, e)

    def _extract_best_transcript(self, transcript_list: Any, video_id: str) -> TranscriptResult:
        transcript = None
        is_gen = False
        lang = "tr"

        # 1. Manuel Türkçe Altyazı
        try:
            transcript = transcript_list.find_transcript(['tr', 'tr-TR'])
            is_gen = False
            lang = "tr"
        except Exception:
            # 2. Otomatik Oluşturulmuş Türkçe Altyazı
            try:
                transcript = transcript_list.find_generated_transcript(['tr', 'tr-TR'])
                is_gen = True
                lang = "tr"
            except Exception:
                # 3. Herhangi bir altyazı
                for t in transcript_list:
                    transcript = t
                    is_gen = getattr(t, 'is_generated', False)
                    lang = getattr(t, 'language_code', 'unknown')
                    break

        if not transcript:
            return TranscriptResult(
                video_id=video_id,
                success=False,
                provider=self.provider_type,
                status=TranscriptStatus.NO_CAPTION_TRACK,
                error="NO_CAPTION_TRACK: Videoda altyazı kanalı bulunamadı."
            )

        items = transcript.fetch()
        segments: List[TranscriptSegment] = []
        for idx, it in enumerate(items):
            txt = (it.get("text", "") if isinstance(it, dict) else getattr(it, "text", "")).strip()
            if txt:
                st = float(it.get("start", 0.0) if isinstance(it, dict) else getattr(it, "start", 0.0))
                dur = float(it.get("duration", 0.0) if isinstance(it, dict) else getattr(it, "duration", 0.0))
                end = round(st + dur, 2)
                st = round(st, 2)
                segments.append(TranscriptSegment(
                    segment_id=f"cap_{video_id}_{idx}",
                    video_id=video_id,
                    start_seconds=st,
                    end_seconds=end,
                    text=txt
                ))

        if not segments:
            return TranscriptResult(
                video_id=video_id,
                success=False,
                provider=self.provider_type,
                status=TranscriptStatus.NO_CAPTION_TRACK,
                error="EMPTY_CAPTIONS: Altyazı metni boş döndü."
            )

        return TranscriptResult(
            video_id=video_id,
            success=True,
            provider=self.provider_type,
            language=lang,
            is_generated=is_gen,
            segments=segments,
            status=TranscriptStatus.TRANSCRIPT_ACQUIRED,
            confidence=0.95 if not is_gen else 0.88
        )

    def _classify_exception(self, video_id: str, exc: Exception) -> TranscriptResult:
        msg = str(exc).lower()
        if "no transcript" in msg or "could not find a transcript" in msg or "transcriptsdisabled" in msg:
            st = TranscriptStatus.NO_CAPTION_TRACK
        elif "private" in msg or "video is private" in msg:
            st = TranscriptStatus.VIDEO_PRIVATE
        elif "unavailable" in msg or "not available" in msg:
            st = TranscriptStatus.VIDEO_UNAVAILABLE
        elif "age" in msg or "sign in" in msg:
            st = TranscriptStatus.VIDEO_AGE_RESTRICTED
        elif "rate limit" in msg or "too many requests" in msg or "429" in msg or "ip" in msg or "blocked" in msg:
            st = TranscriptStatus.CAPTION_FETCH_FAILED
        else:
            st = TranscriptStatus.CAPTION_FETCH_FAILED

        return TranscriptResult(
            video_id=video_id,
            success=False,
            provider=self.provider_type,
            status=st,
            error=str(exc)
        )
