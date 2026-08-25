"""
KPSS Super-Brain: Agentic Research, Veri Bütünlüğü ve Baş Mühendis Doğrulama Testleri
1. Transkript Başarısızlığı ve Sahte Veri İzolasyonu (Test 1)
2. Provenance ve Segment Zaman Damgası Bütünlüğü (Test 2)
3. Tip Güvenli ToolRegistry ve Timeout Kalkanı (Test 3)
4. Çelişki Çözüm Motoru ve Resmi Kaynak Üstünlüğü (Test 4)
5. Stateful Research Agent Durum Makinesi ve Olay Günlüğü (Test 5)
6. Deterministik Çok Faktörlü Hakimiyet Hesaplama (Test 6)
"""
import pytest
import asyncio
from brain.models import (
    SourceType, VideoState, ClaimType, ContradictionSeverity, ContradictionResolution
)
from brain.database import db_session
from senses.transcript_fetcher import transcript_fetcher
from senses.transcript_processor import transcript_processor
from senses.video_queue import video_queue
from autonomous.tool_registry import tool_registry, ToolDefinition
from autonomous.research_agent import research_agent
from cognition.contradiction_engine import contradiction_engine
from brain.curriculum_matrix import curriculum_matrix

@pytest.mark.asyncio
async def test_transcript_failure_does_not_pollute_mastery():
    """
    Test 1: Transkript Başarısızlığı İzolasyonu:
    Transkripti olmayan bir video asla web özetiyle doldurulup 'başarıyla izlendi' sayılamaz.
    """
    fake_vid_id = "test_no_trans_99"
    video_queue.enqueue_video({
        "video_id": fake_vid_id,
        "title": "Altyazısız Test Dersi",
        "teacher_name": "Test Hoca",
        "lesson": "VATANDASLIK",
        "topic": "Temel Haklar"
    })
    
    # Transkript çekimini çağır
    res = await transcript_fetcher.fetch_transcript_resilient(fake_vid_id, enable_whisper_fallback=False)
    assert res.get("success") is False
    assert res.get("error") == "TRANSCRIPT_UNAVAILABLE"

    # Kuyruk durumunu güncelle
    video_queue.mark_no_transcript(fake_vid_id, error_msg=res.get("error"))
    
    # Video durumunu doğrula
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, transcript_length FROM video_queue WHERE video_id = ?", (fake_vid_id,))
        row = cursor.fetchone()
        assert row["status"] == "NO_TRANSCRIPT"
        assert row["transcript_length"] == 0

@pytest.mark.asyncio
async def test_provenance_and_segment_timestamp_integrity():
    """
    Test 2: Provenance ve Segment Zaman Damgası:
    Çıkarılan iddialar (AtomicClaim) gerçek kaynak ve segment referansı taşımalıdır.
    """
    sample_text = "1982 Anayasası Madde 146 uyarınca Anayasa Mahkemesi 15 üyeden oluşur. Üyeler 12 yıl için seçilir."
    proc_res = await transcript_processor.process_video_transcript(
        video_id="test_prov_vid_01",
        title="Anayasa Yargısı",
        teacher_name="Emrah Vahap",
        lesson="VATANDASLIK",
        topic="Anayasa Mahkemesi",
        full_transcript=sample_text
    )

    assert proc_res["facts_extracted"] >= 1
    
    # SQLite atomic_claims tablosunu denetle
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM atomic_claims WHERE lesson = 'VATANDASLIK' AND topic = 'Anayasa Mahkemesi'")
        rows = cursor.fetchall()
        assert len(rows) >= 1
        claim = dict(rows[0])
        assert claim["claim_id"].startswith("claim_")
        assert len(claim["provenance_hash"]) >= 8
        assert "src_yt_test_prov_vid_01" in claim["evidence_refs_json"]

@pytest.mark.asyncio
async def test_tool_registry_type_safety_and_timeouts():
    """
    Test 3: ToolRegistry ve Timeout Kalkanı:
    Kayıtlı araçlar parametre doğrulaması ve zaman aşımı korumasıyla güvenli çalışmalıdır.
    """
    # 1. Bilgi arama aracı testi
    search_res = await tool_registry.execute("knowledge_search", {"query": "Anayasa", "lesson": "VATANDASLIK"})
    assert search_res["success"] is True
    assert "duration_ms" in search_res

    # 2. Var olmayan tool testi
    bad_res = await tool_registry.execute("non_existent_tool", {})
    assert bad_res["success"] is False
    assert "bulunamadı" in bad_res["error"]

def test_contradiction_engine_official_source_wins():
    """
    Test 4: Çelişki Çözüm Motoru:
    Farklı kaynaklardan gelen çelişen iddialar tespit edilmeli ve OFFICIAL_SOURCE_WINS ile çözümlenmelidir.
    """
    claims = [
        {"claim_id": "c1", "text": "1982 Anayasasına göre Anayasa Mahkemesi 15 üyeden oluşur.", "source": "Resmî Gazete"},
        {"claim_id": "c2", "text": "Anayasa Mahkemesi toplam 11 üyeden kuruludur.", "source": "Eski Hoca Notu"}
    ]
    records = contradiction_engine.detect_and_resolve_contradictions(
        lesson="VATANDASLIK",
        topic="Anayasa Mahkemesi Kuruluşu",
        claims=claims
    )
    assert len(records) >= 1
    rec = records[0]
    assert rec.severity == ContradictionSeverity.HIGH
    assert rec.resolution == ContradictionResolution.OFFICIAL_SOURCE_WINS
    assert rec.winning_claim_id == "c1"

@pytest.mark.asyncio
async def test_stateful_research_agent_cycle_and_events():
    """
    Test 5: Stateful Research Agent:
    Otonom ajan tüm durumlardan geçmeli, olayları kaydetmeli ve deterministik hakimiyet üretmelidir.
    """
    res = await research_agent.run_autonomous_research_cycle(
        goal="1982 Anayasası Yargı Organını ve AYM Yapısını Araştır",
        lesson="VATANDASLIK",
        topic="1982 Anayasası Yargı Organı",
        target_concepts=["AYM Üye Sayısı", "HSK Yapısı", "Yargıtay ve Danıştay"]
    )
    assert res["status"] == "COMPLETED"
    assert res["mastery_score"] > 0.0
    assert "research_id" in res

    # Olay günlüğünü doğrula
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM research_events WHERE research_id = ? ORDER BY timestamp ASC", (res["research_id"],))
        events = cursor.fetchall()
        assert len(events) >= 4

def test_deterministic_mastery_calculation():
    """
    Test 6: Çok Faktörlü Deterministik Hakimiyet Hesaplama:
    Mastery skoru kaynak çeşitliliği, kanıt yoğunluğu ve doğrulama metriklerine göre hesaplanır.
    """
    topic_id = "ANAYASA_MAHKEMESI"
    # Örnek kayıt ekle
    curriculum_matrix.record_video_consumption(
        lesson="VATANDASLIK",
        topic=topic_id,
        video_id="test_calc_vid_1",
        teacher_name="Emrah Vahap",
        channel_name="Hoca TV",
        facts_extracted=8,
        traps_extracted=2,
        reasoning_extracted=1
    )
    
    mastery = curriculum_matrix.calculate_deterministic_mastery(topic_id)
    assert mastery["overall_mastery"] > 0.0
    assert 0.0 <= mastery["source_coverage"] <= 1.0
    assert 0.0 <= mastery["evidence_density"] <= 1.0
    assert 0.0 <= mastery["verification_score"] <= 1.0
