"""
KPSS Super-Brain: 7/24 Arka Plan Otonom Daemon Servisi (Daemon Process)
Sistem arka planda sürekli çalışırken görev kuyruğunu tüketir, yeni videoları izler ve soru üretir.
"""
import asyncio
from typing import Optional
from autonomous.task_queue import task_queue
from autonomous.learning_loop import learning_loop
from autonomous.scheduler import agent_scheduler
from senses.channel_monitor import channel_monitor
from senses.youtube_watcher import youtube_watcher

class AutonomousDaemon:
    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True
        agent_scheduler.start()
        print("🤖 [DAEMON] KPSS Super-Brain 7/24 Otonom Arka Plan Servisi Başlatıldı.")
        
        while self.running:
            try:
                # 1. Bekleyen Görev Kuyruğunu Kontrol Et
                task = task_queue.fetch_next_pending_task()
                if task:
                    task_id = task["id"]
                    t_type = task["task_type"]
                    payload = task["payload"]
                    print(f"⚙️ [DAEMON] Görev İşleniyor: [{t_type}] ID={task_id}")
                    
                    if t_type == "LEARNING_CYCLE":
                        await learning_loop.execute_full_cycle(
                            target_topic=payload.get("topic"),
                            target_lesson=payload.get("lesson")
                        )
                    elif t_type == "WATCH_YOUTUBE":
                        await youtube_watcher.analyze_and_learn_from_lecture(
                            video_id_or_url=payload.get("video_id", "demo"),
                            teacher_name=payload.get("teacher_name", "Ramazan Yetgin"),
                            lesson=payload.get("lesson", "TARIH"),
                            topic=payload.get("topic", "Genel Tekrar")
                        )
                    task_queue.mark_completed(task_id)
                else:
                    await asyncio.sleep(5.0)
            except Exception as e:
                print(f"❌ [DAEMON HATA] {str(e)}")
                await asyncio.sleep(10.0)

    def stop(self):
        self.running = False
        agent_scheduler.stop()
        print("🛑 [DAEMON] Otonom Servis Durduruldu.")

super_brain_daemon = AutonomousDaemon()
