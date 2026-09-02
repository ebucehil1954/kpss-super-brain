"""
KPSS Super-Brain: Paralel Worker Koordinatörü ve Kilit Yöneticisi (Worker Coordinator v4)
Paralel çalışan keşif ve sindirici işçilerin (Worker) birbirleriyle çakışmasını, aynı konuyu/videoyu
çifte sindirmesini önleyen asenkron kilit (Lock) ve olay bildirim (Event Bus) katmanı.

[P1-1 DÜZELTME] Lock'lar artık bellekte Set yerine SQLite tabanlı crash-safe mekanizma ile yönetilir.
"""
import asyncio
from typing import Dict, Any, Set, Optional
from datetime import datetime
from brain.database import db_session
from autonomous.state_persistence import state_persistence

class WorkerCoordinator:
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self._lock = asyncio.Lock()
        self.is_shutting_down = False
        self._ensure_lock_table()

    def _ensure_lock_table(self):
        """
        [P1-1] Kilit bilgilerini crash-safe SQLite tablosuna taşır.
        Başlangıçta kalan eski kilitleri temizler (crash recovery).
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_locks (
                task_key TEXT PRIMARY KEY,
                worker_id TEXT NOT NULL,
                acquired_at TEXT NOT NULL
            )
            """)
            # Başlangıçta kalan eski kilitleri temizle (crash recovery)
            cursor.execute("DELETE FROM worker_locks")

    def _get_active_lock_count(self) -> int:
        """Aktif kilit sayısını SQLite'tan okur."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM worker_locks")
            return cursor.fetchone()["cnt"]

    def can_accept_work(self) -> bool:
        """[PHASE 15 BACKPRESSURE] Eğer aktif çalışan sayısı limiti aştıysa geri basınç uygular."""
        if self.is_shutting_down:
            return False
        return self._get_active_lock_count() < self.max_concurrent

    async def acquire_task_lock(self, task_key: str, worker_id: str) -> bool:
        """
        [PHASE 15 + P1-1] Bir konunun veya video_id'nin aynı anda birden fazla worker tarafından
        işlenmesini ve mükerrer çalışmayı engelleyen atomik kilit alır.
        Lock'lar SQLite'ta kalıcı olduğundan crash sonrası da doğru çalışır.
        """
        if self.is_shutting_down:
            return False

        async with self._lock:
            with db_session() as conn:
                cursor = conn.cursor()

                # Backpressure kontrolü
                cursor.execute("SELECT COUNT(*) as cnt FROM worker_locks")
                active_count = cursor.fetchone()["cnt"]
                if active_count >= self.max_concurrent:
                    return False  # Backpressure: havuz dolu

                # Mükerrer işleme engeli (idempotency)
                cursor.execute("SELECT 1 FROM worker_locks WHERE task_key = ?", (task_key,))
                if cursor.fetchone():
                    return False

                # Kilidi al
                cursor.execute(
                    "INSERT INTO worker_locks (task_key, worker_id, acquired_at) VALUES (?, ?, ?)",
                    (task_key, worker_id, datetime.now().isoformat())
                )

            state_persistence.update_worker_heartbeat(
                worker_id=worker_id,
                status="BUSY",
                current_task={"task_key": task_key}
            )
            return True

    async def release_task_lock(self, task_key: str, worker_id: str) -> bool:
        """İşlem bittiğinde kilidi serbest bırakır (SQLite'tan siler)."""
        async with self._lock:
            with db_session() as conn:
                conn.execute("DELETE FROM worker_locks WHERE task_key = ?", (task_key,))

            state_persistence.update_worker_heartbeat(
                worker_id=worker_id,
                status="IDLE",
                current_task=None
            )
            return True

    def is_locked(self, task_key: str) -> bool:
        """Bir görevin kilitli olup olmadığını kontrol eder."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM worker_locks WHERE task_key = ?", (task_key,))
            return cursor.fetchone() is not None

    def trigger_shutdown(self):
        """[PHASE 15] Deterministik temiz kapanış sinyali verir ve tüm kilitleri temizler."""
        self.is_shutting_down = True
        with db_session() as conn:
            conn.execute("DELETE FROM worker_locks")


worker_coordinator = WorkerCoordinator()
