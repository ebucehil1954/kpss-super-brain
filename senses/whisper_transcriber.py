"""
KPSS Super-Brain: GPU Hızlandırmalı Yerel Whisper Ses Transkripsiyon Motoru (Whisper Transcriber v3)
YouTube altyazısı bulunmayan veya IP engeli nedeniyle altyazı çekilemeyen videoların sesini
yt-dlp ile doğrudan indirip yerel GPU (NVIDIA CUDA) üzerinde çalışan Whisper modeli ile %100 doğrulukla metne dönüştürür.
"""
import os
import subprocess
import shutil
import asyncio
from typing import Dict, Any, Optional
from config import super_brain_config

class WhisperTranscriber:
    def __init__(self):
        self.audio_dir = str(super_brain_config.AUDIO_DOWNLOAD_DIR)
        self.whisper_model = None
        self.is_gpu_available = False
        self._check_hardware()

    def _check_hardware(self):
        """CUDA GPU desteğini ve donanımı kontrol eder."""
        try:
            import torch
            self.is_gpu_available = torch.cuda.is_available()
        except ImportError:
            self.is_gpu_available = False

    def _load_model(self):
        """Whisper modelini GPU/CPU üzerine yükler."""
        if self.whisper_model is not None:
            return self.whisper_model

        model_size = super_brain_config.WHISPER_MODEL_SIZE
        device = "cuda" if self.is_gpu_available else "cpu"

        # 1. Öncelik: faster-whisper (Çok hızlı GPU çıkarımı)
        try:
            from faster_whisper import WhisperModel
            compute_type = "float16" if self.is_gpu_available else "int8"
            self.whisper_model = ("faster_whisper", WhisperModel(model_size, device=device, compute_type=compute_type))
            return self.whisper_model
        except Exception:
            pass

        # 2. Öncelik: openai-whisper
        try:
            import whisper
            self.whisper_model = ("openai_whisper", whisper.load_model(model_size, device=device))
            return self.whisper_model
        except Exception:
            pass

        return None

    def download_audio_yt_dlp(self, video_id: str) -> Optional[str]:
        """yt-dlp kullanarak YouTube videosunun ses akışını indirir."""
        output_template = os.path.join(self.audio_dir, f"{video_id}.%(ext)s")
        target_audio_path = os.path.join(self.audio_dir, f"{video_id}.m4a")

        if os.path.exists(target_audio_path):
            return target_audio_path

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # yt-dlp komutu
        cmd = [
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio",
            "--extract-audio",
            "--audio-format", "m4a",
            "--no-playlist",
            "--max-filesize", "80M",
            "-o", output_template,
            video_url
        ]

        try:
            # yt-dlp var mı kontrol et
            if not shutil.which("yt-dlp"):
                # python -m yt_dlp dene
                cmd = ["python", "-m", "yt_dlp"] + cmd[1:]

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
            if os.path.exists(target_audio_path):
                return target_audio_path
            
            # Farklı uzantıyla inmiş olabilir
            for fname in os.listdir(self.audio_dir):
                if fname.startswith(video_id):
                    return os.path.join(self.audio_dir, fname)
        except Exception as e:
            print(f"⚠️ [WHISPER AUDIO DOWNLOAD] Ses indirme hatası: {e}")

        return None

    async def transcribe_video(self, video_id: str) -> Dict[str, Any]:
        """Videoyu indirir ve yerel GPU Whisper ile metne dönüştürür."""
        # 1. Sesi İndir
        audio_file = await asyncio.to_thread(self.download_audio_yt_dlp, video_id)
        if not audio_file or not os.path.exists(audio_file):
            return {
                "success": False,
                "error": "yt-dlp ile ses akışı indirilemedi.",
                "text": ""
            }

        # 2. Modeli Yükle & Transkribe Et
        model_pack = await asyncio.to_thread(self._load_model)
        if not model_pack:
            return {
                "success": False,
                "error": "Yerel Whisper kütüphanesi (faster-whisper veya whisper) bulunamadı.",
                "text": ""
            }

        engine_type, model = model_pack
        try:
            full_text = ""
            if engine_type == "faster_whisper":
                segments, info = model.transcribe(audio_file, language="tr", beam_size=5)
                full_text = " ".join([seg.text for seg in segments])
            elif engine_type == "openai_whisper":
                res = model.transcribe(audio_file, language="tr")
                full_text = res.get("text", "")

            # Temizlik: İndirilen büyük ses dosyasını diskte yer kaplamaması için silebiliriz
            try:
                os.remove(audio_file)
            except Exception:
                pass

            if full_text.strip():
                return {
                    "success": True,
                    "video_id": video_id,
                    "text": full_text.strip(),
                    "device": "cuda" if self.is_gpu_available else "cpu",
                    "engine": engine_type
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Transkripsiyon hatası: {str(e)}",
                "text": ""
            }

        return {"success": False, "error": "Bilinmeyen transkripsiyon hatası.", "text": ""}

whisper_transcriber = WhisperTranscriber()
