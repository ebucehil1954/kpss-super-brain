# 🧠 Promius KPSS Super-Brain (Standalone Autonomous AI)

> **Resmi ÖSYM Müfredatı için Manus Tarzı YouTube Keşif Ajanı, En Az 3-4 Farklı Hoca Tüketim Kuralı ve Çapraz Öğretmen Uzman Sentezi ile Donatılmış Otonom Yapay Zeka KPSS Profesörü.**

---

## 🌟 Öne Çıkan Temel Yetenekler

1. **📋 Resmi Müfredat Konu Hakimiyet Matrisi**:
   - Tarih (27 Soru), Coğrafya (18 Soru), Vatandaşlık/Güncel (15 Soru), Türkçe (30 Soru) ve Matematik/Geometri (30 Soru) olmak üzere **52 resmi konu başlığının** tamamını kapsar.
   - Her konu için **en az 3-4 farklı popüler hocanın ders videosu tüketilmeden** konu tamamlanmış sayılmaz (`0/4` -> `1/4` -> `2/4` -> `3/4` -> `4+/4 Uzman`).

2. **🕵️‍♂️ Manus Tarzı Otonom YouTube Keşif Ajanı**:
   - *Benim Hocam, İsem TV, İndeks Akademi, Hoca Webde, Pegem Akademi* vb. popüler kanalları, oynatma listelerini ve full serileri otonom tarar.
   - Müfredatta eksik kalan konular için en popüler ve kaliteli hocaların derslerini bularak tüketim kuyruğuna aktarır.

3. **🎓 Çapraz Öğretmen Karşılaştırma ve Uzman Sentezi**:
   - Bir konuda 3-4 farklı hoca videosu tüketildiğinde; *Ramazan Yetgin, Mehmet Celal, Aydın Yüce, Bayram Meral, Engin Eraydın, Erdal Kesekler, Emrah Vahap Özkaraca, Öznur Saat Yıldırım* vb. eğitmenlerin ortaklaştığı kesin bilgileri, çeldirici sınav tuzaklarını, hafıza şifrelerini (akrostişler) ve soru çözüm stratejilerini tek bir **KPSS Uzman Öğretmen Zihninde** sentezler.

4. **🛡️ 9 Katmanlı Anti-Halüsinasyon Kalkanı & Z3 Sözel Mantık**:
   - 2017 Anayasa değişikliklerine uygun mülga terim engelleme (Başbakanlık, Tüzük, Gensoru, vb. yasaklıdır).
   - Sahte kanun adı tespiti ve tarihsel anakronizm koruması.
   - Z3 SMT Solver ile sözel mantık ve tablo problemlerinin %100 matematiksel tutarlılık doğrulaması.

5. **⚡ 7/24 Kesintisiz Otonom Tüketim (Hungry Engine v5)**:
   - Ücretsiz Proxy Havuzu Rotasyonu ile 429 / IP engeli savunması.
   - GPU Destekli Yerel Whisper STT ile altyazısız ders videolarının yerel çözümü.
   - SQLite Checkpoint Persistence ile kapanıp açıldığında kaldığı yerden devam edebilme.

---

## 📂 Mimari ve Dizin Yapısı

```text
kpss-super-brain/
├── api/                    # FastAPI REST ve WebSocket sunucusu
├── autonomous/             # 7/24 Hungry Engine, Priority Queue, State Persistence
├── brain/                  # Resmi Müfredat Matrisi, SQLite Ambarı, Deep Ontology
├── cognition/              # Çapraz Hoca Sentezi, Öğretmen Profilleri, Self-Tester
├── memory/                 # Bilgi Grafiği (DAG), Vektör Hafızası, Mülga Kuralları
├── senses/                 # Manus YouTube Keşif Ajanı, Video Kuyruğu, Whisper STT
├── anti_hallucination/     # 9 Katmanlı Çapraz Doğrulama, Z3 Solver, Hakem Heyeti
├── generators/             # Hakem Denetimli Soru Fabrikası, Şifre Motoru
├── data/                   # Kalıcı SQLite DB, JSON hafıza ambarı, transkriptler
├── outputs/                # Canlı Markdown raporları ve özetler
├── tests/                  # Pytest test paketi (23 kapsamlı test)
├── config.py               # Master yapılandırma ve hedef öğretmen/kanal listesi
├── main.py                 # Ana CLI başlatıcı
├── web_ui.py               # Web Kontrol ve Gözlem Merkezi (Port 8500)
├── requirements.txt        # Bağımlılıklar
└── test_system.py          # Hızlı sistem doğrulama testi
```

---

## 🚀 Kurulum ve Başlangıç

### 1. Python Bağımlılıklarını Yükleyin
```bash
cd kpss-super-brain
pip install -r requirements.txt
```

### 2. Yerel Modelleri İndirin (Ollama)
```bash
# 1. Ana Zihin Modeli
ollama pull qwen2.5:14b

# 2. Muhakeme ve Karşıt Hakem Modeli
ollama pull deepseek-r1:8b
```

---

## 🎮 Çalıştırma Yöntemleri

### A. Web Kontrol ve Gözlem Merkezi (Önerilen)
Web arayüzünden müfredat matrisini (`0/4 - 4/4 Video`), Manus keşif radarını ve çoklu hoca sentezlerini canlı izlemek için:
```bash
python web_ui.py
# veya Windows'ta:
start_web_ui.bat
```
👉 Tarayıcınızda açın: **`http://127.0.0.1:8500`**

### B. 7/24 Otonom Keşif ve Tüketim Motoru (Hungry Engine)
Komut beklemeden sürekli YouTube'da gezinip müfredatı yutması için:
```bash
python main.py --mode hungry
# veya Windows'ta:
start_super_brain.bat
```

### C. Doğrulama Testlerini Çalıştırma
```bash
# 1. Pytest Test Paketi
pytest tests/

# 2. Sistem Entegrasyon Testi
python test_system.py
```

---

## 📄 Lisans
Bu proje bağımsız bir otonom yapay zeka araştırma ve eğitim motorudur.
