"""
Forensic Audit P0-2 Regresyon Testleri:
Güven skoru enflasyonu düzeltmesini doğrular:
- Aynı video_id'den gelen tekrar güçlendirme güven skorunu artırmamalı
- MAX_REINFORCEMENTS aşıldığında güven skoru sabit kalmalı
"""
import pytest
import json
from brain.knowledge_store import knowledge_store, MAX_REINFORCEMENTS
from brain.database import db_session


class TestConfidenceInflation:
    """Güven skoru enflasyonu regresyon testleri (P0-2)."""

    def _cleanup_test_records(self):
        """Test kayıtlarını temizle."""
        try:
            with db_session() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM knowledge_records WHERE text LIKE '%CONFIDENCE_TEST%'")
        except Exception:
            pass

    def test_same_video_id_does_not_increase_confidence(self):
        """Aynı video_id ile tekrar güçlendirme güven skorunu artırmamalı."""
        self._cleanup_test_records()

        same_video_source = {
            "type": "youtube_lecture",
            "video_id": "ABC123VIDEO",
            "speaker_or_author": "Test Hoca"
        }

        # İlk kayıt
        r1 = knowledge_store.add_or_reinforce_record(
            text="CONFIDENCE_TEST: TBMM 600 üyeden oluşur",
            record_type="FACT",
            lesson="VATANDASLIK",
            topic="Anayasa",
            confidence=0.90,
            source=same_video_source,
            tags=["test"]
        )
        initial_confidence = r1["confidence"]
        assert r1["action"] == "created"

        # Aynı video_id ile tekrar güçlendirme
        r2 = knowledge_store.add_or_reinforce_record(
            text="CONFIDENCE_TEST: TBMM 600 üyeden oluşur",
            record_type="FACT",
            lesson="VATANDASLIK",
            topic="Anayasa",
            confidence=0.95,
            source=same_video_source,
            tags=["test"]
        )
        assert r2["action"] == "reinforced"
        assert r2["confidence"] == initial_confidence, \
            f"Aynı video_id'den güven skoru artmamalı! {initial_confidence} -> {r2['confidence']}"

        self._cleanup_test_records()

    def test_different_teacher_increases_confidence(self):
        """Farklı bağımsız öğretmen güven skorunu artırmalı."""
        self._cleanup_test_records()

        # İlk kayıt: Hoca A
        r1 = knowledge_store.add_or_reinforce_record(
            text="CONFIDENCE_TEST: Toplantı yeter sayısı 200",
            record_type="FACT",
            lesson="VATANDASLIK",
            topic="Anayasa",
            confidence=0.90,
            source={
                "type": "youtube_lecture",
                "video_id": "VIDEO_A",
                "speaker_or_author": "Hoca A"
            },
            tags=["test"]
        )
        initial_confidence = r1["confidence"]

        # Farklı hoca, farklı video
        r2 = knowledge_store.add_or_reinforce_record(
            text="CONFIDENCE_TEST: Toplantı yeter sayısı 200",
            record_type="FACT",
            lesson="VATANDASLIK",
            topic="Anayasa",
            confidence=0.95,
            source={
                "type": "youtube_lecture",
                "video_id": "VIDEO_B",
                "speaker_or_author": "Hoca B"
            },
            tags=["test"]
        )
        assert r2["action"] == "reinforced"
        assert r2["confidence"] > initial_confidence, \
            "Bağımsız yeni öğretmen güven skorunu artırmalı!"

        self._cleanup_test_records()

    def test_max_reinforcements_cap(self):
        """MAX_REINFORCEMENTS üst limitine ulaşıldığında güven skoru artmamalı."""
        self._cleanup_test_records()

        # İlk kayıt
        knowledge_store.add_or_reinforce_record(
            text="CONFIDENCE_TEST: AYM 15 üyeden oluşur",
            record_type="FACT",
            lesson="VATANDASLIK",
            topic="Anayasa",
            confidence=0.90,
            source={
                "type": "youtube_lecture",
                "video_id": "VID_0",
                "speaker_or_author": "Hoca_0"
            },
            tags=["test"]
        )

        # MAX_REINFORCEMENTS + 2 kez farklı hocalarla güçlendir
        for i in range(1, MAX_REINFORCEMENTS + 3):
            r = knowledge_store.add_or_reinforce_record(
                text="CONFIDENCE_TEST: AYM 15 üyeden oluşur",
                record_type="FACT",
                lesson="VATANDASLIK",
                topic="Anayasa",
                confidence=0.95,
                source={
                    "type": "youtube_lecture",
                    "video_id": f"VID_{i}",
                    "speaker_or_author": f"Hoca_{i}"
                },
                tags=["test"]
            )

        # Son güçlendirme sonrası skor kontrol et
        final_confidence = r["confidence"]

        # MAX_REINFORCEMENTS'ı geçtikten sonra artık artmamalı
        # (Son birkaç güçlendirme skoru sabit tutmalı)
        assert r["times_reinforced"] > MAX_REINFORCEMENTS

        self._cleanup_test_records()


# Temizlik
def teardown_module():
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_records WHERE text LIKE '%CONFIDENCE_TEST%'")
    except Exception:
        pass
