"""
Forensic Audit P1-5 Regresyon Testi:
contradictions tablosundaki is_resolved → resolution schema düzeltmesini doğrular.
"""
import pytest
from brain.database import db_session, initialize_database


class TestContradictionsSchema:
    """contradictions tablosu schema uyumluluk testleri (P1-5)."""

    def test_contradictions_table_has_resolution_column(self):
        """contradictions tablosunda 'resolution' kolonu olmalı, 'is_resolved' değil."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(contradictions)")
            columns = {row[1] for row in cursor.fetchall()}

            assert "resolution" in columns, \
                "contradictions tablosunda 'resolution' kolonu bulunamadı!"
            assert "is_resolved" not in columns, \
                "contradictions tablosunda 'is_resolved' kolonu olmamalı (schema mismatch)!"

    def test_contradictions_query_uses_resolution_column(self):
        """queue.py'deki contradictions sorgusu doğru kolon adını kullanmalı."""
        import inspect
        from curriculum.queue import CurriculumQueue

        source_code = inspect.getsource(CurriculumQueue.mark_video_watched)

        assert "is_resolved" not in source_code, \
            "mark_video_watched() hala 'is_resolved' kullanıyor! (P1-5 düzeltmesi uygulanmamış)"
        assert "resolution = 'UNRESOLVED'" in source_code, \
            "mark_video_watched() 'resolution = UNRESOLVED' sorgusunu kullanmalı!"

    def test_contradictions_unresolved_query_works(self):
        """UNRESOLVED contradictions sorgusu hata vermeden çalışmalı."""
        with db_session() as conn:
            cursor = conn.cursor()
            # Bu sorgu OperationalError fırlatmamalı
            cursor.execute(
                "SELECT COUNT(*) as c_cnt FROM contradictions WHERE topic LIKE ? AND resolution = 'UNRESOLVED'",
                ("%Test%",)
            )
            result = cursor.fetchone()
            assert result is not None
            assert result["c_cnt"] >= 0

    def test_contradiction_engine_timeouts_are_robust(self):
        """ContradictionEngine timeouts en az 2.0s (ping) ve 25.0s (çıkarım) olmalı (P0 Timeout Düzeltmesi)."""
        import inspect
        from cognition import contradiction_engine

        source_ping = inspect.getsource(contradiction_engine._is_ollama_available)
        assert "timeout=0.1" not in source_ping, "Ollama ping timeout 0.1s olmamalı!"
        assert "timeout=2.0" in source_ping or "timeout=2" in source_ping, "Ollama ping timeout 2.0s olmalı!"

        source_check = inspect.getsource(contradiction_engine.check_contradiction)
        assert "timeout=1.0" not in source_check, "Contradiction check timeout 1.0s olmamalı!"
        assert "timeout=25.0" in source_check or "timeout=25" in source_check, "Contradiction check timeout 25.0s olmalı!"

    def test_contradiction_engine_batch_optimization(self):
        """Toplu vektörleşme ve aday filtreleme ile çelişkilerin doğru ve hızlı tespit edildiğini doğrula."""
        from cognition.contradiction_engine import contradiction_engine

        claims = [
            {"claim_id": "c1", "text": "AYM 15 üyeden oluşur.", "source": "Öğretmen A", "speaker_or_author": "Öğretmen A"},
            {"claim_id": "c2", "text": "AYM 11 üyeden oluşur.", "source": "Öğretmen B", "speaker_or_author": "Öğretmen B"},
            {"claim_id": "c3", "text": "Türkiye'nin başkenti Ankara'dır.", "source": "Öğretmen C", "speaker_or_author": "Öğretmen C"},
            {"claim_id": "c4", "text": "Karadeniz kıyılarında bol yağış görülür.", "source": "Öğretmen D", "speaker_or_author": "Öğretmen D"},
        ]
        # 10 adet alakasız iddia daha ekle
        for idx in range(5, 15):
            claims.append({
                "claim_id": f"c{idx}",
                "text": f"Genel kültür bilgisi {idx}: Çeşitli coğrafi özellikler ve nehirler {idx}",
                "source": f"Kaynak {idx}",
                "speaker_or_author": f"Kaynak {idx}"
            })

        recs = contradiction_engine.detect_and_resolve_contradictions("VATANDASLIK", "YARGI", claims)
        # Sadece c1 ve c2 arasında sayısal AYM üye uyuşmazlığı yakalanmalı
        assert len(recs) == 1
        assert "AYM" in recs[0].claim_a_text and "AYM" in recs[0].claim_b_text
