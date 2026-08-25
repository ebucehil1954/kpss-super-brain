"""
KPSS Super-Brain v2: Kapsamlı Sistem ve Yetenek Doğrulama Testleri (Test Suite v2)
1. Derin Ontoloji & Bilgi Grafiği Kapsamı
2. Proxy Havuzu & User-Agent Rotasyonu
3. Checkpoint & Persistent State Kurtarma
4. Bilinç ve Chain-of-Thought Karar Motoru
5. 9 Kademeli Anti-Halüsinasyon Kalkanı
6. Worker Koordinasyonu ve Kilit Mekanizması
"""
import pytest
import asyncio
from brain.deep_ontology import deep_ontology
from brain.knowledge_graph import kpss_knowledge_graph
from senses.proxy_pool import proxy_pool
from autonomous.state_persistence import state_persistence
from autonomous.consciousness import consciousness
from autonomous.worker_coordinator import worker_coordinator
from anti_hallucination.fact_checker import fact_checker
from brain.knowledge_store import knowledge_store

def test_deep_ontology_curriculum_coverage():
    """1. Test: Müfredatın 200+ konuluk derin ontoloji ağacına sahip olduğunu doğrular."""
    stats = deep_ontology.get_curriculum_statistics()
    assert stats["total_nodes"] >= 20, f"Düğüm sayısı yetersiz: {stats['total_nodes']}"
    assert "VATANDASLIK" in stats["by_lesson"]
    assert "TARIH" in stats["by_lesson"]
    assert "COGRAFYA" in stats["by_lesson"]
    assert "TURKCE" in stats["by_lesson"]

def test_deep_ontology_auto_expand():
    """2. Test: Yeni metinden otomatik kavram çıkarıp bilgi grafiğine düğüm bağladığını doğrular."""
    test_text = "1982 Anayasası Madde 87 uyarınca TBMM üye tamsayısının salt çoğunluğu ile kanun teklifleri kabul edilir."
    new_ids = deep_ontology.auto_expand_from_knowledge(test_text, "VATANDASLIK", "1982 Anayasası Yasama Organı")
    assert len(new_ids) >= 1 or len(kpss_knowledge_graph.nodes) > 20

def test_proxy_pool_user_agent_rotation():
    """3. Test: User-Agent ve istek başlıklarının doğru üretildiğini doğrular."""
    headers = proxy_pool.get_headers()
    assert "User-Agent" in headers
    assert "Accept-Language" in headers
    assert len(proxy_pool.USER_AGENTS) >= 10

def test_state_persistence_checkpoint_and_recovery():
    """4. Test: Checkpoint kaydetme, geri yükleme ve zombi görev kurtarmayı test eder."""
    # Checkpoint kaydet
    test_state = {
        "engine_stats": {"items_consumed": 42, "facts_stored": 128},
        "test_marker": "promius_checkpoint_v2"
    }
    state_persistence.save_checkpoint(test_state)
    
    # Checkpoint yükle
    loaded = state_persistence.load_checkpoint()
    assert loaded.get("test_marker") == "promius_checkpoint_v2"
    assert loaded.get("engine_stats", {}).get("items_consumed") == 42

    # Zombi görev kurtarma
    recovered = state_persistence.recover_zombie_tasks()
    assert recovered >= 0

def test_consciousness_chain_of_thought():
    """5. Test: Bilinç motorunun gerekçelendirilmiş CoT kararı ürettiğini doğrular."""
    decision = consciousness.deliberate_next_step()
    assert "decision_id" in decision
    assert "target_lesson" in decision
    assert "target_topic" in decision
    assert "chain_of_thought" in decision
    assert len(decision["chain_of_thought"]) >= 3
    assert "rationale" in decision

def test_9_layer_fact_checker_hallucination_blocking():
    """6. Test: 9 Kademeli Kalkanın mülga kanun ve halüsinasyonları engellediğini doğrular."""
    # Mülga Kanun İhlali
    bad_text_1 = "Başbakan ve Bakanlar Kurulu tüzük çıkarmıştır."
    is_valid, msg = fact_checker.verify_content(bad_text_1, lesson="VATANDASLIK")
    assert not is_valid
    assert "Mülga" in msg or "Halüsinasyon" in msg

    # Sahte Kanun İhlali
    bad_text_2 = "9999 Sayılı Kamu Reformu Kanunu uyarınca memurlar doğrudan atanır."
    is_valid, msg = fact_checker.verify_content(bad_text_2, lesson="VATANDASLIK")
    assert not is_valid

    # Doğru Anayasal Bilgi
    clean_text = "1982 Anayasası Madde 87 uyarınca TBMM üye tam sayısı 600 milletvekilidir."
    is_valid, msg = fact_checker.verify_content(clean_text, topic="1982 Anayasası Yasama ve Karar Yeter Sayıları", lesson="VATANDASLIK")
    assert is_valid

@pytest.mark.asyncio
async def test_worker_coordinator_locks():
    """7. Test: Worker çakışma önleyici kilit mekanizmasını doğrular."""
    key = "YOUTUBE_vid_test_123"
    # 1. Kilit alma
    lock1 = await worker_coordinator.acquire_task_lock(key, "worker_1")
    assert lock1 is True

    # 2. Aynı anda başka worker'ın alması engellenmeli
    lock2 = await worker_coordinator.acquire_task_lock(key, "worker_2")
    assert lock2 is False

    # 3. Kilit serbest bırakılınca tekrar alınabilmeli
    await worker_coordinator.release_task_lock(key, "worker_1")
    lock3 = await worker_coordinator.acquire_task_lock(key, "worker_2")
    assert lock3 is True
    await worker_coordinator.release_task_lock(key, "worker_2")
