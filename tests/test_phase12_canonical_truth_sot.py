"""
KPSS Super-Brain: Phase 12 — Kanonik Tek Gerçek Kaynağı Testleri (Single Source of Truth)
Master Refactor Plan Phase 12 Kapsamı:
1. test_derived_stores_rebuild_from_canonical: Türetilmiş depolar (FTS, Vektör) kanonik veritabanından yeniden inşa edilir.
2. test_vector_memory_cannot_outlive_deleted_canonical: Silinen kanonik bilginin vektör kopyası da silinir.
3. test_graph_derives_strictly_from_canonical: Graf ve FTS türetilmiş depolardır, kanonikten beslenir.
"""
import pytest
from brain.knowledge_store import knowledge_store
from brain.vector_memory import VectorMemoryStore
from brain.database import db_session

def test_derived_stores_rebuild_from_canonical():
    """Phase 12: Kanonik veritabanından tüm türetilmiş depolar deterministik olarak yeniden üretilir."""
    # Kanonik bir kayıt ekle
    rec = knowledge_store.add_record(
        text="Anayasa Mahkemesi 15 üyeden oluşur.",
        record_type="FACT",
        lesson="VATANDASLIK",
        topic="Anayasa Yargısı",
        confidence=0.98
    )
    rec_id = rec["record_id"]

    # Yeniden inşa et
    rebuild_stats = knowledge_store.rebuild_derived_stores()
    assert rebuild_stats["canonical_records"] > 0
    assert rebuild_stats["fts_indexed"] == rebuild_stats["canonical_records"]

    # FTS üzerinden doğrulanır
    results = knowledge_store.search("Anayasa Mahkemesi")
    assert any(r["record_id"] == rec_id for r in results)

def test_vector_memory_cannot_outlive_deleted_canonical():
    """Phase 12: Kanonik tablodan silinen kayıt vektör belleğinde yaşayamaz."""
    rec = knowledge_store.add_record(
        text="TBMM Genel Sekreterliği idari teşkilat yapısı.",
        record_type="FACT",
        lesson="VATANDASLIK",
        topic="TBMM Teşkilat",
        confidence=0.92
    )
    rec_id = rec["record_id"]

    vm = VectorMemoryStore()
    vm.add_memory(doc_id=rec_id, text=rec["text"] if "text" in rec else "TBMM Genel Sekreterliği", lesson="VATANDASLIK", topic="TBMM Teşkilat", source="test")

    # Vektörde var olduğu teyit edilir
    doc_exists = any(d["id"] == rec_id for d in vm.documents)
    assert doc_exists is True

    # Kanonik kayıt silinir
    knowledge_store.delete_record(rec_id)

    # Vektör belleği kontrol edilir: Artık bulunmamalıdır
    vm_after = VectorMemoryStore()
    doc_after = any(d["id"] == rec_id for d in vm_after.documents)
    assert doc_after is False, "Silinmiş kanonik kayıt vektör deposunda kalamaz!"

def test_graph_derives_strictly_from_canonical():
    """Phase 12: Kanonik kayıt silindiğinde FTS aramasından da anında düşer."""
    rec = knowledge_store.add_record(
        text="Sayıştay TBMM adına kamu idarelerini denetler.",
        record_type="FACT",
        lesson="VATANDASLIK",
        topic="Sayıştay Denetimi",
        confidence=0.95
    )
    rec_id = rec["record_id"]

    # Arama sonuçlarında var
    res1 = knowledge_store.search("Sayıştay TBMM adına")
    assert any(r["record_id"] == rec_id for r in res1)

    # Sil
    knowledge_store.delete_record(rec_id)

    # Arama sonuçlarından silinmiş olmalıdır
    res2 = knowledge_store.search("Sayıştay TBMM adına")
    assert not any(r["record_id"] == rec_id for r in res2)
