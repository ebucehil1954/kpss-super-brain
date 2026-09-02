"""
KPSS Super-Brain: YouTube Data API v3 İstemcisi Güvenlik ve İşlevsellik Test Paketi
API anahtarının gizliliğini (maskeleme), süre çözümlemeyi ve arama sözleşmesini test eder.
"""
from unittest.mock import patch, MagicMock
import pytest
from senses.youtube_api_client import _parse_iso8601_duration, YouTubeApiClient, youtube_api_client


def test_iso8601_duration_parsing():
    """ISO 8601 YouTube süre formatlarının doğru saniyeye çevrildiğini doğrula"""
    assert _parse_iso8601_duration("PT1H23M45S") == 5025
    assert _parse_iso8601_duration("PT45M12S") == 2712
    assert _parse_iso8601_duration("PT30S") == 30
    assert _parse_iso8601_duration("PT1H") == 3600
    assert _parse_iso8601_duration("PT10M") == 600
    assert _parse_iso8601_duration("") == 0
    assert _parse_iso8601_duration("INVALID") == 0


def test_api_key_masking_security():
    """API anahtarının loglarda ve arayüzde asla açık şekilde görünmediğini doğrula"""
    masked = YouTubeApiClient._get_masked_key()
    assert "..." in masked
    assert len(masked) <= 12
    # Anahtarın tamamı asla masked içinde olmamalı
    from config import super_brain_config
    if super_brain_config.YOUTUBE_API_KEY:
        assert super_brain_config.YOUTUBE_API_KEY != masked


def test_youtube_api_client_mock_search():
    """Resmi YouTube Data API v3 arama mock çağrısını doğrula"""
    fake_response_data = {
        "items": [
            {
                "id": {"videoId": "test_yt_vid1"},
                "snippet": {
                    "title": "KPSS Tarih İslamiyet Öncesi Türk Tarihi",
                    "channelTitle": "Benim Hocam",
                    "channelId": "ch_123",
                    "publishedAt": "2026-08-20T10:00:00Z",
                    "description": "Ders anlatımı"
                }
            }
        ]
    }
    fake_details_data = {
        "items": [
            {
                "id": "test_yt_vid1",
                "contentDetails": {"duration": "PT35M20S"}
            }
        ]
    }

    mock_resp_search = MagicMock()
    mock_resp_search.status_code = 200
    mock_resp_search.json.return_value = fake_response_data

    mock_resp_details = MagicMock()
    mock_resp_details.status_code = 200
    mock_resp_details.json.return_value = fake_details_data

    with patch("httpx.Client.get") as mock_get:
        mock_get.side_effect = [mock_resp_search, mock_resp_details]
        results = YouTubeApiClient.search_videos("KPSS Tarih", max_results=1)

        assert len(results) == 1
        item = results[0]
        assert item["video_id"] == "test_yt_vid1"
        assert item["title"] == "KPSS Tarih İslamiyet Öncesi Türk Tarihi"
        assert item["channel"] == "Benim Hocam"
        assert item["duration_seconds"] == 2120  # 35*60 + 20
        assert item["url"] == "https://www.youtube.com/watch?v=test_yt_vid1"
