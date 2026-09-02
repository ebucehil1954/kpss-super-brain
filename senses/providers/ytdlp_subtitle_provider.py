"""
KPSS Super-Brain: yt-dlp Altyazı Sağlayıcısı (Provider 2)
Videoyu indirmeden yalnızca VTT/SRT altyazı akışlarını (--skip-download) çeker
ve regex ayrıştırması ile zaman damgalı TranscriptSegment dizisine dönüştürür.
"""
from __future__ import annotations

import os
import re
import glob
import time
import shutil
import asyncio
import tempfile
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from senses.transcript_models import (
    TranscriptProvider, TranscriptProviderType, TranscriptResult,
    TranscriptSegment, TranscriptStatus, TranscriptDiagnostics
)
from config import super_brain_config

logger = logging.getLogger("ytdlp_subtitle_provider")


class YtDlpSubtitleProvider(TranscriptProvider):
    """yt-dlp ile doğrudan VTT/SRT altyazılarını çıkaran 2. Kademe Sağlayıcı"""

    @property
    def provider_type(self) -> TranscriptProviderType:
        return TranscriptProviderType.YTDLP_SUBTITLES

    def supports(self, video_id: str) -> bool:
        return bool(video_id and len(video_id) >= 3)

    async def attempt(self, video_id: str, **kwargs) -> TranscriptResult:
        start_time = time.time()
        start_iso = datetime.now().isoformat()

        # yt-dlp komutunu izole geçici klasörde çalıştır
        result = await asyncio.to_thread(self._fetch_subtitles_ytdlp, video_id)
        
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

    def _fetch_subtitles_ytdlp(self, video_id: str) -> TranscriptResult:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        temp_dir = tempfile.mkdtemp(prefix=f"ytdlp_subs_{video_id}_")

        import sys
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--js-runtimes", "node",
            "--extractor-args", "youtube:player_client=android",
            "--write-sub",
            "--write-auto-sub",
            "--sub-lang", "tr,tr-orig,tr-TR,en",
            "--skip-download",
            "--sub-format", "vtt/srt/best",
            "--no-playlist",
            "--socket-timeout", "30",
            "-o", os.path.join(temp_dir, "%(id)s.%(ext)s"),
        ]

        # Çerez Desteği (Bot ve IP Engeli Savunması)
        if super_brain_config.youtube_cookies_available:
            cmd.extend(["--cookies", str(super_brain_config.YOUTUBE_COOKIES_FILE)])
        elif super_brain_config.YOUTUBE_COOKIES_BROWSER:
            cmd.extend(["--cookies-from-browser", super_brain_config.YOUTUBE_COOKIES_BROWSER])

        cmd.append(video_url)

        try:

            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

            # VTT veya SRT dosyalarını tara
            sub_files = glob.glob(os.path.join(temp_dir, f"{video_id}*.vtt")) + \
                        glob.glob(os.path.join(temp_dir, f"{video_id}*.srt"))

            if not sub_files:
                err_combined = (stdout + "\n" + stderr).lower()
                if "bot" in err_combined or "sign in" in err_combined or "429" in err_combined or "blocked" in err_combined:
                    st = TranscriptStatus.YTDLP_BLOCKED
                    err_msg = "YTDLP_BLOCKED: YouTube bot/IP doğrulaması talep etti."
                elif "private" in err_combined:
                    st = TranscriptStatus.VIDEO_PRIVATE
                    err_msg = "VIDEO_PRIVATE: Video gizli."
                elif "unavailable" in err_combined:
                    st = TranscriptStatus.VIDEO_UNAVAILABLE
                    err_msg = "VIDEO_UNAVAILABLE: Video mevcut değil."
                else:
                    st = TranscriptStatus.NO_CAPTION_TRACK
                    err_msg = "NO_CAPTION_TRACK: yt-dlp altyazı dosyası bulamadı."

                return TranscriptResult(
                    video_id=video_id,
                    success=False,
                    provider=self.provider_type,
                    status=st,
                    error=err_msg
                )

            # Tercihen tr VTT dosyasını seç
            target_file = sub_files[0]
            for sf in sub_files:
                if ".tr." in sf or "tr-TR" in sf:
                    target_file = sf
                    break

            segments = self._parse_vtt_or_srt(target_file, video_id)
            if not segments:
                return TranscriptResult(
                    video_id=video_id,
                    success=False,
                    provider=self.provider_type,
                    status=TranscriptStatus.NO_CAPTION_TRACK,
                    error="EMPTY_SUBTITLES: Altyazı dosyası ayrıştırıldı fakat segment bulunamadı."
                )

            return TranscriptResult(
                video_id=video_id,
                success=True,
                provider=self.provider_type,
                language="tr",
                is_generated=True if "auto" in target_file.lower() else False,
                segments=segments,
                status=TranscriptStatus.TRANSCRIPT_ACQUIRED,
                confidence=0.92
            )

        except subprocess.TimeoutExpired:
            return TranscriptResult(
                video_id=video_id,
                success=False,
                provider=self.provider_type,
                status=TranscriptStatus.TRANSCRIPT_FAILED_TEMPORARY,
                error="TIMEOUT: yt-dlp altyazı çekme zaman aşımına uğradı."
            )
        except Exception as e:
            return TranscriptResult(
                video_id=video_id,
                success=False,
                provider=self.provider_type,
                status=TranscriptStatus.CAPTION_FETCH_FAILED,
                error=f"YTDLP_ERROR: {str(e)}"
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _parse_vtt_or_srt(cls, file_path: str, video_id: str) -> List[TranscriptSegment]:
        segments: List[TranscriptSegment] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        # Zaman damgası deseni: 00:01:23.456 --> 00:01:28.120 veya 01:23.456 --> 01:28.120
        time_pattern = re.compile(
            r"((?:(\d{1,2}):)?(\d{2}):(\d{2})[.,](\d{3}))\s*-->\s*((?:(\d{1,2}):)?(\d{2}):(\d{2})[.,](\d{3}))"
        )

        blocks = re.split(r"\n\s*\n", content)
        seg_idx = 0
        seen_texts = set()

        for b in blocks:
            lines = [line.strip() for line in b.splitlines() if line.strip()]
            if not lines:
                continue

            time_match = None
            text_lines = []
            for line in lines:
                m = time_pattern.search(line)
                if m:
                    time_match = m
                elif not line.isdigit() and not line.startswith("WEBVTT") and not line.startswith("NOTE"):
                    # HTML/VTT tag temizliği (<c>, </c>, <00:01:22>)
                    clean_line = re.sub(r"<[^>]+>", "", line).strip()
                    if clean_line:
                        text_lines.append(clean_line)

            if time_match and text_lines:
                start_sec = cls._timestamp_to_seconds(time_match.group(1))
                end_sec = cls._timestamp_to_seconds(time_match.group(6))
                combined_text = " ".join(text_lines)

                # Mükerrer satır eleme (özellikle dinamik VTT'ler ardışık yineler)
                norm = f"{int(start_sec)}:{combined_text}"
                if norm not in seen_texts and combined_text:
                    seen_texts.add(norm)
                    segments.append(TranscriptSegment(
                        segment_id=f"ytdlp_{video_id}_{seg_idx}",
                        video_id=video_id,
                        start_seconds=round(start_sec, 2),
                        end_seconds=round(end_sec, 2),
                        text=combined_text
                    ))
                    seg_idx += 1

        return segments

    @staticmethod
    def _timestamp_to_seconds(ts_str: str) -> float:
        ts_str = ts_str.replace(",", ".")
        parts = ts_str.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return float(h) * 3600 + float(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return float(m) * 60 + float(s)
        return 0.0
