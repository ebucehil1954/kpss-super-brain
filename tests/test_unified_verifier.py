"""
KPSS Super-Brain: Hiyerarşik Birleşik Doğrulayıcı Test Süiti (Phase 4 Regression Tests)
UnifiedVerifier modülünün Kademe 1 (Kara Liste), Kademe 2 (Z3 SMT Formal Logic) ve Kademe 3 (Savcı / Ground Truth)
hiyerarşisini doğru sırada yürüttüğünü doğrular.
"""
import pytest
from unittest.mock import patch, MagicMock
from cognition.unified_verifier import UnifiedVerifier, VerificationVerdict, VerificationDecision


class TestUnifiedVerifier:

    @pytest.fixture
    def verifier(self):
        return UnifiedVerifier()

    @pytest.mark.asyncio
    async def test_tier_1_blacklist_rejection(self, verifier):
        """Mülga/kaldırılmış terim içeren iddiaların Kademe 1'de anında elendiğini doğrula."""
        claim = "Başbakanlık tarafından yayımlanan tüzük gereğince işlem yapılır."
        decision = await verifier.verify_claim(claim, lesson="VATANDASLIK", topic="Yürütme")

        assert decision.verdict == VerificationVerdict.REJECTED
        assert decision.tier_resolved == "TIER_1_BLACKLIST"
        assert "Başbakan" in decision.reason or "başbakan" in decision.reason or "tüzük" in decision.reason
        assert decision.confidence >= 0.95

    @pytest.mark.asyncio
    async def test_tier_2_z3_contradiction_detection(self, verifier):
        """Anayasal sayılarla çelişen (Z3 UNSAT) iddiaların Kademe 2'de yakalandığını doğrula."""
        claim = "Anayasa Mahkemesi toplam 25 üyeden oluşur ve üyelerin görev süresi 5 yıldır."
        decision = await verifier.verify_claim(claim, lesson="VATANDASLIK", topic="Yargı")

        assert decision.verdict in (VerificationVerdict.CONTRADICTION, VerificationVerdict.REJECTED)
        assert decision.tier_resolved == "TIER_2_Z3_LOGIC"
        assert decision.confidence >= 0.95

    @pytest.mark.asyncio
    async def test_tier_3_prosecutor_confirmation(self, verifier):
        """Doğru anayasal bilginin Kademe 1 ve 2'yi geçip Kademe 3'te onaylandığını doğrula."""
        claim = "1982 Anayasası'na göre TBMM 600 milletvekilinden oluşur."

        mock_prosecutor_result = {
            "verdict": "CONFIRMED",
            "confidence": 0.98,
            "explanation": "Madde 75 ile birebir uyumlu.",
            "canonical_truth": "TBMM üye sayısı: 600",
            "trap_distractor": None,
            "thought_process": "Kanonik ambar ile tam örtüşüyor."
        }

        with patch.object(verifier.prosecutor, "audit_claim_deepseek", return_value=mock_prosecutor_result):
            decision = await verifier.verify_claim(claim, lesson="VATANDASLIK", topic="Yasama")

            assert decision.verdict == VerificationVerdict.CONFIRMED
            assert decision.tier_resolved == "TIER_3_PROSECUTOR"
            assert decision.confidence == 0.98

    @pytest.mark.asyncio
    async def test_batch_verify_claims(self, verifier):
        """batch_verify_claims fonksiyonunun çoklu iddiaları sırayla işlediğini doğrula."""
        claims = [
            {"text": "Bakanlar Kurulu kararnamesi ile yürürlüğe girer.", "lesson": "VATANDASLIK", "topic": "Yürütme"},
            {"text": "TBMM toplantı yeter sayısı 200 milletvekilidir.", "lesson": "VATANDASLIK", "topic": "Yasama"}
        ]

        mock_prosecutor_result = {
            "verdict": "CONFIRMED",
            "confidence": 0.95,
            "explanation": "Doğru",
            "canonical_truth": None,
            "trap_distractor": None
        }

        with patch.object(verifier.prosecutor, "audit_claim_deepseek", return_value=mock_prosecutor_result):
            decisions = await verifier.batch_verify_claims(claims)

            assert len(decisions) == 2
            # İlk iddia mülga terim (Kademe 1)
            assert decisions[0].verdict == VerificationVerdict.REJECTED
            assert decisions[0].tier_resolved == "TIER_1_BLACKLIST"
            # İkinci iddia onaylı (Kademe 3)
            assert decisions[1].verdict == VerificationVerdict.CONFIRMED
            assert decisions[1].tier_resolved == "TIER_3_PROSECUTOR"
