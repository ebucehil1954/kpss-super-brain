"""
KPSS Super-Brain: Phase 5 — Görev Tipleri Sözleşmesi Testleri (Task Contracts)
Master Refactor Plan Phase 5 Kapsamı:
1. test_research_task_is_not_processed_as_video: ResearchTask asla VideoTask olarak kabul edilemez.
2. test_video_task_requires_real_video_id: VideoTask geçerli bir video_id zorunlu kılar.
3. test_task_type_contracts_are_enforced: Tip sözleşmeleri katı biçimde uygulanır.
4. test_invalid_task_payload_is_rejected: Geçersiz payload doğrudan reddedilir.
"""
import pytest
from pydantic import ValidationError
from curriculum.models import (
    TaskType, ResearchTask, VideoTask, IngestionTask, AnalysisTask,
    VerificationTask, LessonType, validate_task_contract
)

def test_research_task_is_not_processed_as_video():
    """Phase 5: Bir konu keşif görevi (ResearchTask) video yürütücüsüne verilemez."""
    task = ResearchTask(
        task_id="task_res_001",
        lesson=LessonType.VATANDASLIK,
        topic_id="VAT_01",
        topic_name="Temel Haklar",
        search_queries=["KPSS Temel Haklar"]
    )
    # ResearchTask bir VIDEO görevi değildir
    assert validate_task_contract(task, TaskType.VIDEO) is False
    assert validate_task_contract(task, TaskType.RESEARCH) is True

def test_video_task_requires_real_video_id():
    """Phase 5: VideoTask sahte veya boş video_id ile oluşturulamaz."""
    with pytest.raises(ValidationError):
        # Boş video ID reddedilir
        VideoTask(
            task_id="vtask_01",
            video_id="",
            url="https://youtube.com",
            title="Ders 1"
        )

    with pytest.raises(ValidationError):
        # Sentetik/fake video ID reddedilir
        VideoTask(
            task_id="vtask_02",
            video_id="fake_vid_123",
            url="https://youtube.com",
            title="Ders 2"
        )

    # Geçerli video_id ile başarıyla oluşur
    v_valid = VideoTask(
        task_id="vtask_03",
        video_id="dQw4w9WgXcQ",
        url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        title="Geçerli Ders"
    )
    assert v_valid.video_id == "dQw4w9WgXcQ"
    assert validate_task_contract(v_valid, TaskType.VIDEO) is True
    assert validate_task_contract(v_valid, TaskType.RESEARCH) is False

def test_task_type_contracts_are_enforced():
    """Phase 5: 5 aşamalı boru hattı sözleşmesi (Pipeline Contracts) doğrulanır."""
    ingest = IngestionTask(task_id="i_1", video_id="dQw4w9WgXcQ", lesson="TARIH", topic="Osmanlı")
    analysis = AnalysisTask(task_id="a_1", video_id="dQw4w9WgXcQ", transcript_text="Metin", lesson="TARIH", topic="Osmanlı")
    verif = VerificationTask(task_id="v_1", claim_id="c_1", claim_text="İddia", lesson="TARIH", topic="Osmanlı")

    assert validate_task_contract(ingest, TaskType.INGESTION) is True
    assert validate_task_contract(ingest, TaskType.ANALYSIS) is False
    assert validate_task_contract(analysis, TaskType.ANALYSIS) is True
    assert validate_task_contract(verif, TaskType.VERIFICATION) is True

def test_invalid_task_payload_is_rejected():
    """Phase 5: Boş veya tanımsız payload'lar sözleşme denetiminde False döner."""
    assert validate_task_contract(None, TaskType.RESEARCH) is False
    assert validate_task_contract({}, TaskType.VIDEO) is False
    assert validate_task_contract({"task_type": "UNKNOWN_GARBAGE"}, TaskType.RESEARCH) is False
