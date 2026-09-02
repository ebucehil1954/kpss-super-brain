"""
KPSS Super-Brain: Yerel Whisper STT Sağlayıcısı (Provider 4 - Son Savunma Hattı)
Videoda hiçbir altyazı bulunamadığında, yt-dlp ile yalnızca ses akışını (m4a/audio-only)
indirerek GPU/CPU yerel Whisper modeli ile zaman damgalı segmentlere dönüştürür.
"""
from __future__ import annotations

import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from senses.transcript_models import (
    TranscriptProvider, TranscriptProviderType, TranscriptResult,
    TranscriptSegment, TranscriptStatus, TranscriptDiagnostics
)
from senses.whisper_transcriber import whisper_transcriber
from config import super_brain_config

logger = logging.getLogger("whisper_provider")


class WhisperProvider(TranscriptProvider):
    """GPU / CPU Yerel Whisper STT Çözümleyicisi (Son Savunma Hattı)"""

    @property
    def provider_type(self) -> TranscriptProviderType:
        return TranscriptProviderType.LOCAL_WHISPER

    def supports(self, video_id: str) -> bool:
        # Whisper yapılandırması etkinse ve geçerli video_id ise destekler
        return bool(super_brain_config.WHISPER_ENABLED and video_id and len(video_id) >= 3)

    async def attempt(self, video_id: str, **kwargs) -> TranscriptResult:
        start_time = time.time()
        start_iso = datetime.now().isoformat()

        try:
            whisper_res = await whisper_transcriber.transcribe_video(video_id)
            duration_ms = int((time.time() - start_time) * 1000)

            if whisper_res.get("success") and whisper_res.get("text"):
                raw_segments = whisper_res.get("segments", [])
                segments: List[TranscriptSegment] = []

                for idx, s in enumerate(raw_segments):
                    txt = s.get("text", "").strip()
                    if txt:
                        st = round(float(s.get("start_seconds", 0.0)), 2)
                        en = round(float(s.get("end_seconds", 0.0)), 2)
                        seg_id = s.get("segment_id") or f"whisper_{video_id}_{idx}"
                        segments.append(TranscriptSegment(
                            segment_id=seg_id,
                            video_id=video_id,
                            start_seconds=st,
                            end_seconds=en,
                            text=txt,
                            segment_hash=s.get("segment_hash", "")
                        ))

                result = TranscriptResult(
                    video_id=video_id,
                    success=True,
                    provider=self.provider_type,
                    language="tr",
                    is_generated=True,
                    segments=segments,
                    status=TranscriptStatus.TRANSCRIPT_ACQUIRED,
                    confidence=0.88
                )
                diag = TranscriptDiagnostics(
                    video_id=video_id,
                    provider=self.provider_type,
                    attempt_number=1,
                    status=TranscriptStatus.TRANSCRIPT_ACQUIRED,
                    started_at=start_iso,
                    finished_at=datetime.now().isoformat(),
                    duration_ms=duration_ms
                )
                result.diagnostics.append(diag)
                result.attempts = 1
                return result

            else:
                err = whisper_res.get("error", "Whisper transkripsiyon başarısız oldu.")
                err_lower = err.lower()
                if "ses akışı indirilemedi" in err_lower or "download" in err_lower:
                    st = TranscriptStatus.AUDIO_DOWNLOAD_FAILED
                else:
                    st = TranscriptStatus.WHISPER_FAILED

                result = TranscriptResult(
                    video_id=video_id,
                    success=False,
                    provider=self.provider_type,
                    status=st,
                    error=err
                )
                diag = TranscriptDiagnostics(
                    video_id=video_id,
                    provider=self.provider_type,
                    attempt_number=1,
                    status=st,
                    error_code=st.value,
                    error_message=err,
                    started_at=start_iso,
                    finished_at=datetime.now().isoformat(),
                    duration_ms=duration_ms
                )
                result.diagnostics.append(diag)
                result.attempts = 1
                return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            err_msg = f"WHISPER_EXCEPTION: {str(e)}"
            result = TranscriptResult(
                video_id=video_id,
                success=False,
                provider=self.provider_type,
                status=TranscriptStatus.WHISPER_FAILED,
                error=err_msg
            )
            diag = TranscriptDiagnostics(
                video_id=video_id,
                provider=self.provider_type,
                attempt_number=1,
                status=TranscriptStatus.WHISPER_FAILED,
                error_code="WHISPER_FAILED",
                error_message=err_msg,
                started_at=start_iso,
                finished_at=datetime.now().isoformat(),
                duration_ms=duration_ms
            )
            result.diagnostics.append(diag)
            result.attempts = 1
            return result
