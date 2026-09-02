"""
KPSS Super-Brain: Phase 10 — Bilgi Grafiği Döngü ve Geçişlilik Testleri
Master Refactor Plan Phase 10 Kapsamı:
1. test_cycle_is_rejected_on_hierarchical_edges: Hiyerarşik kenarlarda döngü oluşumu ValueError fırlatır.
2. test_confidence_decays_across_multi_hop_inference: Çok sekmeli çıkarımlarda güven skoru her adımda erir.
3. test_non_transitive_relations_do_not_chain: Geçişsiz ilişkiler (ASSOCIATED_WITH, CONTRADICTS) zincirlenemez.
"""
import pytest
import os
import tempfile
from brain.knowledge_graph import KPSSKnowledgeGraph

@pytest.fixture
def clean_graph():
    """Geçici bir dosyada yalıtılmış KPSSKnowledgeGraph oluşturur."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    kg = KPSSKnowledgeGraph(storage_path=path)
    kg.nodes = {}
    kg.edges = []
    yield kg
    if os.path.exists(path):
        os.remove(path)

def test_cycle_is_rejected_on_hierarchical_edges(clean_graph):
    """Phase 10: Hiyerarşik kenarlarda (IS_A, PART_OF) döngü kesinlikle reddedilir."""
    kg = clean_graph
    kg.add_node("A", "Kavram A", "ENTITY", "TARIH")
    kg.add_node("B", "Kavram B", "ENTITY", "TARIH")
    kg.add_node("C", "Kavram C", "ENTITY", "TARIH")

    # A -> B -> C (Hiyerarşik: SUBTOPIC_OF)
    kg.add_edge("A", "B", "SUBTOPIC_OF")
    kg.add_edge("B", "C", "SUBTOPIC_OF")

    # C -> A kenarı döngü yaratacağından ValueError fırlatmalıdır!
    with pytest.raises(ValueError) as exc:
        kg.add_edge("C", "A", "SUBTOPIC_OF")
    assert "Döngü Tespit Edildi" in str(exc.value)

def test_confidence_decays_across_multi_hop_inference(clean_graph):
    """Phase 10: Çok adımlı geçişli çıkarımlarda güven skoru her adımda azalır."""
    kg = clean_graph
    kg.add_node("N1", "Düğüm 1", "ENTITY", "VATANDASLIK")
    kg.add_node("N2", "Düğüm 2", "ENTITY", "VATANDASLIK")
    kg.add_node("N3", "Düğüm 3", "ENTITY", "VATANDASLIK")
    kg.add_node("N4", "Düğüm 4", "ENTITY", "VATANDASLIK")

    kg.add_edge("N1", "N2", "IS_A")
    kg.add_edge("N2", "N3", "IS_A")
    kg.add_edge("N3", "N4", "IS_A")

    # 1 adım: N1 -> N2
    path_1 = kg.infer_relation_path("N1", "N2")
    assert path_1 is not None
    conf_1 = path_1["confidence"]

    # 3 adım: N1 -> N4
    path_3 = kg.infer_relation_path("N1", "N4")
    assert path_3 is not None
    conf_3 = path_3["confidence"]

    # Adım sayısı arttıkça güven skoru düşmelidir (Confidence Decay)
    assert conf_3 < conf_1, f"Güven skoru erimelidir: {conf_3} < {conf_1}"
    assert conf_3 <= 0.85 * 0.85

def test_non_transitive_relations_do_not_chain(clean_graph):
    """Phase 10: Geçişsiz ilişkiler (ASSOCIATED_WITH) zincirleme çıkarım yapamaz."""
    kg = clean_graph
    kg.add_node("X", "Kavram X", "ENTITY", "COGRAFYA")
    kg.add_node("Y", "Kavram Y", "ENTITY", "COGRAFYA")
    kg.add_node("Z", "Kavram Z", "ENTITY", "COGRAFYA")

    # X ASSOCIATED_WITH Y ve Y ASSOCIATED_WITH Z
    kg.add_edge("X", "Y", "ASSOCIATED_WITH")
    kg.add_edge("Y", "Z", "ASSOCIATED_WITH")

    # Geçişsiz olduğu için X'ten Z'ye çıkarım yolu bulunmamalıdır
    res = kg.infer_relation_path("X", "Z")
    assert res is None, "Geçişsiz (Non-transitive) ilişkiler zincirleme akıl yürütme üretemez!"
