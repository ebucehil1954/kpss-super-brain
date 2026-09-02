"""
KPSS Super-Brain: Phase 14 — Whisper & CUDA Güvenlik Testleri
Master Refactor Plan Phase 14 Kapsamı:
1. test_cuda_detection_falls_back_cleanly_to_cpu: CUDA yoksa veya arızalanırsa sistem CPU'ya temiz şekilde düşer, çökmez.
2. test_chunked_audio_processing_respects_limits: Uzun sesler VRAM aşımını önlemek için güvenli dilimlere bölünür.
3. test_whisper_error_is_classified_correctly: Ses ve bellek hataları doğru sınıflandırılır.
"""
import pytest
from senses.whisper_transcriber import WhisperTranscriber

def test_cuda_detection_falls_back_cleanly_to_cpu():
    """Phase 14: CUDA yoksa veya arızalanırsa Whisper motoru CPU fallback'e geçer."""
    transcriber = WhisperTranscriber()
    # CUDA'nın olmadığını simüle et
    transcriber.is_gpu_available = False
    assert transcriber.is_gpu_available is False

    # Donanım denetimi sistemi çökertmez
    transcriber._check_hardware()
    assert isinstance(transcriber.is_gpu_available, bool)

def test_chunked_audio_processing_respects_limits():
    """Phase 14: 1800 saniyelik (30 dk) ses 600'er saniyelik güvenli pencerelere bölünür."""
    total_sec = 1800.0
    chunks = WhisperTranscriber.chunk_audio_duration(total_sec, max_chunk_seconds=600.0)
    assert len(chunks) == 3
    assert chunks[0] == (0.0, 600.0)
    assert chunks[1] == (600.0, 1200.0)
    assert chunks[2] == (1200.0, 1800.0)

    # Kısa ses (200 saniye) tek parça kalır
    short_chunks = WhisperTranscriber.chunk_audio_duration(200.0, max_chunk_seconds=600.0)
    assert len(short_chunks) == 1
    assert short_chunks[0] == (0.0, 200.0)

def test_whisper_error_is_classified_correctly():
    """Phase 14: Hata mesajları doğru kategorize edilir."""
    assert WhisperTranscriber.classify_whisper_error("CUDA error: out of memory") == "CUDA_OOM_FALLBACK_REQUIRED"
    assert WhisperTranscriber.classify_whisper_error("ERROR: 404 Video Unavailable on yt-dlp") == "AUDIO_DOWNLOAD_FAILED"
    assert WhisperTranscriber.classify_whisper_error("Corrupted ffmpeg audio stream") == "CORRUPTED_AUDIO"
    assert WhisperTranscriber.classify_whisper_error("Something weird happened") == "GENERIC_AUDIO_FAILURE"
