"""
KPSS Super-Brain: Otonom Zeka Yapılandırma Modülü (Master Config)
"""
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any

BASE_DIR = Path(__file__).resolve().parent

class SuperBrainConfig(BaseModel):
    # Ollama Local LLM Yapılandırması
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    
    # Model Seçimleri
    MAIN_MODEL: str = os.getenv("SUPER_BRAIN_MAIN_MODEL", "qwen2.5:14b")
    REASONING_MODEL: str = os.getenv("SUPER_BRAIN_REASONING_MODEL", "deepseek-r1:8b")
    VISION_MODEL: str = os.getenv("SUPER_BRAIN_VISION_MODEL", "llava")
    EMBEDDING_MODEL: str = os.getenv("SUPER_BRAIN_EMBEDDING_MODEL", "all-minilm")
    FALLBACK_MODEL: str = "qwen2.5:7b"
    
    # Sıcaklık Parametreleri
    FACT_TEMPERATURE: float = 0.1
    CREATIVE_TEMPERATURE: float = 0.6
    STRICT_TEMPERATURE: float = 0.0

    # Z3 SMT Formal Logic Kısıtları
    Z3_TIMEOUT: int = 500  # milisaniye cinsinden Z3 timeout sınırı
    
    # Dizin Yolları
    BASE_DIR: Path = BASE_DIR
    CANONICAL_FACTS_DIR: Path = BASE_DIR / "canonical_facts"
    DATA_DIR: Path = BASE_DIR / "data"
    GROUND_TRUTH_DIR: Path = BASE_DIR / "data" / "ground_truth"
    OUTPUTS_DIR: Path = BASE_DIR / "outputs"
    EXPORTS_DIR: Path = BASE_DIR / "data" / "exports"
    PAST_EXAMS_DIR: Path = BASE_DIR / "data" / "past_exams"
    TRANSCRIPTS_DIR: Path = BASE_DIR / "data" / "transcripts"
    BRAIN_DB_FILE: Path = BASE_DIR / "data" / "brain.db"
    CHROMADB_DIR: Path = BASE_DIR / "data" / "chroma_db"
    KNOWLEDGE_GRAPH_FILE: Path = BASE_DIR / "data" / "knowledge_graph.json"
    EPISODIC_LOG_FILE: Path = BASE_DIR / "data" / "episodic_memory.json"
    TASK_DB_FILE: Path = BASE_DIR / "data" / "tasks.db"
    ENGINE_STATE_DB_FILE: Path = BASE_DIR / "data" / "engine_state.db"
    AUDIO_DOWNLOAD_DIR: Path = BASE_DIR / "data" / "audio_downloads"
    PDF_UPLOADS_DIR: Path = BASE_DIR / "data" / "uploads"
    
    # Proxy & Network Resilience
    PROXY_ROTATION_ENABLED: bool = True
    MAX_TRANSCRIPT_RPM: int = 5
    BACKOFF_BASE_SECONDS: float = 3.0
    
    # GPU / Whisper STT Settings
    WHISPER_ENABLED: bool = True
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") != "" else "auto")
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")
    
    # State Persistence & Checkpointing
    AUTO_CHECKPOINT_INTERVAL_SEC: int = 30
    
    # 7/24 Otonom Öğrenme Parametreleri
    AUTONOMOUS_CYCLE_INTERVAL_SECONDS: int = 1800
    VIDEO_DIGEST_SLEEP_MIN_SEC: int = 15    # Video arası nefes alma / rate limit koruma (sn)
    VIDEO_DIGEST_SLEEP_MAX_SEC: int = 45
    CHANNEL_DISCOVERY_INTERVAL_SEC: int = 21600 # 6 saatte bir yeni videoları ve oynatma listelerini tara
    CONSOLIDATION_INTERVAL_SEC: int = 1800      # 30 dakikada bir derin muhakeme & JSON export
    SELF_EVAL_INTERVAL_SEC: int = 3600          # 1 saatte bir müfredat derinlik analizi
    MIN_VIDEOS_PER_TOPIC: int = 4               # Her resmi konu için minimum farklı video tüketim şartı
    
    # Hedef KPSS YouTube Kanalları (Manus Tarzı Playlist ve Video Keşfi İçin)
    TARGET_KPSS_CHANNELS: List[Dict[str, Any]] = [
        {"name": "Benim Hocam", "handle": "@BenimHocam", "url": "https://www.youtube.com/@BenimHocam", "lessons": ["TARIH", "COGRAFYA", "VATANDASLIK", "TURKCE", "MATEMATIK"]},
        {"name": "İsem TV", "handle": "@isemtv", "url": "https://www.youtube.com/@isemtv", "lessons": ["TARIH", "COGRAFYA", "VATANDASLIK", "TURKCE", "MATEMATIK"]},
        {"name": "İndeks Akademi", "handle": "@indeksakademi", "url": "https://www.youtube.com/@indeksakademi", "lessons": ["TARIH", "COGRAFYA", "VATANDASLIK", "TURKCE", "MATEMATIK"]},
        {"name": "Hoca Webde", "handle": "@hocawebde", "url": "https://www.youtube.com/@hocawebde", "lessons": ["COGRAFYA", "TARIH", "VATANDASLIK"]},
        {"name": "Pegem Akademi", "handle": "@PegemAkademi", "url": "https://www.youtube.com/@PegemAkademi", "lessons": ["TARIH", "COGRAFYA", "VATANDASLIK", "TURKCE", "MATEMATIK"]},
        {"name": "Kadir Koç Akademi", "handle": "@kadirkoctarih", "url": "https://www.youtube.com/@kadirkoctarih", "lessons": ["TARIH"]},
        {"name": "Mehmet Eğit", "handle": "@mehmetegit", "url": "https://www.youtube.com/@mehmetegit", "lessons": ["COGRAFYA"]}
    ]

    # Hedef Popüler KPSS Eğitmenleri & Ders Dağılımı
    TARGET_TEACHERS: List[Dict[str, Any]] = [
        # --- TARİH ---
        {"name": "Ramazan Yetgin", "channel": "Benim Hocam", "lesson": "TARIH", "search_query": "Ramazan Yetgin KPSS Tarih 2026", "channel_handle": "@BenimHocam"},
        {"name": "Mehmet Celal Özyıldız", "channel": "Retro Yayıncılık", "lesson": "TARIH", "search_query": "Mehmet Celal Özyıldız KPSS Tarih", "channel_handle": "@retroyayincilik"},
        {"name": "Aydın Yüce", "channel": "İsem TV", "lesson": "TARIH", "search_query": "Aydın Yüce KPSS Tarih 2026", "channel_handle": "@isemtv"},
        {"name": "Kadir Koç", "channel": "Kadir Koç Akademi", "lesson": "TARIH", "search_query": "Kadir Koç KPSS Tarih", "channel_handle": "@kadirkoctarih"},
        {"name": "Sadettin Akyol", "channel": "İndeks Akademi", "lesson": "TARIH", "search_query": "Sadettin Akyol KPSS Tarih", "channel_handle": "@indeksakademi"},
        
        # --- COĞRAFYA ---
        {"name": "Bayram Meral", "channel": "Benim Hocam", "lesson": "COGRAFYA", "search_query": "Bayram Meral KPSS Coğrafya 2026", "channel_handle": "@BenimHocam"},
        {"name": "Engin Eraydın", "channel": "Hoca Webde", "lesson": "COGRAFYA", "search_query": "Engin Eraydın KPSS Coğrafya", "channel_handle": "@hocawebde"},
        {"name": "Mehmet Eğit", "channel": "Mehmet Eğit", "lesson": "COGRAFYA", "search_query": "Mehmet Eğit KPSS Coğrafya Hafıza Teknikleri", "channel_handle": "@mehmetegit"},
        {"name": "Hakan Bileyen", "channel": "İsem TV", "lesson": "COGRAFYA", "search_query": "Hakan Bileyen KPSS Coğrafya", "channel_handle": "@isemtv"},
        {"name": "Ali Can Demirci", "channel": "İndeks Akademi", "lesson": "COGRAFYA", "search_query": "Ali Can Demirci KPSS Coğrafya", "channel_handle": "@indeksakademi"},

        # --- VATANDAŞLIK & GÜNCEL ---
        {"name": "Emrah Vahap Özkaraca", "channel": "İndeks Akademi", "lesson": "VATANDASLIK", "search_query": "Emrah Vahap Özkaraca KPSS Vatandaşlık 2026", "channel_handle": "@indeksakademi"},
        {"name": "Erdal Kesekler", "channel": "Benim Hocam", "lesson": "VATANDASLIK", "search_query": "Erdal Kesekler KPSS Vatandaşlık", "channel_handle": "@BenimHocam"},
        {"name": "Esra Özkan Karaoğlu", "channel": "İsem TV", "lesson": "VATANDASLIK", "search_query": "Esra Özkan Karaoğlu KPSS Vatandaşlık", "channel_handle": "@isemtv"},
        {"name": "Ali Koç", "channel": "Hoca Webde", "lesson": "VATANDASLIK", "search_query": "Ali Koç KPSS Vatandaşlık", "channel_handle": "@hocawebde"},

        # --- TÜRKÇE ---
        {"name": "Öznur Saat Yıldırım", "channel": "İsem TV", "lesson": "TURKCE", "search_query": "Öznur Saat Yıldırım KPSS Türkçe Dil Bilgisi", "channel_handle": "@isemtv"},
        {"name": "Aker Kartal", "channel": "Hoca Webde", "lesson": "TURKCE", "search_query": "Aker Kartal KPSS Türkçe", "channel_handle": "@hocawebde"},
        {"name": "Yelda Ünal", "channel": "Benim Hocam", "lesson": "TURKCE", "search_query": "Yelda Ünal KPSS Türkçe", "channel_handle": "@BenimHocam"},
        {"name": "Rüştü Bayındır", "channel": "Rüştü Hoca ile Türkçe", "lesson": "TURKCE", "search_query": "Rüştü Hoca KPSS Türkçe Paragraf Taktikleri", "channel_handle": "@rustuhocaileturkce"},

        # --- MATEMATİK & GEOMETRİ ---
        {"name": "İlyas Güneş", "channel": "Benim Hocam", "lesson": "MATEMATIK", "search_query": "İlyas Güneş KPSS Matematik 2026", "channel_handle": "@BenimHocam"},
        {"name": "Mehmet Bilge Yıldız", "channel": "İsem TV", "lesson": "MATEMATIK", "search_query": "Mehmet Bilge Yıldız KPSS Matematik", "channel_handle": "@isemtv"},
        {"name": "Görkem Şahin", "channel": "Benim Hocam", "lesson": "MATEMATIK", "search_query": "Görkem Şahin KPSS Matematik", "channel_handle": "@BenimHocam"}
    ]

super_brain_config = SuperBrainConfig()

# Otomatik Klasörleri Oluştur
os.makedirs(super_brain_config.DATA_DIR, exist_ok=True)
os.makedirs(super_brain_config.GROUND_TRUTH_DIR, exist_ok=True)
os.makedirs(super_brain_config.OUTPUTS_DIR, exist_ok=True)
os.makedirs(super_brain_config.EXPORTS_DIR, exist_ok=True)
os.makedirs(super_brain_config.PAST_EXAMS_DIR, exist_ok=True)
os.makedirs(super_brain_config.TRANSCRIPTS_DIR, exist_ok=True)
os.makedirs(super_brain_config.CHROMADB_DIR, exist_ok=True)
os.makedirs(super_brain_config.AUDIO_DOWNLOAD_DIR, exist_ok=True)
os.makedirs(super_brain_config.PDF_UPLOADS_DIR, exist_ok=True)
