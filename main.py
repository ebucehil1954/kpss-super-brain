"""
KPSS Super-Brain: Ana Başlatıcı ve Komut Satırı Yöneticisi (Main Entry Point v3)
Kullanım:
  python main.py             -> Web Kontrol Panelini Başlatır (Varsayılan: Port 8500)
  python main.py --hungry    -> 7/24 AÇ BEBEK MODU: Kesintisiz Paralel Öğrenme Motorunu Başlatır
  python main.py --daemon    -> 7/24 Arka Plan Otonom Ajan Servisini Başlatır
  python main.py --cycle     -> Tek bir otonom döngü yürütür ve çıkar
  python main.py --predict   -> 2026 Soru Tahmin Raporunu listeler
  python main.py --health    -> Bilişsel olgunluk ve konu eksikliği raporu verir
  python main.py --sync      -> Mevzuat ve TÜİK/MTA resmi verilerini senkronize eder
"""
import sys
import argparse
import asyncio
import json
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from api.server import app
from autonomous.daemon import super_brain_daemon
from autonomous.hungry_engine import hungry_engine
from autonomous.learning_loop import learning_loop
from cognition.prediction_engine import prediction_engine
from cognition.self_tester import self_tester
from senses.mevzuat_crawler import mevzuat_crawler
from senses.tuik_fetcher import tuik_fetcher

async def run_single_cycle():
    print("🚀 Tek Seferlik Otonom Döngü Başlatılıyor...")
    result = await learning_loop.execute_full_cycle()
    print("✅ Döngü Tamamlandı!")
    print(f"   Ders: {result.get('lesson')} — {result.get('topic')}")
    print(f"   Çıktılar 'outputs/' klasörüne kaydedildi.")

async def run_predictions():
    print("🎯 2026 KPSS Soru Tahmin Radarı Hesaplanıyor...")
    preds = await prediction_engine.generate_live_predictions()
    print("=" * 60)
    for idx, p in enumerate(preds, 1):
        print(f"{idx}. [{p.get('lesson')}] {p.get('topic')}")
        print(f"   Olasılık: %{int(p.get('probability')*100)} | Kalıp: {p.get('expected_question_type')}")
        print(f"   Gerekçe: {p.get('rationale')}")
        print("-" * 60)

def run_health_check():
    print("📊 Bilişsel Zeka Sağlığı ve Kör Nokta Taraması...")
    health = self_tester.evaluate_knowledge_health()
    print(f"Olgunluk Skoru: %{health['maturity_score']} ({health['status']})")
    print(f"Toplam Bilgi Kaydı: {health['total_records']}")
    print(f"Kritik Konu Eksikleri ({health['gaps_count']}):")
    for g in health.get("critical_gaps", [])[:5]:
        print(f"  - [{g['lesson']}] {g['topic']} (Mevcut: {g['current_records']})")

async def run_sync():
    print("🏛️ Resmi Mevzuat ve TÜİK/MTA Verileri Senkronize Ediliyor...")
    res_m = await mevzuat_crawler.fetch_constitutional_updates()
    res_t = tuik_fetcher.sync_official_geography_facts()
    print(f"✅ Mevzuat Senkronize Edildi: {res_m.get('synced_articles_count')} madde")
    print(f"✅ TÜİK/MTA Senkronize Edildi: {res_t.get('synced_records')} kayıt")

def main():
    parser = argparse.ArgumentParser(description="Promius KPSS Super-Brain Autonomous AI")
    parser.add_argument("--web", action="store_true", help="Web Görev Kontrol Panelini Başlat (Port 8500)")
    parser.add_argument("--hungry", action="store_true", help="7/24 Açgözlü Kesintisiz Paralel Motoru Başlat (Aç Bebek Modu)")
    parser.add_argument("--daemon", action="store_true", help="7/24 Otonom Arka Plan Servisini Başlat")
    parser.add_argument("--cycle", action="store_true", help="Tek bir otonom öğrenme döngüsü yürüt")
    parser.add_argument("--predict", action="store_true", help="Soru tahmin raporunu göster")
    parser.add_argument("--health", action="store_true", help="Bilişsel olgunluk ve eksik konu raporunu göster")
    parser.add_argument("--sync", action="store_true", help="Resmi Mevzuat ve TÜİK verilerini senkronize et")
    parser.add_argument("--conscious", action="store_true", help="Bilinç ve Düşünce Günlüğü (CoT) durumunu göster")
    parser.add_argument("--checkpoint", action="store_true", help="Kayıtlı son durum ve checkpoint özetini göster")
    parser.add_argument("--port", type=int, default=8500, help="Web UI Portu (Varsayılan: 8500)")

    args = parser.parse_args()

    if args.hungry:
        asyncio.run(hungry_engine.start())
    elif args.conscious:
        from autonomous.consciousness import consciousness
        state = consciousness.get_current_consciousness_state()
        if not state.get("active_focus"):
            consciousness.deliberate_next_step()
            state = consciousness.get_current_consciousness_state()
        active = state.get("active_focus") or {}
        cov = state.get("curriculum_coverage") or {}
        print("🧠 [BİLİNÇ VE DÜŞÜNCE DURUMU]:")
        print(f"   Aktif Odak: {active.get('target_lesson')} — {active.get('target_topic')}")
        print(f"   Müfredat Kapsamı: {cov.get('total_nodes')} Düğüm")
        print(f"   Son Kararlar:")
        for d in state.get('recent_decisions', []):
            print(f"     - [{d.get('timestamp')}] {d.get('target_lesson')}: {d.get('target_topic')} ({d.get('action_type')})")
    elif args.checkpoint:
        from autonomous.state_persistence import state_persistence
        chk = state_persistence.load_checkpoint()
        print("💾 [SON CHECKPOINT DURUMU]:")
        print(json.dumps(chk, ensure_ascii=False, indent=2))
    elif args.cycle:
        asyncio.run(run_single_cycle())
    elif args.predict:
        asyncio.run(run_predictions())
    elif args.health:
        run_health_check()
    elif args.sync:
        asyncio.run(run_sync())
    elif args.daemon:
        asyncio.run(super_brain_daemon.start())
    else:
        # Varsayılan: Web Kontrol Merkezi
        print("🧠 [KPSS SUPER-BRAIN] Görev Kontrol Merkezi Başlatılıyor...")
        print(f"Tarayıcınızda açın: http://127.0.0.1:{args.port}")
        import web_ui
        uvicorn.run("web_ui:app", host="0.0.0.0", port=args.port, reload=False)

if __name__ == "__main__":
    main()
