"""
KPSS Super-Brain: Yerel Ses Transkriptörü ve Whisper Köprüsü (Audio Transcriber v3)
YouTube altyazısının bulunmadığı veya IP kısıtlaması olduğu durumlarda
yerel faster-whisper / whisper.cpp motorunu çağırarak sesi yazıya döker.
"""
import os
import subprocess
from typing import Dict, Any, Optional

class LocalAudioTranscriber:
    @classmethod
    def transcribe_audio_file(cls, audio_file_path: str) -> Dict[str, Any]:
        """
        Yerel ses dosyasını Whisper kütüphanesi varsa kullanarak Türkçe transkribe eder.
        """
        if not os.path.exists(audio_file_path):
            return {"success": False, "error": "Ses dosyası bulunamadı", "text": ""}

        # faster-whisper varsa kullan
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("small", device="cpu", compute_type="int8")
            segments, info = model.transcribe(audio_file_path, language="tr", beam_size=5)
            full_text = " ".join([s.text for s in segments])
            return {
                "success": True,
                "text": full_text,
                "language": info.language,
                "duration": info.duration
            }
        except ImportError:
            pass

        return {
            "success": False,
            "error": "faster-whisper kütüphanesi yüklü değil",
            "text": ""
        }

audio_transcriber = LocalAudioTranscriber()
