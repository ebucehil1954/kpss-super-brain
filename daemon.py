"""
KPSS Super-Brain: 7/24 Otonom Öğrenen Yapay Zeka Öğretmen Süreci (Daemon)
Açgözlü Paralel Öğrenme Motorunu (HungryEngine) çalıştırır. Yüzlerce video ve kaynağı
paralel olarak tüketerek öğretmenlerin mantığını, şifrelerini ve sınav stratejilerini beynine işler.

Çalıştırmak için: python daemon.py
Durdurmak için: CTRL + C (Veri kaybı olmadan güvenli kapanır)
"""
import sys
import os
import asyncio
import signal
from typing import Set

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("KPSS_SUPER_BRAIN")

from autonomous.hungry_engine import hungry_engine

# Windows konsol UTF-8 ayarı
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"Konsol UTF-8 yapılandırılamadı: {e}")

# Aktif arka plan görevleri takibi
_BACKGROUND_TASKS: Set[asyncio.Task] = set()
_SHUTDOWN_EVENT = asyncio.Event()

def _track_task(task: asyncio.Task) -> None:
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)

async def _graceful_shutdown():
    """Tüm arka plan görevlerini ve HungryEngine'i güvenle sonlandırır."""
    if _SHUTDOWN_EVENT.is_set():
        return
    _SHUTDOWN_EVENT.set()
    logger.info("🛑 [DAEMON] Kapatma sinyali alındı. Veritabanı ve durumlar güvenle kaydediliyor...")
    
    # 1. HungryEngine'i durdur (timeout: 5 sn)
    try:
        await asyncio.wait_for(hungry_engine.stop(), timeout=5.0)
        logger.info("✅ HungryEngine başarıyla durduruldu.")
    except asyncio.TimeoutError:
        logger.error("⚠️ HungryEngine durdurulurken 5 saniyelik zaman aşımı oluştu.")
    except Exception as e:
        logger.error(f"Hata: HungryEngine durdurulurken istisna oluştu: {e}", exc_info=True)

    # 2. Kalan arka plan görevlerini iptal et ve bekle
    pending = [t for t in _BACKGROUND_TASKS if not t.done() and t is not asyncio.current_task()]
    if pending:
        logger.info(f"Bekleyen {len(pending)} arka plan görevi iptal ediliyor...")
        for t in pending:
            t.cancel()
        try:
            await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=5.0)
        except Exception as e:
            logger.error(f"Hata: Görevler iptal edilirken beklenmeyen durum: {e}", exc_info=True)

    logger.info("👋 KPSS Super-Brain güvenle durduruldu.")

async def main():
    loop = asyncio.get_running_loop()
    
    # Sinyal dinleyicilerini async döngüye bağla (Unix destekli)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_graceful_shutdown()))
        except NotImplementedError:
            # Windows platformunda add_signal_handler desteklenmez
            pass

    engine_task = asyncio.create_task(hungry_engine.start())
    _track_task(engine_task)

    try:
        await engine_task
    except asyncio.CancelledError:
        logger.info("[DAEMON] Ana motor görevi iptal edildi.")
    except Exception as e:
        logger.error(f"Hata: Daemon çalışma zamanında istisna oluştu: {e}", exc_info=True)
    finally:
        await _graceful_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 KPSS Super-Brain süreci sonlandırıldı.")
