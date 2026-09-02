"""
KPSS Super-Brain: Phase 3 — Güven ve Tekrar Semantiği Testleri (Repetition != Truth)
Master Refactor Plan Phase 3 Kapsamı:
1. test_repetition_does_not_increase_trust: Aynı iddiayı tekrar etmek güven skorunu artıramaz.
2. test_same_source_repetition_is_not_independent: Aynı kaynaktan gelen tekrarlar bağımsız doğrulama sayılmaz.
3. test_independent_sources_can_increase_trust: Farklı bağımsız öğretmenler teyit ettiğinde güven artabilir.
4. test_conflicting_evidence_reduces_or_blocks_trust: Çelişkili kanıt güven skorunu düşürür ve kısıtlar.
"""
import pytest
from brain.knowledge_store import knowledge_store
from brain.database import db_session

@pytest.fixture(autouse=True)
def clean_phase3_test_records():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM knowledge_records WHERE topic IN ('TBMM Toplantı Karar', 'TBMM Karar Sayıları', 'Normlar Hiyerarşisi', 'Eski Hüküm Çelişkisi')")
        cursor.execute("DELETE FROM knowledge_fts WHERE topic IN ('TBMM Toplantı Karar', 'TBMM Karar Sayıları', 'Normlar Hiyerarşisi', 'Eski Hüküm Çelişkisi')")
    yield
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM knowledge_records WHERE topic IN ('TBMM Toplantı Karar', 'TBMM Karar Sayıları', 'Normlar Hiyerarşisi', 'Eski Hüküm Çelişkisi')")
        cursor.execute("DELETE FROM knowledge_fts WHERE topic IN ('TBMM Toplantı Karar', 'TBMM Karar Sayıları', 'Normlar Hiyerarşisi', 'Eski Hüküm Çelişkisi')")

def test_repetition_does_not_increase_trust():
    """Phase 3: Aynı kaynaktan gelen tekrar sadece repeat_count artırır, trust_score artırmaz."""
    text = "TBMM Genel Kurulu toplantı yeter sayısı 200 milletvekilidir."
    lesson = "VATANDASLIK"
    topic = "TBMM Toplantı Karar"

    # 1. İlk kayıt
    src1 = {"source_id": "vid_repeat_01", "speaker_or_author": "Hoca A"}
    r1 = knowledge_store.add_or_reinforce_record(
        text=text, record_type="FACT", lesson=lesson, topic=topic, confidence=0.85, source=src1
    )
    initial_conf = r1["confidence"]

    # 2. Aynı kaynaktan 2. tekrar
    r2 = knowledge_store.add_or_reinforce_record(
        text=text, record_type="FACT", lesson=lesson, topic=topic, confidence=0.85, source=src1
    )
    # Tekrar sayısı artmalı
    assert r2["times_reinforced"] == 2
    # Güven skoru değişmemeli (Repetition != Truth)
    assert r2["confidence"] == initial_conf

def test_same_source_repetition_is_not_independent():
    """Phase 3: Aynı hocanın farklı bir videosu dahi bağımsız hoca teyidi sayılamaz."""
    text = "Karar yeter sayısı hiçbir şekilde 151'den az olamaz."
    lesson = "VATANDASLIK"
    topic = "TBMM Karar Sayıları"

    # İlk kayıt: Hoca A
    src1 = {"source_id": "vid_hoca_a_1", "speaker_or_author": "Emrah Vahap"}
    r1 = knowledge_store.add_or_reinforce_record(
        text=text, record_type="FACT", lesson=lesson, topic=topic, confidence=0.90, source=src1
    )

    # İkinci kayıt: Yine Emrah Vahap (farklı video olsa bile aynı hoca)
    src2 = {"source_id": "vid_hoca_a_2", "speaker_or_author": "Emrah Vahap"}
    r2 = knowledge_store.add_or_reinforce_record(
        text=text, record_type="FACT", lesson=lesson, topic=topic, confidence=0.90, source=src2
    )

    assert r2["times_reinforced"] == 2
    assert r2["confidence"] == r1["confidence"], "Aynı öğretmenin tekrarı güven skorunu yükseltemez!"

def test_independent_sources_can_increase_trust():
    """Phase 3: Gerçekten BAĞIMSIZ yeni bir öğretmen/resmi kaynak teyit ettiğinde güven skoru artabilir."""
    text = "Cumhurbaşkanı kararnamesi ile kanun çelişirse kanun hükümleri uygulanır."
    lesson = "VATANDASLIK"
    topic = "Normlar Hiyerarşisi"

    # Kayıt 1: Hoca A
    src1 = {"source_id": "vid_hoca_1", "speaker_or_author": "Hakan Bileyen"}
    r1 = knowledge_store.add_or_reinforce_record(
        text=text, record_type="FACT", lesson=lesson, topic=topic, confidence=0.88, source=src1
    )

    # Kayıt 2: Farklı ve bağımsız Hoca B
    src2 = {"source_id": "vid_hoca_2", "speaker_or_author": "Esra Özkan"}
    r2 = knowledge_store.add_or_reinforce_record(
        text=text, record_type="FACT", lesson=lesson, topic=topic, confidence=0.88, source=src2
    )

    assert r2["times_reinforced"] == 2
    assert r2["confidence"] > r1["confidence"], "Bağımsız yeni bir hoca teyidi güven skorunu artırmalıdır!"

def test_conflicting_evidence_reduces_or_blocks_trust():
    """Phase 3: Çelişkili veya ihtilaflı kanıt geldiğinde güven skoru derhal düşürülür."""
    text = "TBMM üye tamsayısı 550 milletvekilidir."
    lesson = "VATANDASLIK"
    topic = "Eski Hüküm Çelişkisi"

    # Kayıt 1: Yanlışlıkla yüksek güvenle eklendi
    src1 = {"source_id": "vid_old_1", "speaker_or_author": "Eski Kayıt"}
    r1 = knowledge_store.add_or_reinforce_record(
        text=text, record_type="FACT", lesson=lesson, topic=topic, confidence=0.90, source=src1
    )

    # Kayıt 2: Çelişki / İhtilaf tespit edildi
    src_conflict = {"source_id": "vid_check_2", "speaker_or_author": "Denetleyici", "is_conflicting": True}
    r2 = knowledge_store.add_or_reinforce_record(
        text=text, record_type="FACT", lesson=lesson, topic=topic, confidence=0.90, source=src_conflict,
        tags=["disputed", "conflict"]
    )

    assert r2["confidence"] < 0.50, "Çelişki tespit edilen bilginin güven skoru 0.50 altına inmelidir!"
