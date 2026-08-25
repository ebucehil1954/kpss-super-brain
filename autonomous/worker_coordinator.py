"""
KPSS Super-Brain: Paralel Worker Koordinatörü ve Kilit Yöneticisi (Worker Coordinator v3)
Paralel çalışan keşif ve sindirici işçilerin (Worker) birbirleriyle çakışmasını, aynı konuyu/videoyu
çifte sindirmesini önleyen asenkron kilit (Lock) ve olay bildirim (Event Bus) katmanı.
"""
import asyncio
from typing import Dict, Any, Set, Optional
from datetime import datetime
from autonomous.state_persistence import state_persistence

class WorkerCoordinator:
    def __init__(self):
        self._active_task_locks: Set[str] = set()
        self._lock = asyncio.Lock()
        self.worker_events: Dict[str, asyncio.Event] = {}

    async def acquire_task_lock(self, task_key: str, worker_id: str) -> bool:
        """
        Bir konunun veya video_id'nin aynı anda birden fazla worker tarafından
        işlenmesini engelleyen atomik kilit alır.
        """
        async with self._lock:
            if task_key in self._active_task_locks:
                return False
            self._active_task_locks.add(task_key)
            state_persistence.update_worker_heartbeat(
                worker_id=worker_id,
                status="BUSY",
                current_task={"task_key": task_key}
            )
            return True

    async def release_task_lock(self, task_key: str, worker_id: str):
        """İşlem bittiğinde kilidi serbest bırakır."""
        async with self._lock:
            self._active_task_locks.discard(task_key)
            state_persistence.update_worker_heartbeat(
                worker_id=worker_id,
                status="IDLE",
                current_task=None
            )

    def is_locked(self, task_key: str) -> bool:
        return task_key in self._active_task_locks

worker_coordinator = WorkerCoordinator()
