"""
KPSS Super-Brain: Otonom Görev Zamanlayıcısı (Agent Scheduler)
APScheduler ve Asyncio tabanlı periyodik zamanlama motoru.
"""
import asyncio
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import super_brain_config
from autonomous.task_queue import task_queue
from autonomous.learning_loop import learning_loop

class AgentScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        if not self.is_running:
            # 1. Periyodik Otonom Öğrenme Döngüsü
            self.scheduler.add_job(
                self._trigger_periodic_learning,
                "interval",
                seconds=super_brain_config.AUTONOMOUS_CYCLE_INTERVAL_SECONDS,
                id="kpss_continuous_learning"
            )
            self.scheduler.start()
            self.is_running = True
            print("⏱️ [SCHEDULER] Otonom Zamanlayıcı Aktif Edildi.")

    async def _trigger_periodic_learning(self):
        print("⏰ [SCHEDULER] Zamanlanmış otonom döngü tetikleniyor...")
        await learning_loop.execute_full_cycle()

    def stop(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False

agent_scheduler = AgentScheduler()
