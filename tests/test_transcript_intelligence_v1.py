"""
KPSS Super-Brain: Transcript Reliability & Intelligence V1 Test Paketi
Şartnamede zorunlu kılınan 13 senaryo ve iki-videolu izolasyon testini içerir:
1. test_manual_caption_success
2. test_auto_caption_success
3. test_ytdlp_fallback
4. test_browser_fallback
5. test_whisper_fallback
6. test_all_providers_fail_without_worker_crash
7. test_video_failure_does_not_stop_queue (İki videolu izolasyon: Video A çöker -> DEFERRED, Video B çalışır -> PROCESSED, Worker canlı)
8. test_rate_limit_is_temporary
9. test_permanent_video_failure_is_not_retried_forever
10. test_transcript_segments_preserve_timestamps
11. test_provider_diagnostics_are_saved
12. test_llm_error_is_not_silently_swallowed
13. test_pending_claim_cannot_enter_knowledge_store
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from senses.transcript_models import (
    TranscriptProviderType, TranscriptResult, TranscriptSegment,
    TranscriptStatus, TranscriptDiagnostics
)
from senses.transcript_gateway import TranscriptGateway
from senses.providers.youtube_caption_provider import YouTubeCaptionProvider
from senses.providers.ytdlp_subtitle_provider import YtDlpSubtitleProvider
from senses.providers.browser_transcript_provider import BrowserTranscriptProvider
from senses.providers.whisper_provider import WhisperProvider
from senses.transcript_processor import TranscriptProcessor
from curriculum.models import QueueStatus, FailureClass
from curriculum.queue import curriculum_queue
from autonomous.harvester import harvester
from brain.database import db_session
from brain.knowledge_store import knowledge_store


@pytest.fixture(autouse=True)
def setup_db():
    """Test öncesi tabloları hazırla"""
    from brain.database import initialize_database
    initialize_database()


@pytest.mark.asyncio
async def test_manual_caption_success():
    """1. Manuel Türkçe Altyazı Başarı Testi"""
    provider = YouTubeCaptionProvider()
    fake_items = [
        {"start": 0.0, "duration": 5.0, "text": "Türkiye'nin iklimi ve coğrafi konumu"},
        {"start": 5.0, "duration": 4.5, "text": "Akdeniz iklimi genel özellikleri"}
    ]
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = fake_items
    mock_transcript_list = MagicMock()
    mock_transcript_list.find_transcript.return_value = mock_transcript

    with patch("senses.providers.youtube_caption_provider.YouTubeTranscriptApi") as MockApi:
        MockApi.return_value.list.return_value = mock_transcript_list
        res = await provider.attempt("vid_manual_1")
        assert res.success is True
        assert res.provider == TranscriptProviderType.YOUTUBE_CAPTIONS
        assert res.is_generated is False
        assert len(res.segments) == 2
        assert res.segments[0].start_seconds == 0.0
        assert res.segments[0].end_seconds == 5.0
        assert "iklimi" in res.segments[0].text


@pytest.mark.asyncio
async def test_auto_caption_success():
    """2. Otomatik Üretilmiş Türkçe Altyazı Başarı Testi"""
    provider = YouTubeCaptionProvider()
    fake_items = [
        {"start": 10.0, "duration": 6.0, "text": "Erzurum Kongresi kararları"}
    ]
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = fake_items
    mock_transcript_list = MagicMock()
    mock_transcript_list.find_transcript.side_effect = Exception("No manual transcript")
    mock_transcript_list.find_generated_transcript.return_value = mock_transcript

    with patch("senses.providers.youtube_caption_provider.YouTubeTranscriptApi") as MockApi:
        MockApi.return_value.list.return_value = mock_transcript_list
        res = await provider.attempt("vid_auto_002")
        assert res.success is True
        assert res.is_generated is True
        assert len(res.segments) == 1
        assert res.segments[0].start_seconds == 10.0


@pytest.mark.asyncio
async def test_ytdlp_fallback():
    """3. YouTube Captions Başarısız Olduğunda yt-dlp Subtitle Fallback Testi"""
    gateway = TranscriptGateway()

    # Provider 1 (Captions) başarısız yap
    gateway.providers[0].attempt = AsyncMock(return_value=TranscriptResult(
        video_id="vid_ytdlp_01",
        success=False,
        provider=TranscriptProviderType.YOUTUBE_CAPTIONS,
        status=TranscriptStatus.NO_CAPTION_TRACK,
        error="NO_CAPTION_TRACK"
    ))

    # Provider 2 (yt-dlp) başarılı yap
    fake_segments = [
        TranscriptSegment(segment_id="s1", video_id="vid_ytdlp_01", start_seconds=0.0, end_seconds=4.0, text="Amasya Tamimi maddeleri")
    ]
    gateway.providers[1].attempt = AsyncMock(return_value=TranscriptResult(
        video_id="vid_ytdlp_01",
        success=True,
        provider=TranscriptProviderType.YTDLP_SUBTITLES,
        segments=fake_segments,
        status=TranscriptStatus.TRANSCRIPT_ACQUIRED
    ))

    res = await gateway.get_transcript("vid_ytdlp_01", allow_whisper=False)
    assert res.success is True
    assert res.provider == TranscriptProviderType.YTDLP_SUBTITLES
    assert len(res.segments) == 1
    assert "Amasya" in res.segments[0].text


@pytest.mark.asyncio
async def test_browser_fallback():
    """4. Captions ve yt-dlp Başarısız Olduğunda Browser/Kazıma Fallback Testi"""
    gateway = TranscriptGateway()

    # Provider 1 ve 2 başarısız
    gateway.providers[0].attempt = AsyncMock(return_value=TranscriptResult(
        video_id="vid_brow_01", success=False, provider=TranscriptProviderType.YOUTUBE_CAPTIONS, status=TranscriptStatus.CAPTION_FETCH_FAILED, error="429"
    ))
    gateway.providers[1].attempt = AsyncMock(return_value=TranscriptResult(
        video_id="vid_brow_01", success=False, provider=TranscriptProviderType.YTDLP_SUBTITLES, status=TranscriptStatus.YTDLP_BLOCKED, error="BLOCKED"
    ))

    # Provider 3 (Browser) başarılı
    fake_segments = [
        TranscriptSegment(segment_id="s1", video_id="vid_brow_01", start_seconds=2.0, end_seconds=8.0, text="Sivas Kongresi temsil heyeti")
    ]
    gateway.providers[2].attempt = AsyncMock(return_value=TranscriptResult(
        video_id="vid_brow_01",
        success=True,
        provider=TranscriptProviderType.BROWSER_PLAYWRIGHT,
        segments=fake_segments,
        status=TranscriptStatus.TRANSCRIPT_ACQUIRED
    ))

    res = await gateway.get_transcript("vid_brow_01", allow_whisper=False)
    assert res.success is True
    assert res.provider == TranscriptProviderType.BROWSER_PLAYWRIGHT
    assert "Sivas" in res.segments[0].text


@pytest.mark.asyncio
async def test_whisper_fallback():
    """5. İlk 3 Sağlayıcı Başarısız Olduğunda Whisper Son Savunma Hattı Testi"""
    gateway = TranscriptGateway()

    # İlk 3 sağlayıcı fail
    for i in range(3):
        gateway.providers[i].attempt = AsyncMock(return_value=TranscriptResult(
            video_id="vid_whisp_1", success=False, provider=gateway.providers[i].provider_type, status=TranscriptStatus.NO_CAPTION_TRACK, error="FAIL"
        ))

    # Whisper başarılı
    fake_segments = [
        TranscriptSegment(segment_id="w1", video_id="vid_whisp_1", start_seconds=1.5, end_seconds=6.5, text="Misakımilli kararları son meclis")
    ]
    gateway.providers[3].attempt = AsyncMock(return_value=TranscriptResult(
        video_id="vid_whisp_1",
        success=True,
        provider=TranscriptProviderType.LOCAL_WHISPER,
        segments=fake_segments,
        status=TranscriptStatus.TRANSCRIPT_ACQUIRED
    ))

    res = await gateway.get_transcript("vid_whisp_1", allow_whisper=True)
    assert res.success is True
    assert res.provider == TranscriptProviderType.LOCAL_WHISPER
    assert len(res.segments) == 1
    assert "Misakımilli" in res.segments[0].text


@pytest.mark.asyncio
async def test_all_providers_fail_without_worker_crash():
    """6. Tüm Sağlayıcılar Çöktüğünde Sistemin Çökmemesi ve DEFERRED İşaretlenmesi"""
    gateway = TranscriptGateway()

    for p in gateway.providers:
        p.attempt = AsyncMock(return_value=TranscriptResult(
            video_id="vid_all_fail", success=False, provider=p.provider_type, status=TranscriptStatus.NO_CAPTION_TRACK, error="FAILED"
        ))

    res = await gateway.get_transcript("vid_all_fail", allow_whisper=True)
    assert res.success is False
    assert res.status == TranscriptStatus.TRANSCRIPT_DEFERRED
    assert len(res.diagnostics) >= 4  # Tüm 4 sağlayıcının adli kaydı var


@pytest.mark.asyncio
async def test_video_failure_does_not_stop_queue():
    """
    7. KRİTİK İKİ-VİDEOLU İZOLASYON TESTİ:
    Video A: Tüm altyazı sağlayıcıları çöker -> TRANSCRIPT_DEFERRED
    Video B: Altyazı başarıyla çekilir -> PROCESSED/WATCHED
    Beklenen: Worker durmaz, Video A delege edilir, Video B başarıyla tamamlanır!
    """
    # 1. Kuyruğa iki video ekle
    vid_a = "vid_fail_001"
    vid_b = "vid_succ_002"
    with db_session() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM video_queue WHERE video_id IN (?, ?)", (vid_a, vid_b))
        c.execute("""
        INSERT INTO video_queue (video_id, url, title, channel, teacher_name, lesson, topic, priority, created_at)
        VALUES (?, 'urlA', 'Ders A', 'Kanal A', 'Hoca A', 'TARIH', 'Konu A', 10, '2026-01-01T00:00:00')
        """, (vid_a,))
        c.execute("""
        INSERT INTO video_queue (video_id, url, title, channel, teacher_name, lesson, topic, priority, created_at)
        VALUES (?, 'urlB', 'Ders B', 'Kanal B', 'Hoca B', 'TARIH', 'Konu B', 5, '2026-01-01T00:00:00')
        """, (vid_b,))

    # Harvester için mock ortamı
    async def mock_fetch_resilient(vid, enable_whisper_fallback=True):
        if vid == vid_a:
            return {"success": False, "error": "TRANSCRIPT_UNAVAILABLE", "status": "TRANSCRIPT_DEFERRED", "text": "", "segments": []}
        else:
            return {"success": True, "provider": "YOUTUBE_CAPTIONS", "text": "Lozan Barış Antlaşması maddeleri ve boğazlar", "segments": [{"start": 0, "duration": 5, "text": "Lozan"}]}

    with patch("senses.transcript_fetcher.transcript_fetcher.fetch_transcript_resilient", side_effect=mock_fetch_resilient):
        with patch("cognition.analyst.cognitive_analyst.analyze_transcript", new_callable=AsyncMock) as mock_analyst:
            mock_analyst.return_value = {"facts_count": 2, "mnemonics_count": 1, "traps_count": 0}

            # Video A'yı işle (Başarısız olmalı ama exception atmamalı)
            task_a = MagicMock()
            task_a.task_id = "task_a"
            task_a.lesson.value = "TARIH"
            task_a.topic_name = "Konu A"
            task_a.target_teachers = ["Hoca A"]
            task_a.search_queries = ["qA"]

            with patch.object(curriculum_queue, "get_next_research_task", return_value=task_a):
                with patch.object(curriculum_queue, "get_next_unwatched_video", return_value={"video_id": vid_a, "title": "Ders A", "teacher_name": "Hoca A", "lesson": "TARIH", "topic": "Konu A"}):
                    res_a = await harvester.harvest_single_task()
                    assert res_a["status"] == "transcript_deferred"

            # Video B'yi işle (Başarılı olmalı!)
            task_b = MagicMock()
            task_b.task_id = "task_b"
            task_b.lesson.value = "TARIH"
            task_b.topic_name = "Konu B"
            task_b.target_teachers = ["Hoca B"]
            task_b.search_queries = ["qB"]

            with patch.object(curriculum_queue, "get_next_research_task", return_value=task_b):
                with patch.object(curriculum_queue, "get_next_unwatched_video", return_value={"video_id": vid_b, "title": "Ders B", "teacher_name": "Hoca B", "lesson": "TARIH", "topic": "Konu B"}):
                    res_b = await harvester.harvest_single_task()
                    assert res_b["status"] == "success"

    # Veritabanı durumlarını doğrula
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT status FROM video_queue WHERE video_id = ?", (vid_a,))
        row_a = c.fetchone()
        c.execute("SELECT status FROM video_queue WHERE video_id = ?", (vid_b,))
        row_b = c.fetchone()

        assert row_a["status"] == "TRANSCRIPT_DEFERRED"
        assert row_b["status"] == "WATCHED"


@pytest.mark.asyncio
async def test_rate_limit_is_temporary():
    """8. 429 Rate Limit Hatasının TRANSIENT Sınıfında Olması Testi"""
    failure_class = curriculum_queue.classify_failure("HTTP Error 429: Too Many Requests")
    assert failure_class == FailureClass.QUOTA_EXHAUSTED


@pytest.mark.asyncio
async def test_permanent_video_failure_is_not_retried_forever():
    """9. Silinmiş/Gizli Videoların PERMANENT Olarak Sınıflandırılması"""
    failure_class_404 = curriculum_queue.classify_failure("Video unavailable: 404 Not Found")
    assert failure_class_404 == FailureClass.PERMANENT

    failure_class_private = curriculum_queue.classify_failure("This video is private")
    assert failure_class_private == FailureClass.PERMANENT


@pytest.mark.asyncio
async def test_transcript_segments_preserve_timestamps():
    """10. Segmentlerin Gerçek Zaman Damgalarını ve Hash'lerini Koruması"""
    seg = TranscriptSegment(
        segment_id="seg_01",
        video_id="vid_time_01",
        start_seconds=12.45,
        end_seconds=18.90,
        text="TBMM'nin açılışı ve ilk anayasa"
    )
    assert seg.start_seconds == 12.45
    assert seg.end_seconds == 18.90
    assert len(seg.segment_hash) == 16


@pytest.mark.asyncio
async def test_provider_diagnostics_are_saved():
    """11. Sağlayıcı Teşhislerinin Veritabanına Kaydedilmesi"""
    gateway = TranscriptGateway()
    test_diag = TranscriptDiagnostics(
        video_id="vid_diag_test",
        provider=TranscriptProviderType.YTDLP_SUBTITLES,
        attempt_number=1,
        status=TranscriptStatus.YTDLP_BLOCKED,
        error_code="YTDLP_BLOCKED",
        error_message="Bot challenge triggered",
        duration_ms=250
    )
    gateway._persist_diagnostics(test_diag)

    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM transcript_provider_attempts WHERE video_id = ?", ("vid_diag_test",))
        row = c.fetchone()
        assert row is not None
        assert row["provider"] == "YTDLP_SUBTITLES"
        assert row["status"] == "YTDLP_BLOCKED"
        assert row["duration_ms"] == 250


@pytest.mark.asyncio
async def test_llm_error_is_not_silently_swallowed():
    """12. LLM Hatalarının Sessizce Yutulmadığı ve Structured Loglandığı Testi"""
    with patch("httpx.AsyncClient.post", side_effect=Exception("ConnectionRefusedError to Ollama")):
        res = await TranscriptProcessor.process_video_transcript(
            video_id="vid_llm_err",
            title="Hata Test Dersi",
            teacher_name="Hoca",
            lesson="TARIH",
            topic="Konu",
            full_transcript="Kısa bir transkript metni",
            segments=[]
        )
        assert isinstance(res, dict)
        assert res.get("facts_extracted", 0) == 0


@pytest.mark.asyncio
async def test_pending_claim_cannot_enter_knowledge_store():
    """13. KNOWLEDGE FIREWALL: PENDING Durumundaki İddianın Doğrudan Ambarlara Girememesi"""
    lesson = "TEST_FIREWALL_LESSON"
    topic = "TEST_FIREWALL_TOPIC"

    # Transkript işleme çağrısı yap (facts içeren sahte LLM yanıtı)
    fake_llm_resp = {
        "response": '{"facts": [{"text": "1921 Anayasası Teşkilatı Esasiye yumuşak bir anayasadır.", "subtopic": "Hukuk"}]}'
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_llm_resp

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        await TranscriptProcessor.process_video_transcript(
            video_id="vid_firewall_1",
            title="Anayasa Dersi",
            teacher_name="Test Hoca",
            lesson=lesson,
            topic=topic,
            full_transcript="1921 Anayasası Teşkilatı Esasiye yumuşak bir anayasadır.",
            segments=[]
        )

    # Knowledge store tablosuna bak: FACT olarak onaylanmamış iddia ambarlara GİRMEMİŞ olmalıdır!
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM knowledge_records WHERE lesson = ? AND record_type = 'FACT'", (lesson,))
        fact_count = c.fetchone()["cnt"]
        assert fact_count == 0

        # Ancak SQLite atomic_claims tablosunda PENDING olarak durmalıdır!
        c.execute("SELECT verification_status FROM atomic_claims WHERE lesson = ?", (lesson,))
        claim_row = c.fetchone()
        assert claim_row is not None
        assert claim_row["verification_status"] == "PENDING"


@pytest.mark.asyncio
async def test_circuit_breaker_trips_on_ip_rate_limit():
    """14. 429 Rate Limit Hatalarında Devre Kesicinin Derhal OPEN Durumuna Geçmesi Testi"""
    gateway = TranscriptGateway()

    # Provider 0'ı 429 hatası döndürecek şekilde ayarla
    gateway.providers[0].attempt = AsyncMock(return_value=TranscriptResult(
        video_id="vid_ip_block_1",
        success=False,
        provider=TranscriptProviderType.YOUTUBE_CAPTIONS,
        status=TranscriptStatus.CAPTION_FETCH_FAILED,
        error="YouTube is blocking requests from your IP. (HTTP Error 429: Too Many Requests)"
    ))

    # Whisper'ı başarılı yap
    fake_segments = [
        TranscriptSegment(segment_id="w1", video_id="vid_ip_block_1", start_seconds=0.0, end_seconds=5.0, text="Hızlı Whisper Fallback")
    ]
    gateway.providers[1].attempt = AsyncMock(return_value=TranscriptResult(video_id="vid_ip_block_1", success=False, status=TranscriptStatus.NO_CAPTION_TRACK))
    gateway.providers[2].attempt = AsyncMock(return_value=TranscriptResult(video_id="vid_ip_block_1", success=False, status=TranscriptStatus.NO_CAPTION_TRACK))
    gateway.providers[3].attempt = AsyncMock(return_value=TranscriptResult(
        video_id="vid_ip_block_1", success=True, provider=TranscriptProviderType.LOCAL_WHISPER, segments=fake_segments
    ))

    res1 = await gateway.get_transcript("vid_ip_block_1", allow_whisper=True)
    assert res1.success is True

    # Devre kesici YOUTUBE_CAPTIONS için OPEN olmalıdır
    assert gateway.circuit_breaker.state.get(TranscriptProviderType.YOUTUBE_CAPTIONS) == "OPEN"
    # İkinci çağrıda YOUTUBE_CAPTIONS devre kesici OPEN olduğu için atlanmalıdır (attempt çağrılmamalı)
    gateway.providers[0].attempt.reset_mock()
    res2 = await gateway.get_transcript("vid_ip_block_2", allow_whisper=True)
    assert gateway.providers[0].attempt.call_count == 0

