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
  - `fact_verify`: 4 katmanlı halüsinasyon kalkanını (RefChecker + Z3 + SelfCheckGPT) çalıştırır.

### B. Durum Makineli Otonom Araştırmacı (`autonomous/research_agent.py`)
- `ResearchJobState` durumları üzerinden ilerler:
  `GOAL_CREATED` ➔ `PLANNING` ➔ `DISCOVERING` ➔ `ACQUIRING` ➔ `EXTRACTING` ➔ `VERIFYING` ➔ `COMPARING` ➔ `GAP_ANALYSIS` ➔ `SYNTHESIZING` ➔ `COMPLETED`.
- Her durum değişimi `research_events` tablosuna zaman damgası ve gerekçesiyle kaydedilir.

### C. Atomik İddia ve Kanıt Madenciliği (`senses/transcript_processor.py`)
- Transkriptleri `AtomicClaim` modellerine atomize eder.
- Her claim bir `EvidenceRef` (`source_id`, `video_id`, `segment_id`, `timestamp_str`, `snippet`, `speaker`) taşır.
- `provenance_hash` ile bilginin hangi video ve cümleden türediği matematiksel olarak kanıtlanır.

### D. Çelişki Tespit ve Çözüm Motoru (`cognition/contradiction_engine.py`)
- Farklı hocaların veya eski kaynakların çelişkili ifadelerini tespit eder.
- `OFFICIAL_SOURCE_WINS` politikası ile 1982 Anayasası ve resmî mevzuat hükümleri üstün tutulur.

### E. Deterministik Çok Faktörlü Hakimiyet Modeli (`brain/curriculum_matrix.py`)
- Yapay/sabit skor atamaları yasaktır.
- Formül:
  $$\text{Mastery} = 0.25 \times \text{SourceCov} + 0.20 \times \text{EvidenceDens} + 0.20 \times \text{VerifScore} + 0.15 \times \text{Agreement} + 0.10 \times \text{ConceptCov} + 0.10 \times \text{Freshness}$$
