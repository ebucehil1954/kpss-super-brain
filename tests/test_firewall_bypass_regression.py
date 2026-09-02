"""
Forensic Audit P0-1, P0-3, P0-4, P0-5 Regresyon Testleri:
- analyst.py: LLM çıktıları doğrudan kanonik ambara yazılmadığını doğrula
- transcript_processor.py: Fallback yolunun kanonik ambara yazmadığını doğrula
- prosecutor_auditor.py: Exception durumunda AUDIT_FAILED döndüğünü doğrula
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from brain.knowledge_store import KnowledgeStore, knowledge_store
from brain.database import db_session, initialize_database


class TestFirewallBypassRegression:
    """Knowledge Firewall bypass regresyon testleri."""

    def test_stage_pending_record_does_not_write_to_canonical(self):
        """stage_pending_record() kanonik knowledge_records tablosuna YAZMAMALI."""
        result = knowledge_store.stage_pending_record(
            text="Test bilgi: TBMM 600 üyeden oluşur",
            record_type="FACT",
            lesson="VATANDASLIK",
            topic="Anayasa",
            confidence=0.90,
            source={"type": "test"},
            tags=["test"]
        )

        assert result["status"] == "staged_pending"
        assert result["verification_status"] == "PENDING"
        claim_id = result["claim_id"]

        # Kanonik ambarda (knowledge_records) olmamalı
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_records WHERE text LIKE '%Test bilgi%'")
            canonical_row = cursor.fetchone()
            assert canonical_row is None, "stage_pending_record() kanonik ambara yazmamalı!"

        # Staging'de (atomic_claims) olmalı
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM atomic_claims WHERE claim_id = ?", (claim_id,))
            staging_row = cursor.fetchone()
            assert staging_row is not None, "stage_pending_record() staging tablosuna yazmalı!"
            assert staging_row["verification_status"] == "PENDING"

    def test_stage_pending_record_mnemonic(self):
        """MNEMONIC kategorisi de staging'den geçmeli."""
        result = knowledge_store.stage_pending_record(
            text="[KAYIP SAKAL] Rüzgar şifresi",
            record_type="MNEMONIC",
            lesson="COGRAFYA",
            topic="İklim"
        )
        assert result["status"] == "staged_pending"
        assert result["record_type"] == "MNEMONIC"

    def test_stage_pending_record_trap(self):
        """TRAP kategorisi de staging'den geçmeli."""
        result = knowledge_store.stage_pending_record(
            text="⚠️ TBMM üye sayısı 550 DEĞİLDİR!",
            record_type="TRAP",
            lesson="VATANDASLIK",
            topic="Anayasa"
        )
        assert result["status"] == "staged_pending"
        assert result["record_type"] == "TRAP"

    def test_stage_pending_record_empty_text_skipped(self):
        """Boş metin staging'e yazılmamalı."""
        result = knowledge_store.stage_pending_record(
            text="   ",
            record_type="FACT",
            lesson="GENEL",
            topic="Genel"
        )
        assert result["status"] == "skipped"


class TestProsecutorAuditFailSafe:
    """Prosecutor Auditor hata varsayılanı testleri (P0-3) ve TRAP staging koruması."""

    @pytest.mark.asyncio
    async def test_audit_returns_audit_failed_on_exception(self):
        """DeepSeek-R1 çevrimdışıysa verdict AUDIT_FAILED olmalı."""
        from cognition.prosecutor_auditor import ProsecutorAuditor

        auditor = ProsecutorAuditor()

        # httpx client'ı exception fırlatacak şekilde mock'la
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.return_value = mock_instance

            result = await auditor.audit_claim_deepseek(
                claim_text="TBMM 550 milletvekilinden oluşur",
                lesson="VATANDASLIK",
                topic="Anayasa",
                teacher="Test Hoca"
            )

        assert result["verdict"] == "AUDIT_FAILED", \
            f"Exception durumunda verdict AUDIT_FAILED olmalı, ama {result['verdict']} döndü!"

    @pytest.mark.asyncio
    async def test_prosecutor_rejected_trap_does_not_write_to_canonical(self):
        """REJECTED iddiadan üretilen TRAP kanonik ambara YAZILMAMALI, staging'e düşmeli (P0 Firewall Düzeltmesi)."""
        from cognition.prosecutor_auditor import ProsecutorAuditor
        auditor = ProsecutorAuditor()

        mock_llm_response = {
            "verdict": "REJECTED",
            "confidence": 0.99,
            "reasoning_steps": ["1982 Anayasası Madde 75 gereği TBMM 600 üyedir."],
            "canonical_truth": "TBMM 600 milletvekilinden oluşur.",
            "trap_distractor_formula": "550 sayısı 2017 öncesi eski anayasa kuralıdır."
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": json.dumps(mock_llm_response)}

        unique_claim = f"TBMM üye sayısı 550'dir_{int(pytest.importorskip('time').time())}"

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = mock_instance

            result = await auditor.audit_claim_deepseek(
                claim_text=unique_claim,
                lesson="VATANDASLIK",
                topic="Anayasa",
                teacher="Test Hoca"
            )

        assert result["verdict"] == "REJECTED"

        # Kanonik ambar kontrolü: Doğrudan yazılmamış olmalı!
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_records WHERE text LIKE ?", (f"%{unique_claim}%",))
            canonical_row = cursor.fetchone()
            assert canonical_row is None, "REJECTED TRAP kanonik knowledge_records tablosuna doğrudan YAZILMAMALI!"

            # Staging tablosu kontrolü: atomic_claims içinde PENDING olmalı!
            cursor.execute("SELECT * FROM atomic_claims WHERE text LIKE ? AND claim_type = 'TRAP'", (f"%{unique_claim}%",))
            staged_row = cursor.fetchone()
            assert staged_row is not None, "REJECTED TRAP atomic_claims staging tablosuna PENDING olarak mühürlenmeli!"
            assert staged_row["verification_status"] == "PENDING"


class TestFallbackFactsFirewall:
    """Transcript processor fallback facts regresyon testi (P0-4)."""

    def test_fallback_facts_not_in_canonical_store(self):
        """Fallback regex facts doğrudan kanonik ambara yazılmamalı —
        yalnızca atomic_claims staging tablosuna yazılmalı."""

        # Bu test, transcript_processor.py'deki fallback yolunun
        # knowledge_store.add_record() çağrısını artık İÇERMEDİĞİNİ doğrular
        import inspect
        from senses.transcript_processor import TranscriptProcessor

        source_code = inspect.getsource(TranscriptProcessor.process_video_transcript)

        # Fallback bloğunda (total_facts == 0 koşulundan sonra)
        # knowledge_store.add_record çağrısı OLMAMALI
        fallback_section_start = source_code.find("if total_facts == 0")
        if fallback_section_start != -1:
            fallback_section = source_code[fallback_section_start:]
            assert "knowledge_store.add_record" not in fallback_section, \
                "Fallback facts hala knowledge_store.add_record() ile kanonik ambara yazılıyor! (P0-4)"


class TestAuditorPagination:
    """AuditorEngine sayfalama ve LIMIT 300 kaldırma testleri (Aşama 2)."""

    def test_auditor_runs_with_batch_pagination(self):
        """run_full_knowledge_audit batch_size ve max_records ile çalışabilmeli."""
        from cognition.auditor import auditor_engine
        import inspect

        # Kod seviyesinde LIMIT 300'ün kaldırıldığını ve LIMIT ? OFFSET ? kullanıldığını doğrula
        source = inspect.getsource(auditor_engine.run_full_knowledge_audit)
        assert "LIMIT 300" not in source, "AuditorEngine hala sabit 'LIMIT 300' kullanıyor!"
        assert "LIMIT ? OFFSET ?" in source, "AuditorEngine sayfalamalı sorgu ('LIMIT ? OFFSET ?') kullanmalı!"

        # Küçük batch_size ile çalıştığını doğrula
        audit_res = auditor_engine.run_full_knowledge_audit(batch_size=10, max_records=20)
        assert "total_audited" in audit_res
        assert audit_res["total_audited"] <= 20
        assert "verified_by_z3_and_canon" in audit_res


# Temizlik
def teardown_module():
    """Test sonrası staging kayıtlarını temizle."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM atomic_claims WHERE claim_id LIKE 'staged_%'")
            cursor.execute("DELETE FROM knowledge_records WHERE text LIKE '%Test bilgi%'")
    except Exception:
        pass
