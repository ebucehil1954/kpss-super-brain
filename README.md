# 🧠 Promius KPSS Super-Brain: Agentic Research & Knowledge Mining Engine

> **Resmî ÖSYM KPSS Müfredatı için OpenManus / ReAct Tarzı Otonom Ajan Mimarisi, Denetlenebilir Provenance, Çoklu Hoca Çelişki Çözümü ve Deterministik Bilgi Grafiği ile Donatılmış Yapay Zeka Bilgi Motoru.**

---

## 🌟 Temel Mimari Prensipler

1. **🕵️‍♂️ Durum Makineli Otonom Araştırma Ajanı (Stateful Research Agent)**:
   - `GOAL_CREATED` ➔ `PLANNING` ➔ `DISCOVERING` ➔ `ACQUIRING` ➔ `EXTRACTING` ➔ `VERIFYING` ➔ `COMPARING` ➔ `GAP_ANALYSIS` ➔ `SYNTHESIZING` ➔ `COMPLETED` adımlarını işletir.
   - Her durum geçişini olay günlüğüne (`research_events`) mühürler.

2. **📜 Sıfır Sahte Veri ve Denetlenebilir Provenance**:
   - Transkripti olmayan video asla web özetiyle doldurulmaz; açıkça `TRANSCRIPT_UNAVAILABLE` olarak işaretlenir.
   - Çıkarılan her atomik iddia (`AtomicClaim`), video kimliği, zaman damgalı segment (`TranscriptSegment`) ve SHA-256 `provenance_hash` taşır.

3. **⚖️ Semantik Çelişki Tespit ve Çözüm Motoru (Contradiction Engine)**:
   - `sentence-transformers/all-MiniLM-L6-v2` vektör kosinüs benzerliği (> 0.75) ve yerel **Ollama** (`qwen2.5:7b`) ile bağlamsal çelişkileri tespit eder.
   - `OFFICIAL_SOURCE_WINS` politikası ile 1982 Anayasası ve Resmî Gazete normları üstün tutulur.

4. **🛡️ 4 Katmanlı Doğrulama ve Kısıt Çözücü**:
   - **RefChecker**: İddiaları `(Özne, İlişki, Nesne)` üçlülerine ayırıp doğrular.
   - **SelfCheckGPT**: $T=0.7$ örneklem tutarlılık skoru ($< 0.85$ çelişkileri engeller).
   - **Z3 SMT Solver (Timeout: 500ms)**: Anayasal ve sayısal kısıtları (üye sayıları, yaşlar, oranlar) matematiksel olarak denetler.

5. **📊 Derin Müfredat ve Kaynak Kapsamı Modeli**:
   - Konu başına minimum **8-10 farklı kaynak** (Video, Mevzuat, ÖSYM Çıkmış Sorular) taranır.
   - Gerçek kanıt yoğunluğu, eğitmen mutabakatı ve zamansal tazelik ile dinamik konu hakimiyeti hesaplanır.

---

## 📂 Dizin Yapısı ve Detaylı Dokümantasyon

```text
kpss-super-brain/
├── api/                    # FastAPI REST ve WebSocket sunucusu
├── autonomous/             # ResearchAgent, ToolRegistry, HungryEngine, Coordinator
├── brain/                  # Pydantic Modelleri (models.py), SQLite Ambarı, Curriculum Matrix
├── cognition/              # ContradictionEngine, Çapraz Hoca Analizcisi, Self-Tester
├── memory/                 # Bilgi Grafiği (DAG), Vektör Hafızası, Ground Truth
├── senses/                 # TranscriptFetcher, TranscriptProcessor, VideoCrawler
├── anti_hallucination/     # FactChecker, Z3LogicValidator, MultiReferee
├── generators/             # Hakem Denetimli Soru Fabrikası, KPSS Profesörü Explainer
├── data/                   # Kalıcı SQLite DB, JSON ambarı, transkript önbellekleri
├── tests/                  # Pytest test paketi (29 kapsamlı test)
├── ARCHITECTURE.md         # Ayrıntılı sistem mimarisi
├── AGENT_FLOW.md           # Ajan durum makinesi ve durma koşulları
├── KNOWLEDGE_MODEL.md      # Pydantic iddia ve kanıt şemaları
├── SOURCE_PROVENANCE.md    # Kaynak ve zaman damgası izlenebilirliği
├── ERROR_HANDLING.md       # Hata yönetimi ve sıfır sessiz hata ilkesi
├── TEST_STRATEGY.md        # Test seviyeleri ve doğrulama planı
├── OPERATIONS.md           # Kurulum, çalıştırma ve operasyon rehberi
├── config.py               # Master yapılandırma
├── main.py                 # Ana CLI başlatıcı
└── web_ui.py               # Web Kontrol ve Gözlem Merkezi
```

---

## 🚀 Hızlı Başlangıç

### 1. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Testleri Çalıştırın
```bash
python -m pytest tests/
# 29 passed in ~12s (%100 Başarı)
```

### 3. Sistemi Başlatın
```bash
# Web UI Arayüzü:
python web_ui.py

# Otonom 7/24 Araştırma Motoru:
python main.py
```
