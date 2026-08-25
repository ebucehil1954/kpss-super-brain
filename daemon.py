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
from autonomous.hungry_engine import hungry_engine

# Windows konsol UTF-8 ayarı
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def handle_shutdown(signum, frame):
    print("\n🛑 [DAEMON] Kapatma sinyali alındı. Veritabanı güvenle kaydediliyor...")
    asyncio.create_task(hungry_engine.stop())

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

async def main():
    await hungry_engine.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("👋 KPSS Super-Brain güvenle durduruldu.")
