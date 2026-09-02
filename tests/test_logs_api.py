"""
KPSS Super-Brain: Logs API & Visual Dashboard Test Paketi
Kullanıcının talep ettiği kart şablonu, video linki, Qwen LLM çıkarımları,
denetçi denetimleri ve her sorguda alınan hata teşhislerini test eder.
"""
import pytest
from fastapi.testclient import TestClient
from api.server import app
from brain.database import db_session, initialize_database


@pytest.fixture(autouse=True)
def setup_test_db():
    initialize_database()
    # Test verisi ekle
    with db_session() as conn:
        cursor = conn.cursor()
        # 1. Video Queue
        cursor.execute("""
        INSERT OR REPLACE INTO video_queue (
            video_id, url, title, channel, teacher_name, lesson, topic,
            duration_seconds, status, priority, created_at, watched_at
        ) VALUES (
            'test_log_vid_1', 'https://www.youtube.com/watch?v=test_log_vid_1',
            'KPSS Coğrafya Türkiye İklimi Test Dersi', 'Benim Hocam',
            'Bayram Meral', 'COGRAFYA', 'Türkiye İklimi',
            1800, 'WATCHED', 10, '2099-01-01T00:00:00', '2099-01-01T00:30:00'
        )
        """)

        # 2. Transcript Provider Attempts (Hata ve Başarı kayıtları)
        cursor.execute("DELETE FROM transcript_provider_attempts WHERE video_id = 'test_log_vid_1'")
        cursor.execute("""
        INSERT INTO transcript_provider_attempts (
            video_id, provider, attempt_number, status, error_code, error_message, started_at, finished_at, duration_ms
        ) VALUES 
        ('test_log_vid_1', 'YOUTUBE_CAPTIONS', 1, 'CAPTION_FETCH_FAILED', '429', 'YouTube blocking IP (HTTP 429)', '2026-08-27T12:00:01', '2026-08-27T12:00:03', 2000),
        ('test_log_vid_1', 'YTDLP_SUBTITLES', 2, 'YTDLP_BLOCKED', 'BLOCKED', 'Bot challenge requested', '2026-08-27T12:00:04', '2026-08-27T12:00:06', 2000),
        ('test_log_vid_1', 'LOCAL_WHISPER', 3, 'TRANSCRIPT_ACQUIRED', NULL, NULL, '2026-08-27T12:00:07', '2026-08-27T12:00:12', 5000)
        """)

        # 3. Knowledge Records (Qwen LLM Çıkarımları)
        cursor.execute("""
        INSERT OR REPLACE INTO knowledge_records (
            record_id, text, record_type, lesson, topic, subtopic,
            confidence, first_learned, last_reinforced
        ) VALUES 
        ('rec_fact_1', 'Türkiye kıyılarında Akdeniz iklimi görülür.', 'FACT', 'COGRAFYA', 'Türkiye İklimi', 'İklim Tipleri', 0.95, '2026-08-27T12:30:00', '2026-08-27T12:30:00'),
        ('rec_mnem_1', 'KAYIP SAKAL: Rüzgarların yön şifresi', 'MNEMONIC', 'COGRAFYA', 'Türkiye İklimi', 'Rüzgarlar', 0.98, '2026-08-27T12:30:00', '2026-08-27T12:30:00'),
        ('rec_trap_1', 'Mikroklima alanları ile makroklima karıştırılmamalıdır.', 'TRAP', 'COGRAFYA', 'Türkiye İklimi', 'Tuzaklar', 0.90, '2026-08-27T12:30:00', '2026-08-27T12:30:00')
        """)

        # 4. Atomic Claims (Denetçi Denetimleri)
        cursor.execute("""
        INSERT OR REPLACE INTO atomic_claims (
            claim_id, text, lesson, topic, subtopic, claim_type,
            confidence, verification_status, provenance_hash, created_at
        ) VALUES 
        ('claim_01', 'Akdeniz ikliminde yazlar sıcak ve kuraktır.', 'COGRAFYA', 'Türkiye İklimi', 'Genel', 'FACT', 0.95, 'VERIFIED', 'hash_01', '2026-08-27T12:30:00'),
        ('claim_02', 'Rize mikroklima sahasında turunçgil yetişir.', 'COGRAFYA', 'Türkiye İklimi', 'Özel', 'FACT', 0.90, 'PENDING', 'hash_02', '2026-08-27T12:30:00')
        """)


def test_logs_pipeline_api():
    """Pipeline günlük kartları uç noktasını doğrula"""
    client = TestClient(app)
    response = client.get("/api/logs/pipeline")
    assert response.status_code == 200
    data = response.json()
    assert "cards" in data
    assert len(data["cards"]) >= 1

    card = next(c for c in data["cards"] if c["video_id"] == "test_log_vid_1")
    assert card["title"] == "KPSS Coğrafya Türkiye İklimi Test Dersi"
    assert "youtube.com/watch?v=test_log_vid_1" in card["video_url"]
    
    # Qwen LLM çıkarımları
    assert card["inferences_summary"]["facts_count"] >= 1
    assert card["inferences_summary"]["mnemonics_count"] >= 1
    assert card["inferences_summary"]["traps_count"] >= 1
    assert card["inferences_summary"]["total_count"] >= 3

    # Denetçi özeti
    assert card["audits_summary"]["verified_claims"] >= 1
    assert card["audits_summary"]["pending_claims"] >= 1

    # Her sorguda alınan hatalar
    assert len(card["attempts"]) == 3
    providers = [a["provider"] for a in card["attempts"]]
    assert "YOUTUBE_CAPTIONS" in providers
    assert "YTDLP_SUBTITLES" in providers
    assert "LOCAL_WHISPER" in providers


def test_logs_video_details_api():
    """Video detayları ve Qwen LLM çıkarımları modal uç noktasını doğrula"""
    client = TestClient(app)
    response = client.get("/api/logs/video/test_log_vid_1/details")
    assert response.status_code == 200
    data = response.json()
    assert data["video"]["video_id"] == "test_log_vid_1"
    assert data["records_count"] >= 3
    texts = [r["text"] for r in data["records"]]
    assert any("KAYIP SAKAL" in t for t in texts)


def test_logs_video_audits_api():
    """Denetçi denetim raporu modal uç noktasını doğrula"""
    client = TestClient(app)
    response = client.get("/api/logs/video/test_log_vid_1/audits")
    assert response.status_code == 200
    data = response.json()
    assert data["claims_count"] >= 2
    statuses = [c["verification_status"] for c in data["claims"]]
    assert "VERIFIED" in statuses
    assert "PENDING" in statuses
    assert len(data["firewall_rules"]) >= 3


def test_logs_stats_api():
    """Log istatistikleri özet uç noktasını doğrula"""
    client = TestClient(app)
    response = client.get("/api/logs/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_videos"] >= 1
    assert data["watched_videos"] >= 1
    assert data["total_attempts"] >= 3


def test_serve_logs_html_page():
    """/logs görsel HTML sayfasının başarıyla render edildiğini doğrula"""
    client = TestClient(app)
    response = client.get("/logs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Openmanus - İşçi Bir adet" in response.text
    assert "Qwen LLM" in response.text or "Qwen llm" in response.text
    assert "blue-link" in response.text


def test_serve_root_html_page():
    """/ ana kontrol paneli HTML sayfasının başarıyla render edildiğini doğrula"""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "PROMIUS" in response.text
    assert "KPSS SUPER-BRAIN" in response.text
    assert "Saha Günlüğü" in response.text

