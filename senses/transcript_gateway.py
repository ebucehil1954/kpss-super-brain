"""
KPSS Super-Brain: Transcript Gateway & Fallback Motoru (Transcript Gateway V1)
Şartnamede tanımlanan 4 kademeli katı fallback sırasını, sağlayıcı bazlı devre kesiciyi (Circuit Breaker)
ve adli teşhis günlüğü kaydını yöneten merkezi transkript ağ geçidi.
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from senses.transcript_models import (
    TranscriptProvider, TranscriptProviderType, TranscriptResult,
    TranscriptSegment, TranscriptStatus, TranscriptDiagnostics
)
from senses.providers.youtube_caption_provider import YouTubeCaptionProvider
from senses.providers.ytdlp_subtitle_provider import YtDlpSubtitleProvider
from senses.providers.browser_transcript_provider import BrowserTranscriptProvider
from senses.providers.whisper_provider import WhisperProvider
from config import super_brain_config
from brain.database import db_session

logger = logging.getLogger("transcript_gateway")


class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class ProviderCircuitBreaker:
    """Sağlayıcı düzeyinde arızaları izole eden devre kesici"""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 120.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state: Dict[TranscriptProviderType, str] = {}
        self.failure_count: Dict[TranscriptProviderType, int] = {}
        self.last_failure_time: Dict[TranscriptProviderType, float] = {}

    def is_available(self, provider_type: TranscriptProviderType) -> bool:
        state = self.state.get(provider_type, CircuitState.CLOSED)
        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.OPEN:
            elapsed = time.time() - self.last_failure_time.get(provider_type, 0.0)
            if elapsed >= self.cooldown_seconds:
                self.state[provider_type] = CircuitState.HALF_OPEN
                logger.info(f"🔄 [CIRCUIT BREAKER] {provider_type.value} HALF_OPEN durumuna geçti, deneme yapılacak.")
                return True
            return False

        # HALF_OPEN durumunda 1 denemeye izin ver
        return True

    def record_success(self, provider_type: TranscriptProviderType):
        self.state[provider_type] = CircuitState.CLOSED
        self.failure_count[provider_type] = 0

    def record_failure(self, provider_type: TranscriptProviderType):
        failures = self.failure_count.get(provider_type, 0) + 1
        self.failure_count[provider_type] = failures
        self.last_failure_time[provider_type] = time.time()

        if failures >= self.failure_threshold:
            self.state[provider_type] = CircuitState.OPEN
            logger.warning(
                f"⚡ [CIRCUIT BREAKER] {provider_type.value} {failures} ardışık hata nedeniyle "
                f"OPEN durumuna alındı! ({self.cooldown_seconds}s boyunca atlanacak)"
            )

    def trip_breaker(self, provider_type: TranscriptProviderType, reason: str = ""):
        """Sistemik IP engeli (HTTP 429 / bot algılama) durumunda devreyi derhal OPEN durumuna alır."""
        self.state[provider_type] = CircuitState.OPEN
        self.last_failure_time[provider_type] = time.time()
        logger.warning(
            f"⚡ [CIRCUIT BREAKER] {provider_type.value} sistemik IP engeli ({reason}) nedeniyle "
            f"derhal OPEN durumuna alındı! ({self.cooldown_seconds}s boyunca atlanacak)"
        )


class TranscriptGateway:
    """4 Kademeli Dayanıklı Transkript Ağ Geçidi"""

    TRANSCRIPTS_DIR = str(super_brain_config.TRANSCRIPTS_DIR)

    def __init__(self):
        self.circuit_breaker = ProviderCircuitBreaker(failure_threshold=3, cooldown_seconds=120.0)
        self.providers: List[TranscriptProvider] = [
            YouTubeCaptionProvider(),
            YtDlpSubtitleProvider(),
            BrowserTranscriptProvider(),
            WhisperProvider()
        ]

    async def get_transcript(self, video_id: str, allow_whisper: bool = True) -> TranscriptResult:
        """
        4 Kademeli Katı Fallback Akışı:
        1. Disk Önbellek
        2. YouTubeCaptionProvider (Resmi / Otomatik Altyazı)
        3. YtDlpSubtitleProvider (yt-dlp VTT/SRT Altyazı Akışı)
        4. BrowserTranscriptProvider (Sayfa Kazıma / Player Response)
        5. WhisperProvider (Yalnızca Ses + Yerel Whisper STT)
        """
        # 1. Disk Önbelleği Kontrolü
        cached = self._load_disk_cache(video_id)
        if cached:
            self._save_segments_to_db(cached.segments)
            return cached

        all_diagnostics: List[TranscriptDiagnostics] = []
        attempt_counter = 0

        # Sağlayıcıları Sırayla Dene
        for provider in self.providers:
            # Whisper politikası kontrolü
            if provider.provider_type == TranscriptProviderType.LOCAL_WHISPER and not allow_whisper:
                continue

            if not provider.supports(video_id):
                continue

            # Devre kesici kontrolü
            if not self.circuit_breaker.is_available(provider.provider_type):
                logger.info(f"⏭️ [GATEWAY] {provider.provider_type.value} devre kesici OPEN olduğu için atlanıyor.")
                continue

            attempt_counter += 1
            logger.info(f"▶️ [GATEWAY] Deneniyor: {provider.provider_type.value} (Video: {video_id})")

            try:
                result = await provider.attempt(video_id)
                if not result.diagnostics:
                    diag = TranscriptDiagnostics(
                        video_id=video_id,
                        provider=provider.provider_type,
                        attempt_number=attempt_counter,
                        status=result.status,
                        error_code=result.error or result.status.value,
                        error_message=result.error
                    )
                    all_diagnostics.append(diag)
                    self._persist_diagnostics(diag)
                else:
                    all_diagnostics.extend(result.diagnostics)
                    for diag in result.diagnostics:
                        self._persist_diagnostics(diag)

                if result.success and result.segments:
                    self.circuit_breaker.record_success(provider.provider_type)
                    # Önbelleğe ve veritabanına mühürle
                    self._save_disk_cache(result)
                    self._save_segments_to_db(result.segments)

                    result.diagnostics = all_diagnostics
                    result.attempts = attempt_counter
                    logger.info(f"✅ [GATEWAY] Altyazı başarıyla alındı: {provider.provider_type.value} ({len(result.segments)} segment)")
                    return result
                else:
                    self.circuit_breaker.record_failure(provider.provider_type)
                    logger.warning(f"⚠️ [GATEWAY] {provider.provider_type.value} başarısız: {result.error}")

                    # Eğer hata IP engeli veya bot doğrulaması ise devreyi derhal aç (hızlı fallback)
                    err_str = str(result.error or "")
                    if "429" in err_str or "blocking requests from your IP" in err_str or "YTDLP_BLOCKED" in err_str or "Too Many Requests" in err_str:
                        self.circuit_breaker.trip_breaker(provider.provider_type, reason="IP_RATE_LIMITED_429")

                    # Kalıcı video hatalarında (Gizli/Silinmiş) diğer sağlayıcıları zorlamaya gerek yoktur
                    if result.status in (TranscriptStatus.VIDEO_PRIVATE, TranscriptStatus.VIDEO_UNAVAILABLE, TranscriptStatus.VIDEO_AGE_RESTRICTED):
                        result.diagnostics = all_diagnostics
                        result.attempts = attempt_counter
                        return result

            except Exception as e:
                logger.error(f"❌ [GATEWAY] {provider.provider_type.value} beklenmeyen hata: {e}")
                self.circuit_breaker.record_failure(provider.provider_type)
                diag = TranscriptDiagnostics(
                    video_id=video_id,
                    provider=provider.provider_type,
                    attempt_number=attempt_counter,
                    status=TranscriptStatus.TRANSCRIPT_FAILED_TEMPORARY,
                    error_code="UNEXPECTED_PROVIDER_CRASH",
                    error_message=str(e),
                    duration_ms=0
                )
                all_diagnostics.append(diag)
                self._persist_diagnostics(diag)

        # Tüm sağlayıcılar tükendi — Şartname Kuralı: TRANSCRIPT_DEFERRED olarak mühürle
        logger.error(f"🛑 [GATEWAY] {video_id} için TÜM sağlayıcılar başarısız oldu. TRANSCRIPT_DEFERRED işaretleniyor.")
        return TranscriptResult(
            video_id=video_id,
            success=False,
            status=TranscriptStatus.TRANSCRIPT_DEFERRED,
            error="TRANSCRIPT_UNAVAILABLE",
            diagnostics=all_diagnostics,
            attempts=attempt_counter
        )

    def _save_disk_cache(self, result: TranscriptResult):
        """Yapılandırılmış JSON önbelleğini diske kaydeder"""
        os.makedirs(self.TRANSCRIPTS_DIR, exist_ok=True)
        json_path = os.path.join(self.TRANSCRIPTS_DIR, f"{result.video_id}_transcript.json")
        txt_path = os.path.join(self.TRANSCRIPTS_DIR, f"{result.video_id}_transcript.txt")

        cache_data = {
            "video_id": result.video_id,
            "source_type": result.provider.value if result.provider else "UNKNOWN",
            "full_text": result.full_text,
            "segments": [s.model_dump() for s in result.segments],
            "language": result.language,
            "is_generated": result.is_generated,
            "confidence": result.confidence,
            "fetched_at": datetime.now().isoformat(),
            "content_hash": hashlib.sha256(result.full_text.encode("utf-8")).hexdigest()[:16]
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result.full_text)

    def _load_disk_cache(self, video_id: str) -> Optional[TranscriptResult]:
        """Diskteki yapılandırılmış JSON önbelleğini okur"""
        json_path = os.path.join(self.TRANSCRIPTS_DIR, f"{video_id}_transcript.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    full_text = data.get("full_text", "")
                    if full_text and len(full_text.strip()) > 50:
                        segments = [TranscriptSegment(**s) for s in data.get("segments", [])]
                        prov = TranscriptProviderType(data.get("source_type", "DISK_CACHE")) if data.get("source_type") in TranscriptProviderType.__members__ else TranscriptProviderType.DISK_CACHE
                        return TranscriptResult(
                            video_id=video_id,
                            success=True,
                            provider=prov,
                            language=data.get("language", "tr"),
                            is_generated=data.get("is_generated", False),
                            segments=segments,
                            full_text=full_text,
                            cached=True,
                            status=TranscriptStatus.TRANSCRIPT_ACQUIRED,
                            confidence=data.get("confidence", 0.95)
                        )
            except Exception as e:
                logger.warning(f"Disk cache read error for {video_id}: {e}")
        return None

    def _save_segments_to_db(self, segments: List[TranscriptSegment]):
        """Segmentleri SQLite transcript_segments tablosuna mühürler"""
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
                    s.segment_id, s.video_id, s.start_seconds,
                    s.end_seconds, s.text, s.segment_hash
                ))

    def _persist_diagnostics(self, diag: TranscriptDiagnostics):
        """Teşhis günlüğünü SQLite transcript_provider_attempts tablosuna yazar"""
        try:
            with db_session() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO transcript_provider_attempts (
                    video_id, provider, attempt_number, status,
                    error_code, error_message, started_at, finished_at, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    diag.video_id, diag.provider.value, diag.attempt_number,
                    diag.status.value, diag.error_code, diag.error_message,
                    diag.started_at, diag.finished_at, diag.duration_ms
                ))
        except Exception as e:
            logger.warning(f"Could not persist transcript diagnostics: {e}")


transcript_gateway = TranscriptGateway()
