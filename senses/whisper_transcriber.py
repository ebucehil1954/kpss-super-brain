"""
KPSS Super-Brain: GPU Hızlandırmalı Yerel Whisper Ses Transkripsiyon Motoru (Whisper Transcriber v4)
YouTube altyazısı bulunmayan videoların sesini yt-dlp ile indirip yerel Whisper modeli ile
zaman damgalı segmentlere (`start_seconds`, `end_seconds`, `text`) dönüştürür.
"""
from __future__ import annotations

import os
import subprocess
import shutil
import asyncio
import hashlib
from typing import Dict, Any, List, Optional
from config import super_brain_config

class WhisperTranscriber:
    def __init__(self):
        self.audio_dir = str(super_brain_config.AUDIO_DOWNLOAD_DIR)
        self.whisper_model = None
        self.is_gpu_available = False
        self._check_hardware()

    def _check_hardware(self):
        """[PHASE 14] CUDA GPU desteğini ve donanımı gerçek bellek testi ile kontrol eder."""
        try:
            import torch
            if torch.cuda.is_available():
                try:
                    # Sanity check: CUDA sürücü veya bellek uyumsuzluğunu doğrula
                    test_t = torch.zeros((1,), device="cuda")
                    del test_t
                    self.is_gpu_available = True
                except Exception:
                    self.is_gpu_available = False
            else:
                self.is_gpu_available = False
        except ImportError:
            self.is_gpu_available = False

    def _load_model(self):
        """[PHASE 14] Whisper modelini GPU/CPU üzerine güvenle yükler (CUDA hata verirse CPU fallback)."""
        if self.whisper_model is not None:
            return self.whisper_model

        model_size = super_brain_config.WHISPER_MODEL_SIZE

        # 1. Faster-Whisper denemesi (GPU -> CPU Fallback)
        try:
            from faster_whisper import WhisperModel
            if self.is_gpu_available:
                try:
                    self.whisper_model = ("faster_whisper", WhisperModel(model_size, device="cuda", compute_type="float16"))
                    return self.whisper_model
                except Exception:
                    # CUDA başarısız olursa derhal CPU'ya düş
                    self.is_gpu_available = False
            try:
                self.whisper_model = ("faster_whisper", WhisperModel(model_size, device="cpu", compute_type="int8"))
                return self.whisper_model
            except Exception:
                self.whisper_model = ("faster_whisper", WhisperModel(model_size, device="cpu", compute_type="float32"))
                return self.whisper_model
        except Exception:
            pass

        # 2. OpenAI Whisper denemesi (GPU -> CPU Fallback)
        try:
            import whisper
            device = "cuda" if self.is_gpu_available else "cpu"
            try:
                self.whisper_model = ("openai_whisper", whisper.load_model(model_size, device=device))
                return self.whisper_model
            except Exception:
                self.is_gpu_available = False
                self.whisper_model = ("openai_whisper", whisper.load_model(model_size, device="cpu"))
                return self.whisper_model
        except Exception:
            pass

        return None

    @staticmethod
    def chunk_audio_duration(total_duration_seconds: float, max_chunk_seconds: float = 600.0) -> List[Tuple[float, float]]:
        """[PHASE 14] Uzun ses dosyalarını VRAM ve bellek taşmasını önlemek için güvenli dilimlere böler."""
        if total_duration_seconds <= 0:
            return []
        chunks = []
        start = 0.0
        while start < total_duration_seconds:
            end = min(total_duration_seconds, start + max_chunk_seconds)
            chunks.append((round(start, 2), round(end, 2)))
            start = end
        return chunks

    @staticmethod
    def classify_whisper_error(error_str: str) -> str:
        """[PHASE 14] Whisper ve ses işleme hatalarını sınıflandırır."""
        err = (error_str or "").lower()
        if "out of memory" in err or "cuda oom" in err or "cuda error" in err:
            return "CUDA_OOM_FALLBACK_REQUIRED"
        if "download" in err or "404" in err or "yt-dlp" in err:
            return "AUDIO_DOWNLOAD_FAILED"
        if "corrupt" in err or "invalid data" in err or "ffmpeg" in err:
            return "CORRUPTED_AUDIO"
        return "GENERIC_AUDIO_FAILURE"

    def download_audio_yt_dlp(self, video_id: str) -> Optional[str]:
        """yt-dlp kullanarak YouTube videosunun ses akışını indirir."""
        os.makedirs(self.audio_dir, exist_ok=True)
        output_template = os.path.join(self.audio_dir, f"{video_id}.%(ext)s")
        target_audio_path = os.path.join(self.audio_dir, f"{video_id}.m4a")

        # Mevcut tamamlanmış dosyayı kontrol et
        if os.path.exists(target_audio_path):
            return target_audio_path

        if os.path.exists(self.audio_dir):
            for fname in os.listdir(self.audio_dir):
                if fname.startswith(video_id) and not fname.endswith(".part"):
                    return os.path.join(self.audio_dir, fname)

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        import sys
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--js-runtimes", "node",
            "--extractor-args", "youtube:player_client=android",
            "-f", "ba[ext=m4a]/18/best",
            "--no-playlist",
            "--socket-timeout", "20",
            "--no-warnings",
            "--max-filesize", "650M",
            "-o", output_template,
        ]

        # Çerez Desteği (Bot ve IP Engeli Savunması)
        if super_brain_config.youtube_cookies_available:
            cmd.extend(["--cookies", str(super_brain_config.YOUTUBE_COOKIES_FILE)])
        elif super_brain_config.YOUTUBE_COOKIES_BROWSER:
            cmd.extend(["--cookies-from-browser", super_brain_config.YOUTUBE_COOKIES_BROWSER])

        cmd.append(video_url)

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=240)
            if os.path.exists(target_audio_path):
                return target_audio_path

            if os.path.exists(self.audio_dir):
                for fname in os.listdir(self.audio_dir):
                    if fname.startswith(video_id) and not fname.endswith(".part"):
                        return os.path.join(self.audio_dir, fname)
        except Exception as e:
            print(f"⚠️ [WHISPER AUDIO DOWNLOAD] Ses indirme hatası: {e}")

        return None

    async def transcribe_video(self, video_id: str) -> Dict[str, Any]:
        """Videoyu indirir ve yerel GPU Whisper ile zaman damgalı segmentlerle metne dönüştürür."""
        # 1. Sesi İndir
        audio_file = await asyncio.to_thread(self.download_audio_yt_dlp, video_id)
        if not audio_file or not os.path.exists(audio_file):
            return {
                "success": False,
                "error": "yt-dlp ile ses akışı indirilemedi.",
                "text": "",
                "segments": []
            }

        # 2. Modeli Yükle & Transkribe Et
        model_pack = await asyncio.to_thread(self._load_model)
        if not model_pack:
            return {
                "success": False,
                "error": "Yerel Whisper kütüphanesi (faster-whisper veya whisper) bulunamadı.",
                "text": "",
                "segments": []
            }

        engine_type, model = model_pack
        try:
            full_text_parts = []
            segments_list = []

            if engine_type == "faster_whisper":
                segments, info = model.transcribe(audio_file, language="tr", beam_size=5)
                for idx, seg in enumerate(segments):
                    s_txt = seg.text.strip()
                    if s_txt:
                        start_s = round(float(seg.start), 2)
                        end_s = round(float(seg.end), 2)
                        seg_id = f"whisper_seg_{video_id}_{idx}"
                        seg_hash = hashlib.sha256(f"{video_id}:{start_s}:{end_s}:{s_txt}".encode()).hexdigest()[:16]
                        full_text_parts.append(s_txt)
                        segments_list.append({
                            "segment_id": seg_id,
                            "video_id": video_id,
                            "start_seconds": start_s,
                            "end_seconds": end_s,
                            "text": s_txt,
                            "segment_hash": seg_hash
                        })
            elif engine_type == "openai_whisper":
                res = model.transcribe(audio_file, language="tr")
                for idx, seg in enumerate(res.get("segments", [])):
                    s_txt = seg.get("text", "").strip()
                    if s_txt:
                        start_s = round(float(seg.get("start", 0.0)), 2)
                        end_s = round(float(seg.get("end", 0.0)), 2)
                        seg_id = f"whisper_seg_{video_id}_{idx}"
                        seg_hash = hashlib.sha256(f"{video_id}:{start_s}:{end_s}:{s_txt}".encode()).hexdigest()[:16]
                        full_text_parts.append(s_txt)
                        segments_list.append({
                            "segment_id": seg_id,
                            "video_id": video_id,
                            "start_seconds": start_s,
                            "end_seconds": end_s,
                            "text": s_txt,
                            "segment_hash": seg_hash
                        })

            full_text = " ".join(full_text_parts)

            # Temizlik
            try:
                os.remove(audio_file)
            except Exception:
                pass

            if full_text.strip():
                return {
                    "success": True,
                    "video_id": video_id,
                    "text": full_text.strip(),
                    "segments": segments_list,
                    "device": "cuda" if self.is_gpu_available else "cpu",
                    "engine": engine_type
                }
        except Exception as e:
            err_class = self.classify_whisper_error(str(e))
            if err_class == "CUDA_OOM_FALLBACK_REQUIRED" and self.is_gpu_available:
                self.is_gpu_available = False
                self.whisper_model = None
                return await self.transcribe_video(video_id)
            return {
                "success": False,
                "error": f"Transkripsiyon hatası [{err_class}]: {str(e)}",
                "error_class": err_class,
                "text": "",
                "segments": []
            }

        return {"success": False, "error": "Bilinmeyen transkripsiyon hatası.", "text": "", "segments": []}

whisper_transcriber = WhisperTranscriber()
