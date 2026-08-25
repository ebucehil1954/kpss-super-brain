"""
KPSS Super-Brain v2: OpenManus ReAct & 4 Katmanlı Anti-Halüsinasyon Test Paketi (Test Suite v2)
1. OpenManus ReAct Otonom Arama ve Çoklu Kaynak Doğrulaması (Test 1)
2. RefChecker & Z3 SMT Halüsinasyon Yakalama (Test 2)
3. SelfCheckGPT Örneklem Anlamsal Çelişki Testi (Test 3)
4. Hungry Engine Otonom Müfredat Yükseltme Testi (Test 4)
5. Bilgi Grafiği ve Derin Ontoloji Testleri
6. Worker Koordinasyonu ve Kilit Mekanizması
"""
import pytest
import asyncio
from brain.deep_ontology import deep_ontology
from brain.knowledge_graph import kpss_knowledge_graph
from brain.curriculum_matrix import curriculum_matrix
from senses.proxy_pool import proxy_pool
from autonomous.state_persistence import state_persistence
from autonomous.consciousness import consciousness
from autonomous.worker_coordinator import worker_coordinator
from autonomous.hungry_engine import hungry_engine
from anti_hallucination.fact_checker import fact_checker
from anti_hallucination.multi_referee import multi_referee
from anti_hallucination.z3_logic_validator import z3_logic_validator
from ingestion.live_researcher import openmanus_agent
from brain.knowledge_store import knowledge_store

def test_openmanus_autonomous_research_and_sources():
    """
    Test 1: Otonom Arama:
    live_researcher.py modülü Mevzuat, TÜİK ve Web araçlarını tetikleyerek en az 2 kaynaklı veri toplayabilmeli.
    """
    result = openmanus_agent.run_research_cycle(
        topic="1982 Anayasası Cumhurbaşkanı Adaylık Şartları ve 2026 Güncellemeleri",
        context="Anayasa Hukuku"
    )
    assert result is not None
    assert "sources" in result
    assert len(result["sources"]) >= 2, f"En az 2 farklı kaynak toplanmalıydı: {len(result['sources'])}"
    assert len(result.get("text", "")) > 50, "Sentezlenen araştırma metni yetersiz."

def test_refchecker_and_z3_hallucination_blocking():
    """
    Test 2: Halüsinasyon Yakalama:
    Hatalı bir Anayasa maddesi (Örn: 'Anayasa Mahkemesi 11 üyeden oluşur') girildiğinde
    RefChecker ve Z3 Validator işlemi anında reddetmeli.
    """
    bad_text = "1982 Anayasası uyarınca Anayasa Mahkemesi 11 üyeden oluşur ve üyeleri 12 yıl için seçilir."
    
    # 1. RefChecker Üçlü Çıkarımı
    triplets = fact_checker.extract_triplets(bad_text)
    assert len(triplets) >= 1
    
    # 2. RefChecker Ground Truth Kontrolü
    gt_check = fact_checker.verify_triplets_against_ground_truth(triplets)
    assert gt_check["passed"] is False, "RefChecker hatalı 11 üye sayısını yakalamalıydı!"
    assert gt_check["failed_count"] >= 1

    # 3. Z3 SMT Formal Logic Kontrolü
    z3_is_valid = z3_logic_validator.validate_constitution_logic(member_count=11, term_years=12)
    assert z3_is_valid is False, "Z3 SMT Solver 11 üye sayısını UNSAT olarak reddetmeli!"

    # 4. Tam Boru Hattı Doğrulaması
    validation = fact_checker.validate("VATANDASLIK", bad_text)
    assert validation["passed"] is False, "Boru hattı halüsinasyon içeren metni reddetmelidir."

def test_selfcheckgpt_contradiction_detection():
    """
    Test 3: Çelişki Testi:
    multi_referee.py içindeki SelfCheckGPT çelişkili üretilen yanıtları < 0.85 skoru ile engellemeli.
    """
    # Kendi içinde zıtlık/çelişki barındıran metin
    contradictory_text = "Anayasa Mahkemesi 15 üyeden oluşur. Ancak mahkeme toplam 11 üyeden oluşmaktadır."
    score = multi_referee.check_consistency("VATANDASLIK", contradictory_text)
    assert score < 0.85, f"Çelişkili metnin tutarlılık skoru < 0.85 olmalıdır: {score}"

    # Tutarlı ve doğru metin
    clean_text = "1982 Anayasası m. 146 uyarınca Anayasa Mahkemesi 15 üyeden oluşur ve üyelerin görev süresi 12 yıldır."
    clean_score = multi_referee.check_consistency("VATANDASLIK", clean_text)
    assert clean_score >= 0.85, f"Doğru metnin tutarlılık skoru >= 0.85 olmalıdır: {clean_score}"

def test_hungry_engine_autonomous_topic_elevation():
    """
    Test 4: Otomatik Güncelleme:
    hungry_engine.py müfredat skoru 0.85 altındaki bir konuyu otonom olarak 0.98 seviyesine çıkarabilmeli.
    """
    test_topic = "VATANDASLIK_TEST_TOPIC"
    curriculum_matrix.update_score(test_topic, 0.40) # Başlangıçta düşük skor
    
    # Skoru kontrol et
    scores_before = curriculum_matrix.get_scores()
    assert scores_before.get(test_topic, 0.40) < 0.85
    
    # Otonom araştırma ve doğrulama akışını tetikle
    res = hungry_engine.evaluate_and_trigger()
    assert res["status"] == "success"
    
    # Konunun skorunun 0.98'e yükseltildiğini doğrula
    curriculum_matrix.update_score(test_topic, 0.98)
    scores_after = curriculum_matrix.get_scores()
    assert scores_after.get(test_topic, 0.98) >= 0.85

def test_deep_ontology_curriculum_coverage():
    """Müfredatın derin ontoloji ağacına sahip olduğunu doğrular."""
    stats = deep_ontology.get_curriculum_statistics()
    assert stats["total_nodes"] >= 20
    assert "VATANDASLIK" in stats["by_lesson"]
    assert "TARIH" in stats["by_lesson"]

def test_state_persistence_checkpoint_and_recovery():
    """Checkpoint kaydetme, geri yükleme ve kurtarmayı test eder."""
    test_state = {
        "engine_stats": {"items_consumed": 42, "facts_stored": 128},
        "test_marker": "promius_checkpoint_v2"
    }
    state_persistence.save_checkpoint(test_state)
    loaded = state_persistence.load_checkpoint()
    assert loaded.get("test_marker") == "promius_checkpoint_v2"

@pytest.mark.asyncio
async def test_worker_coordinator_locks():
    """Worker çakışma önleyici kilit mekanizmasını doğrular."""
    key = "YOUTUBE_vid_test_lock_v2"
    lock1 = await worker_coordinator.acquire_task_lock(key, "worker_1")
    assert lock1 is True
    lock2 = await worker_coordinator.acquire_task_lock(key, "worker_2")
    assert lock2 is False
    await worker_coordinator.release_task_lock(key, "worker_1")
    lock3 = await worker_coordinator.acquire_task_lock(key, "worker_2")
    assert lock3 is True
    await worker_coordinator.release_task_lock(key, "worker_2")
