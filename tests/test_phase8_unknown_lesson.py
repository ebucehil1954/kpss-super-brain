"""
KPSS Super-Brain: Phase 8 — Bilinmeyen Ders Çözümleme Testleri (Unknown != TARIH)
Master Refactor Plan Phase 8 Kapsamı:
1. test_unknown_lesson_is_unknown: Tanımsız veya anlamsız ders adı UNKNOWN döner.
2. test_non_history_lesson_never_falls_back_to_history: Tarih dışı dersler asla Tarih'e düşürülemez.
3. test_alias_resolution: Türkçe karakterli veya eşanlamlı dersler başarıyla çözümlenir.
"""
import pytest
from curriculum.models import LessonType

def test_unknown_lesson_is_unknown():
    """Phase 8: Bilinmeyen dersler kesinlikle UNKNOWN döner, asla TARIH olmaz."""
    assert LessonType.from_str("Biyoloji") == LessonType.UNKNOWN
    assert LessonType.from_str("Kuantum_Fizigi_101") == LessonType.UNKNOWN
    assert LessonType.from_str("") == LessonType.UNKNOWN
    assert LessonType.from_str(None) == LessonType.UNKNOWN
    assert LessonType.from_str("XYZ_UNKNOWN_LESSON") == LessonType.UNKNOWN

def test_non_history_lesson_never_falls_back_to_history():
    """Phase 8: Tarih dışı dersler veya yabancı alanlar kesinlikle TARIH kategorisine sızamaz."""
    res = LessonType.from_str("Fransizca")
    assert res != LessonType.TARIH
    assert res == LessonType.UNKNOWN

    res2 = LessonType.from_str("Astronomi")
    assert res2 != LessonType.TARIH
    assert res2 == LessonType.UNKNOWN

def test_alias_resolution():
    """Phase 8: Türkçe karakterli, İngilizce veya yaygın takma adlar doğru derse çözülür."""
    assert LessonType.from_str("coğrafya") == LessonType.COGRAFYA
    assert LessonType.from_str("vatandaşlık") == LessonType.VATANDASLIK
    assert LessonType.from_str("anayasa") == LessonType.VATANDASLIK
    assert LessonType.from_str("dil bilgisi") == LessonType.TURKCE
    assert LessonType.from_str("geometri") == LessonType.MATEMATIK
    assert LessonType.from_str("osmanlı") == LessonType.TARIH
