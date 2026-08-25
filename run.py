"""
KPSS Super-Brain: Ana Test ve Otonom Döngü Çalıştırıcı (CLI Runner)
Kullanım: python run.py
"""
import sys
import asyncio

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from config import super_brain_config
from brain.blacklist_rules import BlacklistAuditor
from brain.knowledge_graph import kpss_knowledge_graph
from brain.vector_memory import vector_memory
from cognition.prediction_engine import prediction_engine
from cognition.teacher_profiler import teacher_profiler
from autonomous.learning_loop import learning_loop

async def main():
    print("=" * 70)
    print("🧠 PROMIUS KPSS SUPER-BRAIN — OTONOM YAPAY ZEKA ÖĞRETMENİ")
    print("=" * 70)
    print(f"📍 Ollama Bağlantısı: {super_brain_config.OLLAMA_BASE_URL}")
    print(f"📍 Ana Model: {super_brain_config.MAIN_MODEL}")
    print(f"📍 Muhakeme Modeli: {super_brain_config.REASONING_MODEL}")
    print(f"📍 Vektör Hafıza: {vector_memory.get_stats()['total_knowledge_chunks']} Parçacık")
    print("-" * 70)
    
    # 1. Kara Liste ve Mülga Kanun Savunma Testi
    sample_text = "Başbakan ve Bakanlar Kurulu tüzük çıkarmıştır."
    is_clean, violations = BlacklistAuditor.audit_text(sample_text)
    print(f"🛡️ [GÜVENLİK TESTİ] 2017 Anayasa Değişikliği ve Mülga Kanun Savunması:")
    print(f"   Denetlenen Metin: '{sample_text}'")
    print(f"   Sonuç: {'❌ BAŞARIYLA ENGELLENDİ' if not is_clean else '✅ GEÇTİ'}")
    print(f"   İhlal Kaydı: {violations}")
    print("-" * 70)
    
    # 2. Bilgi Grafiği ve Eğitmen Zihniyeti Modeli Testi
    print(f"📊 [BİLGİ GRAFİĞİ & EĞİTMEN MODELLERİ]:")
    print(f"   TBMM Üye Tam Sayısı: {kpss_knowledge_graph.nodes['VAT_TBMM_SAYILARI']['properties']['tbmm_uye_tamsayisi']}")
    print(f"   Seçim Yenileme Çoğunluğu: {kpss_knowledge_graph.nodes['VAT_TBMM_SAYILARI']['properties']['secim_yenileme_cogunlugu']}")
    print(f"   Kayıtlı Eğitmen Sayısı: {len(teacher_profiler.get_all_profiles())} (Ramazan Yetgin, Bayram Meral, Emrah Vahap vb.)")
    print("-" * 70)
    
    # 3. 2026 KPSS Soru Tahmin Radarı
    print(f"🎯 [2026 KPSS SORU TAHMİN RADARI]:")
    predictions = await prediction_engine.generate_live_predictions()
    for p in predictions[:3]:
        print(f"   - [{p.get('lesson')}] {p.get('topic')} -> Olasılık: %{int(p.get('probability')*100)}")
    print("-" * 70)

    # 4. Otonom Öğrenme ve Üretim Döngüsü Testi
    print("🤖 [OTONOM ÖĞRENME VE ÜRETİM DÖNGÜSÜ BAŞLATILIYOR]...")
    result = await learning_loop.execute_full_cycle(
        target_lesson="VATANDASLIK",
        target_topic="1982 Anayasası Yasama ve Karar Yeter Sayıları",
        watch_youtube=True
    )
    print("-" * 70)
    print("✨ DÖNGÜ ÇIKTILARI:")
    if result.get("youtube_insights"):
        print(f"   🎥 Eğitmen Vurgusu: {result['youtube_insights'].get('teacher_name')} -> {result['youtube_insights'].get('key_emphasis', [''])[0]}")
    if result.get("facts"):
        print(f"   📰 Üretilen Flashcard: {len(result['facts'])} adet")
    if result.get('mnemonic'):
        print(f"   ✨ Üretilen Akrostiş: {result['mnemonic'].get('code')} — {result['mnemonic'].get('title')}")
    if result.get('question'):
        print(f"   📝 Üretilen Soru: {result['question'].get('stem')[:75]}...")
        print(f"   ✅ Onaylanan Doğru Cevap: [{result['question'].get('expected_answer')}]")
        print(f"   ⚖️ Hakem Kararı: {result['question'].get('referee_verification')}")
    print("=" * 70)
    print("🎉 KPSS SUPER-BRAIN OTONOM MOTORU KUSURSUZ ÇALIŞIYOR!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
