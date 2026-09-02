# 🏛️ KPSS Super-Brain: Sistem Mimarisi (ARCHITECTURE.md)

Bu doküman, `ebucehil1954/kpss-super-brain` projesinin üretim kalitesindeki **Agentic Research & Knowledge Mining** mimarisini, veri modellerini ve bileşenler arası veri akışını açıklar.

---

## 1. Yüksek Düzey Sistem Mimarisi

```text
                         ┌─────────────────────────┐
                         │       USER / API        │
                         └────────────┬────────────┘
                                      ↓
                         ┌─────────────────────────┐
                         │     RESEARCH AGENT      │
                         │ Plan / Act / Reflect    │
                         └────────────┬────────────┘
                                      ↓
                     ┌────────────────┴────────────────┐
                     ↓                                 ↓
          ┌────────────────────┐             ┌────────────────────┐
          │  SOURCE DISCOVERY  │             │  KNOWLEDGE MEMORY  │
          │  YouTube/Web/PDF   │             │  Search/Graph/RAG  │
          └──────────┬─────────┘             └──────────┬─────────┘
                     ↓                                  ↓
          ┌────────────────────┐             ┌────────────────────┐
          │    ACQUISITION     │             │    GAP ANALYZER    │
          │  transcript/PDF    │             │  coverage/missing  │
          └──────────┬─────────┘             └──────────┬─────────┘
                     └────────────────┬─────────────────┘
                                      ↓
                           ┌────────────────────┐
                           │   EVIDENCE ENGINE  │
                           │   claim/evidence   │
                           │   provenance hash  │
                           └──────────┬─────────┘
                                      ↓
                           ┌────────────────────┐
                           │    VERIFICATION    │
                           │  official/temporal │
                           │  Z3 SMT / RefCheck │
                           │  contradiction     │
                           └──────────┬─────────┘
                                      ↓
              ┌───────────────────────┴───────────────────────┐
              ↓                                               ↓
    ┌───────────────────┐                           ┌───────────────────┐
    │  RELATIONAL STORE │                           │  KNOWLEDGE GRAPH  │
    │  SQLite / Events  │                           │  DAG / Entities   │
    └─────────┬─────────┘                           └─────────┬─────────┘
              ↓                                               ↓
              └───────────────────────┬───────────────────────┘
                                      ↓
                            ┌───────────────────┐
                            │   MASTER TOPIC    │
                            │ verified profile  │
                            └───────────────────┘
```

---

## 2. Temel Çekirdek Bileşenler

### A. Tip Güvenli Araç Kayıt Defteri (`autonomous/tool_registry.py`)
- Araçların doğrudan kontrolsüz fonksiyonlar olarak çağrılmasını önler.
- `ToolDefinition` ile her araç için `name`, `input_schema`, `output_schema`, `timeout_seconds`, `retry_policy` ve `side_effects` zorunludur.
- Kayıtlı Temel Araçlar:
  - `youtube_search`: Popüler hoca videolarını ve oynatma listelerini keşfeder.
  - `transcript_fetch`: Zaman damgalı segmentleri ve tam transkripti çeker.
  - `official_mevzuat_search`: Mevzuat.gov.tr ve Resmi Gazete kanunlarını sorgular.
  - `tuik_mta_search`: TÜİK nüfus/tarım ve MTA maden verilerini doğrular.
  - `knowledge_search`: SQLite FTS5 ambarındaki doğrulanmış iddiaları arar.
  - `fact_verify`: Anti-halüsinasyon kalkanını (Z3 SMT Biçimsel Mantık + ProsecutorAuditor + RefChecker; *SelfCheckGPT: Yol Haritasında*) çalıştırır.

### B. Durum Makineli Otonom Araştırmacı (`autonomous/research_agent.py` & `autonomous/hungry_engine.py`)
- `ResearchJobState` durumları üzerinden ilerler:
  `GOAL_CREATED` ➔ `PLANNING` ➔ `DISCOVERING` ➔ `ACQUIRING` ➔ `EXTRACTING` ➔ `VERIFYING` ➔ `COMPARING` ➔ `GAP_ANALYSIS` ➔ `SYNTHESIZING` ➔ `COMPLETED`.
- Her durum değişimi `research_events` tablosuna zaman damgası ve gerekçesiyle kaydedilir.
- `HungryEngine` 7/24 otonom döngüde müfredat eksiklerini tespit edip asenkron araştırma ve anti-halüsinasyon denetimi tetikler.

### C. Atomik İddia, Kanıt Madenciliği ve Bilgi Güvenlik Duvarı (`brain/knowledge_store.py` & `senses/transcript_processor.py`)
- Transkriptleri ve dokümanları `AtomicClaim` modellerine atomize eder.
- **Knowledge Firewall & Staging:** Doğrulanmamış hiçbir iddia (MNEMONIC, TRAP, FACT dahil) doğrudan kanonik ambara yazılmaz. `stage_pending_record()` ile `atomic_claims` tablosuna `PENDING` olarak alınır; yalnızca denetimden geçen iddialar `commit_verified_claim()` ile kanonize edilir.
- Her claim bir `EvidenceRef` (`source_id`, `video_id`, `segment_id`, `timestamp_str`, `snippet`, `speaker`) taşır.
- `provenance_hash` ile bilginin hangi video ve cümleden türediği matematiksel olarak kanıtlanır.

### D. Çelişki Tespit ve Çözüm Motoru (`cognition/contradiction_engine.py` & `cognition/auditor.py`)
- Farklı hocaların veya eski kaynakların çelişkili ifadelerini tespit eder.
- `OFFICIAL_SOURCE_WINS` politikası ile 1982 Anayasası ve resmî mevzuat hükümleri üstün tutulur.
- Çelişkili hoca iddiaları silinmek yerine `TRAP` (ÖSYM Soru Çeldiricisi) olarak mühürlenir.

### E. Dinamik Optimize Edilmiş Çok Faktörlü Hakimiyet Modeli (`curriculum/queue.py` & `brain/mastery.py`)
- Yapay/sabit skor atamaları yerine `DynamicWeightOptimizer` (Scikit-Learn) ile normalize edilmiş ağırlıklar kullanılır:
  $$\text{Mastery} = w_1 \times \text{SourceCov} + w_2 \times \text{EvidenceDens} + w_3 \times \text{VerifScore} + w_4 \times \text{Agreement} + w_5 \times \text{ConceptCov} + w_6 \times \text{Freshness}$$
- Konunun `MASTERED` sayılabilmesi için $\text{Mastery} \ge 0.85$, çözülmemiş çelişki $= 0$, hedef video $\ge 4$ ve $\ge 2$ farklı eğitmen zorunludur.

---

## 3. V1.5 Doküman, Sınav ve Çok Modlu Bilgi Grafiği Mimarisi

V1.5 sürümü, sisteme PDF ders dokümanlarını, ÖSYM sınav kitapçıklarını, soru kalıplarını, çeldirici tuzakları ve REST API altyapısını entegre eder:

```text
  ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
  │  YouTube Videos │       │  Lecture PDFs   │       │  Official Exams │
  └────────┬────────┘       └────────┬────────┘       └────────┬────────┘
           │                         │                         │
           └────────────────► ◄──────┴────────────────► ◄──────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │    COMMON EVIDENCE MODEL    │
                      │  (Traceable Source Anchors) │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │   CANDIDATE CLAIMS & TRAPS  │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │    AUDITOR VERIFICATION     │
                      │ (Prosecutor / Evidence Gate)│
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │   CANONICAL KNOWLEDGE CORE  │
                      └──────────────┬──────────────┘
                                     │
                      ┌──────────────┴──────────────┐
                      ▼                             ▼
       ┌─────────────────────────────┐┌─────────────────────────────┐
       │   KNOWLEDGE GRAPH (Derived) ││ MISSION CONTROL / REST API  │
       │  - Multimodal Concept Nodes ││ - Real-Time Ingestion Async │
       │  - Semantic Typed Edges     ││ - Deep Provenance Explorer  │
       │  - Pedagogical Traps & Links││ - Honest Progress Stream    │
       └─────────────────────────────┘└─────────────────────────────┘
```

### Temel V1.5 Bileşenleri:
1. **`ingestion/document_manager.py`**: SHA-256 idempotency garantisiyle güvenli doküman alımı.
2. **`ingestion/document_parser.py`**: Sayfa seviyesinde segmentasyon ve OCR tespiti.
3. **`curriculum/document_classifier.py`**: 8 sınıflı doküman sınıflandırması ve kaskat müfredat eşleme.
4. **`ingestion/exam_parser.py`**: Çok sütunlu sınav ayrıştırıcı, 5 seçeneğin verbatim korunması ve olumsuzluk kökü tespiti.
5. **`cognition/question_solver.py`**: Resmi cevap anahtarı üstünlüğü (Kural 7) ve `LLM_DISAGREEMENT` protokolü.
6. **`cognition/pattern_classifier.py`**: 11 soyut ÖSYM soru kalıbı taksonomisi ve çok etiketli eşleme.
7. **`cognition/trap_detector.py`**: Kanıt zorunlu çeldirici ve bilişsel yanılgı modellemesi.
8. **`cognition/exam_statistics_engine.py`**: Yeniden hesaplanabilir sınav soru dağılım ve trend metrikleri.
9. **`brain/v15_graph_sync.py`**: Kanonik SQLite tablolarından türetilen deterministik Bilgi Grafiği senkronizasyonu (Kural 6).
10. **`api/v15_routes.py`**: Doküman yönetimi, sınav zekası, kanıt ve graf gezginini dışa açan Mission Control REST API'si.
