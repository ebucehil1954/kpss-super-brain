"""
KPSS Super-Brain: Phase 15 — Orkestrasyon ve Geri Basınç (Backpressure) Testleri
Master Refactor Plan Phase 15 Kapsamı:
1. test_worker_pool_respects_backpressure: İşçi havuzu kapasite sınırını aşamaz, geri basınç uygular.
2. test_duplicate_task_is_not_reprocessed: Aynı anda çalışan veya kilitli olan görev mükerrer işlenemez.
3. test_system_shuts_down_cleanly: Kapanış sinyali verildiğinde yeni iş alımı durdurulur ve temiz kapanır.
"""
import pytest
import asyncio
from autonomous.worker_coordinator import WorkerCoordinator

@pytest.mark.asyncio
async def test_worker_pool_respects_backpressure():
    """Phase 15: Havuz limiti 2 iken 3. görev geri basınç nedeniyle kilit alamaz."""
    coord = WorkerCoordinator(max_concurrent=2)

    # 1. ve 2. görevler kilit alır
    ok1 = await coord.acquire_task_lock("task_01", "worker_1")
    ok2 = await coord.acquire_task_lock("task_02", "worker_2")
    assert ok1 is True
    assert ok2 is True

    # 3. görev geri basınç nedeniyle reddedilir
    assert coord.can_accept_work() is False
    ok3 = await coord.acquire_task_lock("task_03", "worker_3")
    assert ok3 is False, "Maksimum worker sınırı aşıldığında geri basınç (backpressure) uygulanmalıdır!"

    # 1. görev tamamlanıp bırakılır
    await coord.release_task_lock("task_01", "worker_1")
    assert coord.can_accept_work() is True

    # Artık 3. görev yer bulabilir
    ok3_retry = await coord.acquire_task_lock("task_03", "worker_3")
    assert ok3_retry is True

@pytest.mark.asyncio
async def test_duplicate_task_is_not_reprocessed():
    """Phase 15: Aynı görev anahtarı (task_key) mükerrer olarak iki işçiye verilemez."""
    coord = WorkerCoordinator(max_concurrent=4)

    # İşçi 1 kilit alır
    got_lock = await coord.acquire_task_lock("vid_osmanli_01", "worker_1")
    assert got_lock is True

    # İşçi 2 aynı video_id'yi işlemeye çalışırsa engellenir
    duplicate_lock = await coord.acquire_task_lock("vid_osmanli_01", "worker_2")
    assert duplicate_lock is False, "Aynı görev anahtarı aynı anda mükerrer işlenemez!"

@pytest.mark.asyncio
async def test_system_shuts_down_cleanly():
    """Phase 15: Kapanış sinyali (shutdown) tetiklendiğinde yeni görev alımı durdurulur."""
    coord = WorkerCoordinator(max_concurrent=4)
    coord.trigger_shutdown()

    assert coord.is_shutting_down is True
    assert coord.can_accept_work() is False

    got_lock = await coord.acquire_task_lock("new_task_after_shutdown", "worker_1")
    assert got_lock is False, "Kapanış sinyali verildiğinde koordinatör yeni kilit dağıtamaz!"
