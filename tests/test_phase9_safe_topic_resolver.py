"""
KPSS Super-Brain: Phase 9 — Güvenli Konu Eşleyici Testleri (Safe Topic Resolver)
Master Refactor Plan Phase 9 Kapsamı:
1. test_exact_topic_resolution: Tam topic_id veya tam konu adı hatasız çözülür.
2. test_alias_topic_resolution: Kanonik alt konu eşleşmeleri doğru konuya yönlenir.
3. test_ambiguous_topic_returns_unknown: Belirsiz veya alakasız başlıklar None döner.
4. test_wrong_topic_is_not_silently_selected: Yanlış bir konu sessizce seçilemez.
"""
import pytest
from brain.curriculum_matrix import curriculum_matrix

def test_exact_topic_resolution():
    """Phase 9: Tam topic_id veya tam resmi konu adı tam eşleşir."""
    # Tam topic_id ile
    res1 = curriculum_matrix.resolve_topic_safely("VATANDASLIK", "VATANDASLIK_TEMEL_HUKUK_KAVRAMLARI")
    assert res1 == "VATANDASLIK_TEMEL_HUKUK_KAVRAMLARI"

    # Tam isim ile
    res2 = curriculum_matrix.resolve_topic_safely("VATANDASLIK", "Temel Hukuk Kavramları")
    assert res2 == "VATANDASLIK_TEMEL_HUKUK_KAVRAMLARI"

    # Tarih tam isim ile
    res3 = curriculum_matrix.resolve_topic_safely("TARIH", "İslamiyet Öncesi Türk Tarihi ve Kültür-Medeniyeti")
    assert res3 == "TARIH_ILK_TURK_DEVLETLERI"

def test_alias_topic_resolution():
    """Phase 9: Belirgin kanonik alt konular ana konuya çözümlenir."""
    # "İskitler" -> İslamiyet Öncesi Türk Tarihi
    res = curriculum_matrix.resolve_topic_safely("TARIH", "İskitler (Sakalar)")
    assert res == "TARIH_ILK_TURK_DEVLETLERI"

    # "Talas Savaşı" -> İlk Türk İslam Devletleri
    res2 = curriculum_matrix.resolve_topic_safely("TARIH", "Talas Savaşı ve Türklerin İslamlaşması")
    assert res2 == "TARIH_ILK_TURK_ISLAM_DEVLETLERI"

def test_ambiguous_topic_returns_unknown():
    """Phase 9: Belirsiz, yabancı veya alakasız metinler None döner."""
    assert curriculum_matrix.resolve_topic_safely("VATANDASLIK", "xyz_alakasiz_sey") is None
    assert curriculum_matrix.resolve_topic_safely("TARIH", "123") is None
    assert curriculum_matrix.resolve_topic_safely("COGRAFYA", "") is None
    assert curriculum_matrix.resolve_topic_safely("COGRAFYA", "Fransa Şehirleri") is None

def test_wrong_topic_is_not_silently_selected():
    """Phase 9: Coğrafya konusu Vatandaşlık dersi içinde yanlış bir konuya eşlenemez."""
    # Coğrafya konusu Vatandaşlık'a sorulursa None dönmeli (sessizce rastgele vatandaşlık konusu olamaz!)
    res = curriculum_matrix.resolve_topic_safely("VATANDASLIK", "Türkiye'nin Dağları ve Platoları")
    assert res is None
