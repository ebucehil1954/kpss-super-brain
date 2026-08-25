# 🧠 Promius KPSS Super-Brain: Agentic Research & Knowledge Mining Engine

> **Resmî ÖSYM KPSS Müfredatı için OpenManus / ReAct Tarzı Otonom Ajan Mimarisi, Denetlenebilir Provenance, Çoklu Hoca Çelişki Çözümü ve Deterministik Bilgi Grafiği ile Donatılmış Yapay Zeka Bilgi Motoru.**

---

## 🌟 Temel Mimari Prensipler

1. **🕵️‍♂️ Durum Makineli Otonom Araştırma Ajanı (Stateful Research Agent)**:
   - `GOAL_CREATED` ➔ `PLANNING` ➔ `DISCOVERING` ➔ `ACQUIRING` ➔ `EXTRACTING` ➔ `VERIFYING` ➔ `COMPARING` ➔ `GAP_ANALYSIS` ➔ `SYNTHESIZING` ➔ `COMPLETED` adımlarını işletir.
   - Her durum geçişini olay günlüğüne (`research_events`) mühürler.

2. **📜 Şeffaf Güven Aralığı ve Denetlenebilir Provenance**:
   - Her çıktının yanında % **Güven Aralığı** (Confidence Score) ve **Kaynak Bağlantısı** (Provenance) gösterilir.
   - Transkripti olmayan video için mevzuat fallback araması çalıştırılır; çıkarılan her atomik iddia (`AtomicClaim`) video kimliği, zaman damgası (`TranscriptSegment`) veya mevzuat URL'si taşır.

3. **⚖️ Semantik Çelişki Tespit ve Çözüm Motoru (Contradiction Engine)**:
   - `sentence-transformers/all-MiniLM-L6-v2` vektör kosinüs benzerliği (> 0.75) ve yerel **Ollama** (`qwen2.5:7b`) ile bağlamsal çelişkileri tespit eder.
   - `OFFICIAL_SOURCE_WINS` politikası ile 1982 Anayasası ve Resmî Gazete normları üstün tutulur.

4. **🛡️ Çok Katmanlı Doğrulama ve Kısıt Çözücü**:
   - **RefChecker**: İddiaları `(Özne, İlişki, Nesne)` üçlülerine ayırıp doğrular.
   - **SelfCheckGPT**: Örneklem tutarlılık skoru ile belirsiz iddiaları filtreler.
   - **Z3 SMT Solver (Timeout: 500ms)**: Anayasal ve sayısal kısıtları (üye sayıları, yaşlar, oranlar) matematiksel olarak denetler.

5. **📊 Derin Müfredat ve Kaynak Kapsamı Modeli**:
   - Konu başına minimum **8-10 farklı kaynak** (Video, Mevzuat, ÖSYM Çıkmış Sorular) taranır.
   - `DynamicWeightOptimizer` (scikit-learn Lojistik Regresyon) ve PostgreSQL + pgvector ile konu hakimiyeti ve semantik arama gerçekleştirilir.

---

## 📂 Dizin Yapısı ve Detaylı Dokümantasyon

```text
kpss-super-brain/
├── api/                    # FastAPI REST ve WebSocket sunucusu
├── autonomous/             # ResearchAgent, ToolRegistry, HungryEngine, GapAnalyzer
├── brain/                  # DynamicWeightOptimizer, pgvector (pg_database.py), Curriculum Matrix
├── canonical_facts/        # Dinamik ÖSYM ve mevzuat gerçekleri (.jsonl)
├── cognition/              # ContradictionEngine (all-MiniLM + Ollama), Teacher Identity
├── memory/                 # Bilgi Grafiği, Vektör Hafızası, Ground Truth
├── senses/                 # TranscriptFetcher, YouTubeWatcher (pypdf Fallback)
├── anti_hallucination/     # FactChecker, Z3LogicValidator, MultiReferee
├── templates/              # Jinja2 güvenli HTML şablonları (XSS Korumalı)
├── tests/                  # Pytest birim, entegrasyon ve 2025 KPSS duman testleri
├── docker-compose.yml      # PostgreSQL 16 + pgvector servisi
├── config.py               # Master yapılandırma
├── main.py                 # Ana otonom araştırma başlatıcı
└── web_ui.py               # FastAPI + Jinja2 Güvenli Web Kontrol Paneli
```

---

## 🚀 Hızlı Başlangıç

### 1. Bağımlılıkları Yükleyin ve Veritabanını Başlatın
```bash
pip install -r requirements.txt
docker-compose up -d postgres-pgvector
```

### 2. Testleri Çalıştırın
```bash
python -m pytest tests/
python -m pytest tests/integration/test_real_world.py
```

### 3. Sistemi Başlatın
```bash
# FastAPI + Jinja2 Güvenli Web Arayüzü:
python web_ui.py

# Otonom Araştırma Motoru:
python main.py
```
