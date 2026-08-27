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
    parser.add_argument("--curriculum", action="store_true", help="3 KPSS Sınavı Müfredat ve Hakimiyet Raporunu Göster")
    parser.add_argument("--next-task", action="store_true", help="OpenManus için sıradaki yüksek öncelikli araştırma görevlerini göster")
    parser.add_argument("--harvester", action="store_true", help="7/24 Kesintisiz Otonom YouTube Karadeliğini Başlat (Saha İşçisi)")
    parser.add_argument("--harvest-once", action="store_true", help="Tek bir görevi YouTube'dan araştır, transkriptini indir ve dur")
    parser.add_argument("--teacher", type=str, help="Belirli bir hocanın çıkarılan zihin profilini ve şifrelerini göster")
    parser.add_argument("--mnemonics", action="store_true", help="Hafızadaki tüm KPSS ezber şifrelerini (akrostiş, kodlama) listele")
    parser.add_argument("--traps", action="store_true", help="Hafızadaki tüm ÖSYM sınav tuzaklarını ve çeldiricileri listele")
    parser.add_argument("--port", type=int, default=8500, help="Web UI Portu (Varsayılan: 8500)")

    args = parser.parse_args()

    if args.teacher:
        from cognition.teacher_learner import teacher_learner
        prof = teacher_learner.get_or_create_profile(args.teacher)
        print("=" * 70)
        print(f"🎓 [EĞİTMEN ZİHİN PROFİLİ]: {prof['name']} ({prof['channel']})")
        print("=" * 70)
        print(f"Ders: {prof['lesson']} | İzlenen Video: {prof['videos_watched']} | Toplam Kelime: {prof['total_transcript_words']}")
        print(f"Bilgi Katkısı: {prof['unique_facts_count']} Bilgi | {len(prof['mnemonics_used'])} Şifre | {prof['trap_warnings_count']} Tuzak Uyarısı")
        print("\n🔑 Kullanılan Özel Şifre ve Kodlamalar:")
        if prof['mnemonics_used']:
            for m in prof['mnemonics_used']:
                print(f"  - [{m.get('code', 'ŞİFRE')}]: {m.get('title', '')} -> {m.get('explanation', '')}")
        else:
            print("  (Henüz özel şifre tespit edilmedi)")
        print("\n🎯 Odak Konular:")
        for t in prof['favorite_topics'][:5]:
            print(f"  - {t}")
        print("=" * 70)
    elif args.mnemonics:
        from brain.database import db_session
        print("=" * 70)
        print("🔑 [KPSS HAFIZA AMBARI] TÜM EZBER ŞİFRELERİ VE AKROSTİŞLER")
        print("=" * 70)
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_records WHERE record_type = 'MNEMONIC' ORDER BY first_learned DESC LIMIT 30")
            rows = cursor.fetchall()
            for r in rows:
                print(f"📌 [{r['lesson']}] {r['text']}")
        print("=" * 70)
    elif args.traps:
        from brain.database import db_session
        print("=" * 70)
        print("⚠️ [ÖSYM TUZAK RADARI] ÇELDİRİCİLER VE HOCA UYARILARI")
        print("=" * 70)
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_records WHERE record_type = 'TRAP' ORDER BY first_learned DESC LIMIT 30")
            rows = cursor.fetchall()
            for r in rows:
                print(f"⚡ [{r['lesson']} - {r['topic']}] {r['text']}")
        print("=" * 70)
    elif args.harvester:
        from autonomous.harvester import youtube_harvester
        asyncio.run(youtube_harvester.start_continuous_harvest())
    elif args.harvest_once:
        from autonomous.harvester import youtube_harvester
        res = asyncio.run(youtube_harvester.harvest_single_task())
        print("\n🏁 [HASAT SONUCU]:")
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.curriculum:
        from curriculum import curriculum_engine, curriculum_queue
        report = curriculum_engine.get_gap_analysis()
        q_stats = curriculum_queue.get_queue_stats()
        print("=" * 70)
        print("📚 [KPSS SUPER-BRAIN] 3 SINAV MÜFREDAT HAKİMİYET VE EKSİK RADARI")
        print("=" * 70)
        print(f"Genel Müfredat Doluluk Oranı: %{report['coverage_percentage']}")
        print(f"Tüketilen Ders Videosu: {report['total_videos_consumed']} / {report['total_target_videos']}")
        print(f"Toplam Konu Sayısı: {report['total_topics']}")
        print("\nKonu Hakimiyet Aşamaları:")
        for stage, cnt in report['stages'].items():
            print(f"  - {stage}: {cnt} konu")
        print("\nDers Bazlı İlerleme:")
        for l_name, l_stat in report['by_lesson'].items():
            pct = round((l_stat['consumed_videos'] / l_stat['target_videos'] * 100), 1) if l_stat['target_videos'] > 0 else 0
            print(f"  - {l_name}: %{pct} ({l_stat['consumed_videos']}/{l_stat['target_videos']} Video)")
        print("\nCanlı Video Kuyruk Durumu:")
        print(f"  - Bekleyen: {q_stats['pending_videos']} | İzlenen: {q_stats['watched_videos']} | Altyazısız: {q_stats['no_transcript_videos']}")
        print("=" * 70)
    elif args.next_task:
        from curriculum import curriculum_engine
        tasks = curriculum_engine.generate_next_research_tasks(count=5)
        print("=" * 70)
        print("🎯 [OPENMANUS GÖREV LİSTESİ] SIRADAKİ EN YÜKSEK ÖNCELİKLİ HEDEFLER")
        print("=" * 70)
        for t in tasks:
            print(f"📌 Görev ID: {t.task_id} | Öncelik: {t.priority}")
            print(f"   Ders: {t.lesson.value} | Konu: {t.topic_name}")
            print(f"   Hedef Hocalar: {', '.join(t.target_teachers)}")
            print(f"   Örnek Arama: '{t.search_queries[0]}'")
            print(f"   Gerekçe: {t.reason}")
            print("-" * 70)
    elif args.hungry:
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
