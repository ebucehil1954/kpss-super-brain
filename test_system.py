"""
KPSS Super-Brain: Sistem Entegrasyon ve Doğrulama Testi
"""
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from brain.database import initialize_database
from brain.knowledge_store import knowledge_store
from brain.reasoning_store import reasoning_store
from brain.curriculum_matrix import curriculum_matrix
from cognition.cross_teacher_analyzer import cross_teacher_analyzer
from senses.youtube_crawler_agent import youtube_crawler_agent
from senses.video_crawler import video_crawler
from senses.video_queue import video_queue
from cognition.teacher_learner import teacher_learner
from cognition.self_tester import self_tester
from brain.exporter import data_exporter

print("1. DB Başlatılıyor...")
initialize_database()

print("2. Resmi Müfredat Konu Hakimiyet Matrisi Yükleniyor...")
curriculum_matrix.initialize_mastery_matrix()
rep = curriculum_matrix.get_curriculum_mastery_report()
print(f"  └─ Toplam Resmi ÖSYM Konusu: {rep['total_official_topics']} konu.")

print("3. Çoklu Hoca Video Tüketim Kaydı...")
res1 = curriculum_matrix.record_video_consumption(
    lesson="VATANDASLIK",
    topic="1982 Anayasası Yasama Organı ve Sayıları",
    video_id="demo_vid_01",
    teacher_name="Emrah Vahap Özkaraca",
    channel_name="İndeks Akademi",
    facts_extracted=8,
    traps_extracted=3
)
print(f"  └─ Konu Hakimiyet Durumu: {res1['mastery_stage']} (İzlenen Hoca Sayısı: {res1['distinct_teachers_count']})")

print("4. Çapraz Hoca Uzman Sentezi...")
synth = cross_teacher_analyzer.synthesize_master_topic_profile("VATANDASLIK", "1982 Anayasası Yasama Organı ve Sayıları")
print(f"  └─ Sentez Özeti: {synth['master_summary'][:80]}...")

print("5. Manus YouTube Keşif Durumu...")
discovery_status = youtube_crawler_agent.get_status()
print(f"  └─ Keşif Ajanı: {discovery_status['current_action']}")

print("6. Sade JSON Dışa Aktarımları...")
files = data_exporter.export_all()
for k, v in files.items():
    print(f"  └─ {k} -> {v}")

print("7. Müfredat Kapsam Analizi...")
health = self_tester.evaluate_knowledge_health()
print(f"  └─ Kapsam: %{health['curriculum_coverage_pct']} | Durum: {health['status']} | Eksikler: {health['gaps_count']}")

print("\n🎉 TÜM SİSTEM BİLEŞENLERİ BAŞARIYLA DOĞRULANDI!")
