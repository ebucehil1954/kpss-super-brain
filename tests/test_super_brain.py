"""
KPSS Super-Brain: Otonom Zeka & %0 Halüsinasyon Doğrulama Test Paketi (Pytest Suite v3)
Tüm güvenlik kalkanlarının, hakem heyetinin, Z3 sözel mantık çözücüsünün ve açgözlü öncelik kuyruğunun testleri.
"""
import pytest
import os
import sys

# Test klasöründen üst modüllere erişim
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from brain.blacklist_rules import BlacklistAuditor
from anti_hallucination.citation_validator import citation_validator
from anti_hallucination.temporal_validator import temporal_validator
from anti_hallucination.numerical_validator import numerical_validator
from anti_hallucination.z3_logic_validator import z3_logic_validator
from anti_hallucination.fact_checker import fact_checker
from anti_hallucination.semantic_contradiction_detector import semantic_contradiction_detector
from anti_hallucination.multi_referee import multi_referee
from autonomous.priority_queue import priority_queue
from generators.mnemonic_engine import mnemonic_engine
from generators.full_exam_composer import full_exam_composer

def test_blacklist_repealed_terms():
    """2017 Anayasa Değişikliği mülga kavramlarının engellendiğini test eder."""
    bad_texts = [
        "Başbakanlık genelgesi ile yeni düzenleme yapılmıştır.",
        "TBMM Bakanlar Kurulu tüzük çıkarmıştır.",
        "Milletvekilleri gensoru önergesi vermiştir.",
        "Kanun tasarısı Meclis Başkanlığına sunulmuştur.",
        "Askeri Yargıtay bu konuda karar vermiştir."
    ]
    for text in bad_texts:
        is_clean, violations = BlacklistAuditor.audit_text(text)
        assert not is_clean, f"Engellenmesi gereken mülga terim geçti: '{text}'"
        assert len(violations) > 0

def test_blacklist_foreign_language_leaks():
    """Türkçe KPSS metinlerine sızan İngilizce terimlerin engellendiğini test eder."""
    bad_texts = [
        "Grand National Assembly toplantı yeter sayısı 200'dür.",
        "According to Article 75 of Constitution of Turkey...",
        "The President has issued a new decree."
    ]
    for text in bad_texts:
        is_clean, violations = BlacklistAuditor.audit_text(text)
        assert not is_clean, f"İngilizce sızıntı engellenemedi: '{text}'"

def test_fake_law_citation_validation():
    """Uydurma/sahte kanun isimlerinin (örn: İdare Hukuku Kanunu) engellendiğini test eder."""
    fake_law_texts = [
        "İdare Hukuku Kanunu'nun 34. maddesi uyarınca yetki devri yapılmıştır.",
        "İdari Teşkilat Kanunu hükümlerine göre hareket edilir.",
        "Anayasa Hukuku Kanunu m. 12 düzenlemesi mevcuttur.",
        "Vatandaşlık Kanunnamesi hükmü uygulanır."
    ]
    for text in fake_law_texts:
        is_clean, violations = citation_validator.validate_text(text)
        assert not is_clean, f"Sahte kanun adı engellenemedi: '{text}'"
        assert any("Uydurma/Sahte Kanun" in v for v in violations)

def test_temporal_anakronizm_validation():
    """Tarihsel dönem kaymalarının ve yanlış padişah ıslahatlarının engellendiğini test eder."""
    bad_history_texts = [
        "19. yüzyıl Osmanlı'sında Lale Devri (1839-1876) önemli bir dönemdir.",
        "Lale Devri'nde Nizam-ı Cedit ordusu kurularak askeri ıslahat yapılmıştır.",
        "Nizam-ı Cedit dönemi III. Ahmet tarafından başlatılmıştır."
    ]
    for text in bad_history_texts:
        is_clean, violations = temporal_validator.validate_historical_text(text)
        assert not is_clean, f"Tarihsel anakronizm engellenemedi: '{text}'"

def test_numerical_quorum_validator():
    """Deterministik sayısal ve anayasal oran denetimini test eder."""
    bad_numbers = [
        "1982 Anayasası'na göre TBMM 550 milletvekilinden oluşur.",
        "TBMM toplantı yeter sayısı en az 151 milletvekilidir.",
        "TBMM seçimlerin yenilenmesine 200 milletvekili ile karar verebilir.",
        "Anayasa Mahkemesi 17 üyeden kurulur.",
        "Milletvekili seçilme yaşı 25'tir."
    ]
    for text in bad_numbers:
        is_clean, violations = numerical_validator.validate_numbers(text)
        assert not is_clean, f"Hatalı sayısal veri engellenemedi: '{text}'"
        assert len(violations) > 0

def test_z3_verbal_logic_satisfiable():
    """Z3 Sözel Mantık kısıt çözücüsünün tutarlı senaryolardaki başarısını test eder."""
    valid_scenario = "Ahmet, Burak ve Ceyda 1, 2 ve 3. sıralarda oturmaktadır."
    valid_clues = [
        "Ahmet 3. sırada değildir.",
        "Burak Ceyda'nın hemen önündedir.",
        "Ceyda 3. sıradadır."
    ]
    is_valid, msg = z3_logic_validator.validate_verbal_logic_puzzle(valid_scenario, valid_clues)
    assert is_valid, f"Geçerli sözel mantık senaryosu reddedildi: {msg}"

def test_z3_verbal_logic_contradiction_detection():
    """Z3 Sözel Mantık çözücüsünün çelişkili (çözümsüz/UNSAT) soruları yakaladığını test eder."""
    contradictory_scenario = "Ahmet, Burak ve Ceyda 1, 2 ve 3. sıralarda oturmaktadır."
    contradictory_clues = [
        "Ahmet 1. sırada değildir.",
        "Burak Ceyda'nın hemen önündedir.",
        "Ceyda 3. sıradadır." # Bu durumda Burak=2, Ahmet zorunlu 1 olur; ama öncül 1 Ahmet 1. sırada değildir diyor -> ÇELİŞKİ!
    ]
    is_valid, msg = z3_logic_validator.validate_verbal_logic_puzzle(contradictory_scenario, contradictory_clues)
    assert not is_valid, "Çelişkili sözel mantık senaryosu onaylanmamalıydı!"
    assert "UNSAT" in msg or "çelişiyor" in msg or "0 geçerli tablo" in msg

def test_mnemonic_structure_and_phonetics():
    """Akrostiş şifrelerinde harf sayısı ve baş harf uyumunu test eder."""
    # Geçersiz akrostiş (Harf sayısı uyuşmuyor: Kod 6 harf, satır 4)
    invalid_mnemonic = {
        "code": "KADERİ",
        "breakdown": [
            {"letter": "K", "word": "Kastamonu"},
            {"letter": "A", "word": "Artvin"},
            {"letter": "D", "word": "Diyarbakır"},
            {"letter": "E", "word": "Elazığ"}
        ]
    }
    is_valid, msg = mnemonic_engine._validate_mnemonic_structure(invalid_mnemonic)
    assert not is_valid, "Harf sayısı eksik akrostiş onaylanmamalı!"

    # Geçerli akrostiş
    valid_mnemonic = {
        "code": "KADER",
        "breakdown": [
            {"letter": "K", "word": "Kastamonu (Küre)"},
            {"letter": "A", "word": "Artvin (Murgul)"},
            {"letter": "D", "word": "Diyarbakır (Ergani)"},
            {"letter": "E", "word": "Elazığ (Maden)"},
            {"letter": "R", "word": "Rize (Çayeli)"}
        ]
    }
    is_valid_ok, ok_msg = mnemonic_engine._validate_mnemonic_structure(valid_mnemonic)
    assert is_valid_ok, f"Geçerli akrostiş reddedildi: {ok_msg}"

def test_fact_checker_unified_defense():
    """FactChecker'ın 7 kademeli kalkanını test eder."""
    bad_combined_question = (
        "19. yüzyıl Lale Devri reformları sırasında İdare Hukuku Kanunu'na göre "
        "Başbakan ve Bakanlar Kurulu tüzük çıkarmıştır. TBMM üye tamsayısı ise 550'dir."
    )
    is_clean, reason = fact_checker.verify_content(bad_combined_question)
    assert not is_clean, "Tüm güvenlik ihlallerini barındıran metin FactChecker'dan geçmemeli!"
    assert any(x in reason for x in ["Mülga/Kaldırılmış Terim", "Uydurma/Sahte Kanun", "Anakronizm", "Sayısal Bilgi Yanılgısı"])

def test_dynamic_priority_queue():
    """Açgözlü öncelik kuyruğunun çalıştığını ve sıraladığını test eder."""
    pq = priority_queue
    pq.enqueue("YOUTUBE", "VATANDASLIK", "TBMM Karar Sayıları", {"id": "1"}, base_priority=80.0)
    pq.enqueue("WEB_ACADEMIC", "TARIH", "Lale Devri", {"id": "2"}, base_priority=95.0)
    
    item = pq.dequeue()
    assert item is not None
    assert item["lesson"] == "TARIH" # 95.0 priority comes first

@pytest.mark.asyncio
async def test_multi_referee_audit():
    """Çoklu hakem çift-kör denetim sistemini test eder."""
    sample_question = {
        "stem": "1982 Anayasası'na göre TBMM'nin seçimlerin yenilenmesine karar verebilmesi için gerekli üye çoğunluğu hangisidir?",
        "options": {
            "A": "Salt Çoğunluk",
            "B": "Üye tamsayısının beşte üç çoğunluğu (360)",
            "C": "Üye tamsayısının üçte iki çoğunluğu (400)",
            "D": "En az 151 milletvekili"
        },
        "expected_answer": "B"
    }
    is_approved, report, details = await multi_referee.audit_question_triple_blind(sample_question)
    assert is_approved, f"Hakem denetimi başarısız: {report}"
    assert details["consensus_rate"] >= 0.6
