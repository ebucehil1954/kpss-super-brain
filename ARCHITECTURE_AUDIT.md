# KPSS Super-Brain — Mimari ve Modül Sınırları Denetimi (ARCHITECTURE AUDIT)

> **Denetim Raporu:** Modül sınırları, veri akış yolları, eşzamanlılık ve sistem tasarım ilkeleri

---

## 1. Modül Sınırları ve Katmanlı Yapı Analizi

KPSS Super-Brain 5 temel mantıksal katmandan oluşmaktadır:

```text
[ Dış Katman: YouTube, Mevzuat, Web, PDF ]
                     │
                     ▼
[ Senses Katmanı ]: transcript_gateway, transcript_fetcher, youtube_api_client, whisper_transcriber
                     │
                     ▼
[ Cognition Katmanı ]: transcript_processor, cognitive_analyst, contradiction_engine,
                       auditor, prosecutor_auditor, correlation_engine, teacher_learner
                     │
                     ▼
[ Brain Katmanı ]: database (SQLite), knowledge_store, knowledge_graph,
                   curriculum_matrix, dynamic_weight_optimizer, reasoning_store
                     ▲
                     │
[ Autonomous Katmanı ]: hungry_engine, harvester, research_agent, consciousness
```

### 1.1 Katman İzolasyonunun Güçlü Yönleri
1. **OpenManus Boundary Guard:** `openmanus_bridge/client.py` içinde yer alan `commit_knowledge_forbidden()` metodu ile OpenManus'un veya harici arama araçlarının doğrudan veritabanına kanonik veri yazması mimari olarak engellenmiştir.
2. **Knowledge Firewall (Staging vs. Canon):** `atomic_claims` tablosu staging, `knowledge_records` tablosu kanon olarak kesin sınırla ayrılmıştır.
3. **Merkezi SSoT (Single Source of Truth):** SQLite `brain.db` mutlak gerçeklik kaynağıdır. Knowledge Graph, FTS5 arama indeksi ve vektör benzerlikleri türetilmiş (derived) geçici yapılardır ve veritabanından yeniden inşa edilebilir.

### 1.2 Mimari Sınır İhlalleri ve Riskler
1. **Savcı Baypası (Bkz. Bulgu 1):** `prosecutor_auditor.py`, `knowledge_store.add_or_reinforce_record()` metodunu doğrudan çağırarak staging aşamasını baypas etmektedir.
2. **Çapraz Bağımlılık (Circular Import Potansiyeli):** `cognition/analyst.py` doğrudan `cognition/teacher_learner.py` ve `brain/knowledge_store.py`'u çağırırken, `teacher_learner` da `brain/database`'i çağırmaktadır. İç içe importlar (`import inside function`) sıklıkla kullanılarak döngüsel bağımlılıklar maskelenmiştir.

---

## 2. Eşzamanlılık (Concurrency), Thread-Safety ve Kilitler

| Bileşen | Eşzamanlılık Mekanizması | Risk Seviyesi | Durum |
|---------|-------------------------|---------------|-------|
| **SQLite Veritabanı** | WAL Mode + `busy_timeout` (db_session retry) | 🟢 DÜŞÜK | Eşzamanlı okumalarda kilitlenme yok; yazmalarda 5 denemeli retry mekanizması var. |
| **Knowledge Graph** | `threading.RLock()` + `os.replace()` atomik kayıt | 🟢 DÜŞÜK | Bellek içi graf thread-safe, diske yazarken geçici dosya kullanılıyor. |
| **TranscriptGateway** | `ProviderCircuitBreaker` bellek içi sözlük | 🟡 ORTA | Çoklu async worker aynı anda circuit breaker state güncellediğinde race condition olabilir. |
| **ResearchAgent FSM** | SQLite `research_jobs` + `research_events` | 🟢 DÜŞÜK | Her durum geçişi veritabanına mühürleniyor. |

---

## 3. Temel Mimari Soruların Değerlendirmesi

### Soru 1: Sistem gerçekten sürekli öğrenen bir KPSS zekâsı oluşturacak mimariye sahip mi?
**Cevap:** **Kısmen EVET, ancak doğrulama darboğazları giderilmelidir.**
- *Kanıt:* `CurriculumMatrix` 885 satırlık eksiksiz müfredat ağacını barındırır. `ResearchAgent` eksik konuları tespit edip (`GAP_ANALYSIS`), yeni aramalar tetikleyerek (`RESEARCHING_GAPS`) döngüyü kapatabilmektedir.
- *Kısıt:* Çelişki motorundaki 1.0 saniyelik timeout (Bulgu 2) ve O(n²) karmaşıklığı (Bulgu 3), uzun süreli otonom öğrenmede sistemi yavaşlatacak ve yanlış mutabakatlara izin verecektir.

### Soru 6: Provenance zinciri her durumda korunuyor mu?
**Cevap:** **Standart akışta EVET, Savcı TRAP akışında HAYIR.**
- *Kanıt:* `TranscriptProcessor`'dan çıkan her fact için `EvidenceRef` oluşturulur (`video_id`, `segment_id`, `timestamp_str`, `snippet`). `ProvenanceValidator` bu 4 alanı denetlemeden kanonik ambarı açmaz.
- *İstisna:* `prosecutor_auditor.py` L189'da üretilen TRAP kayıtları bu zincirden muaftır.

### Soru 7: Tek bir hata bütün sistemi durdurabilir mi?
**Cevap:** **HAYIR (İzolasyon Başarılı).**
- *Kanıt:* `harvester.py` L295-305'te video başına `try/except` izolasyonu vardır. Bir video başarısız olduğunda `TRANSCRIPT_FAILED_TEMPORARY` olarak işaretlenir ve kuyruk diğer videolara geçer.
- *Kanıt:* `TranscriptGateway` 4 kademeli fallback ile tek bir altyazı sağlayıcısının çökmesini tolere eder.

### Soru 14: Birden fazla database/index farklı truth kaynakları oluşturabilir mi?
**Cevap:** **HAYIR.**
- Tüm veriler `brain.db` SQLite içinde yaşar. `knowledge_fts` bir FTS5 sanal tablosudur ve ana tabloyla senkronizedir. Knowledge Graph JSON dosyası `brain.db`'den türetilebilir. Çift truth kaynağı yoktur.

### Soru 16: Gereksiz derecede karmaşık veya çakışan bileşenler var mı?
**Cevap:** **EVET.**
- `cognition/auditor.py` (Z3 + Anayasa kuralları) ile `cognition/prosecutor_auditor.py` (DeepSeek-R1) kısmen çakışan görevleri yürütmektedir. İkisi de Anayasa çelişkilerini denetlemektedir. Birleştirilmeli veya hiyerarşik (Auditor -> Z3 -> DeepSeek-R1) olarak tek bir `VerificationPipeline` altında toplanmalıdır.
- `autonomous/hungry_engine.py` ile `autonomous/harvester.py` arasında görev dağılımı karmaşıktır; HungryEngine hem scheduler hem supervisor gibi davranmaktadır.

---

## 4. Mimari Tavsiyeler (Architectural Recommendations)

1. **Birleşik Doğrulama Boru Hattı (Unified Verification Pipeline):** `FactChecker`, `AuditorEngine` ve `ProsecutorAuditor` tek bir `VerificationGateway` arkasında toplanmalıdır.
2. **Kanonik Girdi Kapısı (Single Ingestion Invariant):** Kanonik `knowledge_records` tablosuna doğrudan INSERT yapan tüm kod yolları kaldırılmalı; YALNIZCA `knowledge_store.commit_verified_claim()` metoduna izin verilmelidir.
3. **Asenkron Çelişki Kuyruğu:** Çelişki denetimi canlı ingestion akışından çıkarılıp arka plan asenkron worker'ına devredilmelidir.
