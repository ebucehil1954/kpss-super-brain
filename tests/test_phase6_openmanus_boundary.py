"""
KPSS Super-Brain: Phase 6 — OpenManus Sınır ve Yetki İzolasyon Testleri
Master Refactor Plan Phase 6 Kapsamı:
1. test_openmanus_returns_research_result: OpenManus doğrulanmış ResearchResult döner.
2. test_openmanus_cannot_commit_knowledge: OpenManus doğrudan kanonik bilgi yazamaz.
3. test_openmanus_cannot_change_trust: OpenManus doğrudan güven skoru değiştiremez.
4. test_openmanus_result_is_schema_validated: Sonuçlar Pydantic şema doğrulamasına tabidir.
"""
import pytest
from openmanus_bridge import (
    ResearchResult, DiscoveredVideo, OpenManusResultParser,
    openmanus_bridge_client
)
from curriculum.models import ResearchTask, LessonType

def test_openmanus_returns_research_result():
    """Phase 6: OpenManus ayrıştırıcısı bir ResearchResult örneği döner."""
    mock_raw = {
        "summary": "Coğrafya araması yapıldı.",
        "videos": [
            {
                "video_id": "dQw4w9WgXcQ",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Yer Şekilleri",
                "channel": "Benim Hocam",
                "teacher_name": "Bayram Meral",
                "duration_seconds": 1200
            }
        ]
    }
    result = OpenManusResultParser.parse_raw_output(
        task_id="t_om_01",
        query="KPSS Coğrafya Bayram Meral",
        raw_output=mock_raw
    )
    assert isinstance(result, ResearchResult)
    assert result.status == "SUCCESS"
    assert len(result.videos) == 1
    assert result.videos[0].video_id == "dQw4w9WgXcQ"

def test_openmanus_cannot_commit_knowledge():
    """Phase 6: OpenManus istemcisinin doğrudan kanonik bilgi yazma yetkisi yoktur."""
    assert openmanus_bridge_client.commit_knowledge_forbidden is not None
    with pytest.raises(PermissionError):
        openmanus_bridge_client.commit_knowledge_forbidden()

    # ResearchResult nesnesi üzerinde de doğrudan commit yetkisi bulunmaz
    res = ResearchResult(task_id="t1", query="q", status="SUCCESS")
    assert res.can_commit_directly() is False

def test_openmanus_cannot_change_trust():
    """Phase 6: OpenManus güven skorunu (trust/confidence) doğrudan değiştiremez."""
    res = ResearchResult(task_id="t2", query="q", status="SUCCESS")
    assert res.can_modify_trust() is False

def test_openmanus_result_is_schema_validated():
    """Phase 6: Sahte video ID'leri OpenManus sonuç şemasından elenir."""
    mock_with_fake = {
        "videos": [
            {"video_id": "fake_bad_video", "title": "Sahte"}, # Reddedilmeli
            {"video_id": "valid123456", "title": "Geçerli"}     # Kabul edilmeli
        ]
    }
    parsed = OpenManusResultParser.parse_raw_output("t3", "query", mock_with_fake)
    # Yalnızca geçerli video kabul edilmelidir
    assert len(parsed.videos) == 1
    assert parsed.videos[0].video_id == "valid123456"
