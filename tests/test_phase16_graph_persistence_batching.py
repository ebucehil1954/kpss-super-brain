"""
KPSS Super-Brain: Phase 16 — Bilgi Grafiği Atomik Kalıcılık ve Batch Testleri
Master Refactor Plan Phase 16 Kapsamı:
1. test_atomic_write_prevents_partial_graph: Dosya yazımı geçici dosya ve os.replace ile atomiktir.
2. test_batch_edge_insertion_is_atomic: Batch kenar eklemesinde tek bir hata tüm grubu iptal eder (rollback).
3. test_debounced_save_reduces_io: Dirty flag sayesinde gereksiz disk yazımları engellenir.
"""
import pytest
import os
import tempfile
import json
from brain.knowledge_graph import KPSSKnowledgeGraph

@pytest.fixture
def temp_kg():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    kg = KPSSKnowledgeGraph(storage_path=path)
    kg.nodes = {}
    kg.edges = []
    kg.save(force=True)
    yield kg
    if os.path.exists(path):
        os.remove(path)

def test_atomic_write_prevents_partial_graph(temp_kg):
    """Phase 16: save() işlemi geçerli ve hatasız JSON formatında atomik kayıt üretir."""
    kg = temp_kg
    kg.add_node("NODE_1", "Test Düğüm 1", "ENTITY", "TARIH")
    kg.add_node("NODE_2", "Test Düğüm 2", "ENTITY", "TARIH")

    # Dosyanın diskte tam ve geçerli JSON olduğunu doğrula
    assert os.path.exists(kg.storage_path)
    with open(kg.storage_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "NODE_1" in data["nodes"]
        assert "NODE_2" in data["nodes"]

def test_batch_edge_insertion_is_atomic(temp_kg):
    """Phase 16: Toplu kenar eklemesinde tek bir döngü hatası tüm batch'i geri alır (atomik rollback)."""
    kg = temp_kg
    kg.add_node("A", "Düğüm A", "ENTITY", "VATANDASLIK")
    kg.add_node("B", "Düğüm B", "ENTITY", "VATANDASLIK")
    kg.add_node("C", "Düğüm C", "ENTITY", "VATANDASLIK")

    # Mevcut kenar: A -> B (SUBTOPIC_OF)
    kg.add_edge("A", "B", "SUBTOPIC_OF")
    initial_edge_count = len(kg.edges)

    # Batch: B -> C (geçerli) ve C -> A (döngü hatası!)
    batch = [
        {"source": "B", "target": "C", "relation": "SUBTOPIC_OF"},
        {"source": "C", "target": "A", "relation": "SUBTOPIC_OF"} # DÖNGÜ!
    ]

    with pytest.raises(ValueError) as exc:
        kg.batch_edge_insertion_atomic(batch)
    assert "Batch Atomic Hata" in str(exc.value)

    # Hiçbir yeni kenar eklenmemiş olmalıdır (Rollback korundu)
    assert len(kg.edges) == initial_edge_count
    assert not any(e["source"] == "B" and e["target"] == "C" for e in kg.edges)

def test_debounced_save_reduces_io(temp_kg):
    """Phase 16: Dirty bayrağı yokken çağrılan save() disk I/O yapmaz."""
    kg = temp_kg
    kg._dirty = False
    initial_saves = kg._save_count

    # Dirty olmadığı için save çağrısı disk yazımını atlar
    kg.save()
    assert kg._save_count == initial_saves

    # Değişiklik yapıldığında dirty = True olur ve yazılır
    kg.add_node("X1", "Etiket", "ENTITY", "TURKCE")
    assert kg._save_count > initial_saves
