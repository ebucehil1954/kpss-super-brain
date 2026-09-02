"""
KPSS Super-Brain: Phase 7 — Kanal Taraması ve Kimlik Doğrulama Testleri
Master Refactor Plan Phase 7 Kapsamı:
1. test_channel_scan_stays_within_channel: Kanal taraması yalnızca o kanala ait videoları içerir.
2. test_global_search_does_not_claim_channel_ownership: Küresel arama kanal sahipliği iddia edemez.
3. test_channel_identity_is_verified: Altın standart kanal kimlikleri doğrulanır.
"""
import pytest
from curriculum.channel_scanner import channel_scanner

def test_channel_identity_is_verified():
    """Phase 7: Altın standart KPSS kanalları kimlik doğrulamasından geçer."""
    assert channel_scanner.verify_channel_identity("Benim Hocam") is True
    assert channel_scanner.verify_channel_identity("Hocawebde") is True
    assert channel_scanner.verify_channel_identity("İsem TV") is True
    assert channel_scanner.verify_channel_identity("RastgeleBilinmeyenKanal12345") is False
    assert channel_scanner.verify_channel_identity("") is False

def test_channel_scan_stays_within_channel():
    """Phase 7: Kanal taraması yapıldığında harici kanalların videoları filtrelenir."""
    mixed_videos = [
        {"video_id": "vid_1", "title": "Tarih 1", "channel": "Benim Hocam"},
        {"video_id": "vid_2", "title": "Tarih 2", "channel": "İsem TV"},
        {"video_id": "vid_3", "title": "Tarih 3", "channel": "Benim Hocam"},
        {"video_id": "vid_4", "title": "Tarih 4", "channel": "Rastgele Kanal"}
    ]

    filtered = channel_scanner.filter_videos_by_channel(mixed_videos, target_channel="Benim Hocam")
    assert len(filtered) == 2
    for v in filtered:
        assert v["channel"] == "Benim Hocam"

def test_global_search_does_not_claim_channel_ownership():
    """Phase 7: Hedef kanal belirtilmediğinde küresel arama tüm kanalları kendi orijinal adıyla tutar."""
    mixed_videos = [
        {"video_id": "vid_1", "title": "Coğrafya", "channel": "Hocawebde"},
        {"video_id": "vid_2", "title": "Vatandaşlık", "channel": "Yediiklim"}
    ]
    # target_channel boş bırakıldığında kanallara zorla tek bir isim atanamaz
    results = channel_scanner.filter_videos_by_channel(mixed_videos, target_channel="")
    assert len(results) == 2
    assert results[0]["channel"] == "Hocawebde"
    assert results[1]["channel"] == "Yediiklim"
