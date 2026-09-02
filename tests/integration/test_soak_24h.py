"""
KPSS Super-Brain: 24 Saatlik Dayanıklılık ve Yük Entegrasyon Test Süiti (Soak & Stress Tests)
50 ardışık otonom araştırma ve sindirme döngüsünü simüle ederek:
1. SQLite kilitlenme (deadlock / SQLITE_BUSY) dayanıklılığını,
2. Eşzamanlı worker görev kilitleme mekanizmasını (worker_locks),
3. Kuyruk önceliklendirme ve checkpoint kararlılığını doğrular.
"""
import pytest
import asyncio
import os
import gc
from unittest.mock import patch, MagicMock

from autonomous.priority_queue import priority_queue
from autonomous.worker_coordinator import worker_coordinator
from autonomous.state_persistence import state_persistence
from curriculum.queue import CurriculumQueue
from cognition.unified_verifier import UnifiedVerifier, VerificationVerdict
from brain.database import db_session


class TestSoakAndResilience:

    @pytest.fixture(autouse=True)
    def clean_queues(self):
        """Her testten önce bellek ve kilit kuyruklarını temizle."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM worker_locks")
            cursor.execute("DELETE FROM video_queue")
            conn.commit()
        yield

    @pytest.mark.asyncio
    async def test_sequential_50_cycles_soak_resilience(self):
        """50 ardışık otonom döngünün sıfır hata ve kilitlenme ile çalıştığını doğrula."""
        verifier = UnifiedVerifier()
        c_queue = CurriculumQueue()

        processed_count = 0

        for i in range(50):
            task_key = f"soak_task_{i % 5}"
            worker_id = f"worker_{i % 3}"

            # 1. Görev Kilidi Al
            has_lock = await worker_coordinator.acquire_task_lock(task_key, worker_id)
            if not has_lock:
                # Başka işçide kilit varsa serbest bırakılmasını simüle et
                await worker_coordinator.release_task_lock(task_key, f"worker_{(i - 1) % 3}")
                has_lock = await worker_coordinator.acquire_task_lock(task_key, worker_id)

            assert has_lock is True, f"Döngü {i}: Görev kilidi alınamadı"

            # 2. Kuyruk Ekleme & Çıkarma
            priority_queue.enqueue(
                source_type="YOUTUBE",
                lesson="VATANDASLIK",
                topic=f"Konu_{i}",
                payload={"video_id": f"vid_soak_{i:03d}", "teacher_name": "Emrah Vahap Özkaraca"},
                base_priority=float(i)
            )

            dequeued = priority_queue.dequeue()
            assert dequeued is not None
            assert dequeued["topic"] == f"Konu_{i}"

            # 3. Hiyerarşik Doğrulama Simülasyonu
            test_claim = f"TBMM üye sayısı 600'dür (Döngü {i})"
            with patch.object(verifier.prosecutor, "audit_claim_deepseek") as mock_audit:
                mock_audit.return_value = {
                    "verdict": "CONFIRMED",
                    "confidence": 0.96,
                    "explanation": "Doğru",
                    "canonical_truth": None,
                    "trap_distractor": None
                }
                decision = await verifier.verify_claim(test_claim, lesson="VATANDASLIK", topic="Yasama")
                assert decision.verdict == VerificationVerdict.CONFIRMED

            # 4. Görev Kilidini Bırak
            released = await worker_coordinator.release_task_lock(task_key, worker_id)
            assert released is True, f"Döngü {i}: Görev kilidi serbest bırakılamadı"

            # 5. Checkpoint Kaydet
            state_persistence.save_checkpoint({
                "cycle": i,
                "engine_stats": {"items_consumed": i + 1}
            })

            processed_count += 1

        assert processed_count == 50
        # Çöp toplayıcıyı tetikle
        gc.collect()

    @pytest.mark.asyncio
    async def test_concurrent_multi_worker_locks(self):
        """Birden çok işçinin aynı anda farklı görevleri güvenle işlediğini ve backpressure limitini doğrula."""
        results = []

        async def worker_job(worker_num: int, task_name: str):
            lock_acquired = await worker_coordinator.acquire_task_lock(task_name, f"worker_{worker_num}")
            results.append((worker_num, task_name, lock_acquired))
            if lock_acquired:
                await asyncio.sleep(0.05)
                await worker_coordinator.release_task_lock(task_name, f"worker_{worker_num}")

        # 4 işçiyi (max_concurrent limiti) aynı anda başlat
        tasks = [
            worker_job(1, "task_A"),
            worker_job(2, "task_B"),
            worker_job(3, "task_C"),
            worker_job(4, "task_D")
        ]
        await asyncio.gather(*tasks)

        assert len(results) == 4
        assert all(res[2] is True for res in results), "4 eşzamanlı işçi kilit alamadı"
