# CURRENT_STATE.md — KPSS Super-Brain Repository Forensics & Baseline Report

**Inspection Date:** 2026-08-27  
**Commit Baseline:** `ed134c3`  
**Test Baseline:** 100 collected, 98 PASSED, 2 FAILED (Time: 126.13s)

---

## 1. Current Architecture Overview

```text
                                 MÜFREDAT MATRİSİ
                            (curriculum/engine.py: 56 Konu)
                                         │
                                         ▼
                                   SUPERVISOR
                            (autonomous/research_planner.py)
                                         │
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
             Video Kuyruğu                            Araştırma Görevi
          (curriculum/queue.py)                     (ResearchTask Contract)
                     │                                       │
                     ▼                                       ▼
            YOUTUBE KARADELİĞİ                       OPENMANUS SAHA İŞÇİSİ
         (autonomous/harvester.py)               (openmanus/app/agent/kpss_agent)
                     │                                       │
                     └───────────────────┬───────────────────┘
                                         ▼
                             TRANSKRİPT VE KANITLAR
                          (senses/transcript_processor.py)
                                         │
                                         ▼
                             BİLİŞSEL ANALİST (LLM)
                             (cognition/analyst.py)
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
                 Aday İddialar                      Hoca Zihni
                 (CandidateClaims)             (TeacherLearner & Profiles)
                         │
                         ▼
             ═════════════════════════════════════════════
             [KNOWLEDGE FIREWALL İHLALİ - TESPİT EDİLDİ]
             ═════════════════════════════════════════════
                         │ (Doğrudan Yazım Mevcut!)
                         ▼
                 KNOWLEDGE STORE & GRAPH
              (brain/knowledge_store.py)
                         ▲
                         │ (Denetim Sonradan Geliyor!)
              DENETLEYİCİ & SAVCILIK MOTORU
         (cognition/auditor.py + prosecutor_auditor.py + Z3)
```

---

## 2. Component Dependencies & Directory Map

- **`curriculum/`**: 3 sınavlı müfredat modelleri (`models.py`), altın standart hoca/kanal listeleri (`sources.py`), eksik radarı (`engine.py`), SQLite destekli görev/video kuyruğu (`queue.py`).
- **`autonomous/`**: Otonom saha işçisi (`harvester.py`), görev yöneticisi (`research_agent.py`), öncelik kuyruğu (`priority_queue.py`), araç kütüğü (`tool_registry.py`).
- **`senses/`**: Çok katmanlı transkript çekici (`transcript_fetcher.py`), transkript işleyici (`transcript_processor.py`), video kuyruğu (`video_queue.py`).
- **`brain/`**: SQLite veritabanı şeması ve WAL oturumları (`database.py`), bilgi ambarı (`knowledge_store.py`), epistemik modeller (`models.py`), DAG/Graf motoru (`knowledge_graph.py`), muhakeme ambarı (`reasoning_store.py`).
- **`cognition/`**: Bilişsel analist (`analyst.py`), eğitmen modelleme (`teacher_learner.py`), çapraz hoca sentezleyici (`cross_teacher_analyzer.py`), korelasyon grafı (`correlation_engine.py`), Z3 kalkanı (`auditor.py`), DeepSeek-R1 savcılık motoru (`prosecutor_auditor.py`).
- **`anti_hallucination/`**: Z3 SMT çözücüsü (`z3_logic_validator.py`), 7 kademeli bilgi doğrulayıcı (`fact_checker.py`), çoklu hakem denetimi (`multi_referee.py`).
- **`canonical_facts/`**: 1982 Anayasası kanun maddeleri (`constitution_facts.jsonl`), Osmanlı kronolojisi (`history_facts.jsonl`), TÜİK coğrafya verileri (`geography_facts.jsonl`).
- **`openmanus/`**: `YouTubeCrawlerTool`, `KPSSAgent`, sandbox ve terminal araçları.

---

## 3. Data Flow & Persistence Map

| Veri Varlığı | Kaynak | Birincil Yazma Yolu | İkincil / Türetilmiş Depo |
|---|---|---|---|
| **Video Metadata** | YouTube Search (`yt_dlp` / OpenManus) | `video_queue` (SQLite) | `topic_mastery.consumed_video_ids_json` |
| **Transkript** | `transcript_fetcher.py` (Resilient) | `video_transcripts` (SQLite) | Cache / Bellek |
| **Aday İddia (Claim)** | `senses/transcript_processor.py` | `atomic_claims` (SQLite) | Geçici liste |
| **Kanonik Bilgi (FACT)** | `cognition/analyst.py` / `transcript_processor.py` | `knowledge_records` (SQLite) | FTS5 Index / `knowledge_graph.json` |
| **Ezber Şifresi (MNEMONIC)** | `cognition/analyst.py` | `knowledge_records` (`record_type='MNEMONIC'`) | `teacher_profiles.mnemonics_used_json` |
| **Sınav Tuzağı (TRAP)** | `cognition/auditor.py` / `prosecutor_auditor.py` | `knowledge_records` (`record_type='TRAP'`) | Web Paneli Tuzak Listesi |
| **İlişki Kenarları** | `cognition/correlation_engine.py` | `data/knowledge_graph.json` | Bellek İçi Graf |
| **Savcılık Hükümleri** | `cognition/prosecutor_auditor.py` | `prosecutor_audits` (SQLite) | Web Paneli Hüküm Akışı |

---

## 4. LLM Call Map

| Çağrı Yeri | Model | Amaç | Sıcaklık | Format |
|---|---|---|---|---|
| `cognition/analyst.py` | `qwen2.5:14b` | 5 Katmanlı Bilgi Çıkarımı (Fact, Trap, Mnemonic) | 0.15 | JSON |
| `cognition/prosecutor_auditor.py` | `deepseek-r1:8b` | Adversarial Savcılık Denetimi ve Hakemlik | 0.00 | JSON + `<think>` |
| `senses/transcript_processor.py` | `qwen2.5:14b` | Transkript bloklarından iddia ayrıştırma | 0.20 | JSON |
| `anti_hallucination/multi_referee.py`| `qwen2.5:14b` / Fallback | Çift-kör soru ve iddia hakemliği | 0.10 | Metin / JSON |
| `autonomous/research_agent.py` | `qwen2.5:14b` | Görev tamamlama evaluatörü | 0.10 | JSON |

---

## 5. Baseline Test Sonuçları ve Yeniden Üretilen Hatalar

### A. pytest Çalıştırma Komutu:
`python -m pytest tests -v`

### B. Başarısız Olan Testler (2 Adet):
1. **`tests/test_agentic_research_and_integrity.py::test_provenance_and_segment_timestamp_integrity`**
   - **Hata:** `AttributeError: 'ReasoningStore' object has no attribute 'add_chain'`
   - **Konum:** `senses/transcript_processor.py:282`
   - **Kök Neden:** `transcript_processor.py`, `reasoning_store.save_reasoning_chain` yerine var olmayan `add_chain` metodunu çağırmaktadır.

2. **`tests/test_final_hardening_integration.py::test_task11_mocked_end_to_end_reaches_completed`**
   - **Hata:** `AssertionError: Araştırma COMPLETED olmalıydı, hata: RESEARCH_EXCEPTION: 'ReasoningStore' object has no attribute 'add_chain'`
   - **Konum:** `autonomous/research_agent.py:188` üzerinden çağrılan transkript işleme adımı.
   - **Kök Neden:** Aynı `ReasoningStore.add_chain` eksikliği entegrasyon araştırmasını patlatmaktadır.

---

## 6. Kritik P0 ve P1 Açıkları Haritası (Master Plan Kapsamı)

| Öncelik | Faz | Konu | İlgili Dosya / Fonksiyon | Mevcut Durum / Risk |
|---|---|---|---|---|
| **P0** | **PHASE 1** | Sahte YouTube ID Üretimi | `senses/transcript_fetcher.py`, `autonomous/harvester.py` | Arama başarısız olunca sentetik ID üretilmemeli, `DISCOVERY_FAILED` dönmeli. |
| **P0** | **PHASE 2** | Knowledge Firewall İhlali | `senses/transcript_processor.py:224` | Raw LLM çıktısı doğrudan `knowledge_store.add_record` ile kaydediliyor; doğrulama kalkanını bypass ediyor. |
| **P0** | **PHASE 3** | Tekrar Frekansı != Gerçeklik | `brain/knowledge_store.py:add_or_reinforce_record` | Tekrar sayısı güven skorunu (`confidence`) yapay olarak artırmamalı; `repeat_count` ile `trust_score` ayrılmalı. |
| **P0** | **PHASE 4** | Video Sayısı != Hakimiyet | `brain/curriculum_matrix.py`, `curriculum/queue.py` | 4 video izlemek tek başına konuyu `MASTERED` yapmamalı; kavram ve doğrulanmış iddia kapsamı aranmalı. |
| **P1** | **PHASE 5** | Görev Sözleşmeleri Ayrımı | `curriculum/models.py`, `autonomous/research_agent.py` | `ResearchTask` asla `VideoTask` gibi video işleyicisine doğrudan verilmemeli. |
| **P1** | **PHASE 6** | OpenManus Sınır İhlali | `openmanus/app/agent/kpss_agent.py` | OpenManus araştırır; doğrudan kanonik veritabanına yazamaz ve güven skoru değiştiremez. |
| **P1** | **PHASE 7** | Kanal Taraması vs Global Arama | `openmanus/app/tool/youtube_crawler_tool.py` | Kanal taraması ile küresel arama ayrılmalı. |
| **P1** | **PHASE 8** | Bilinmeyen Ders -> TARIH Hatası | `senses/transcript_processor.py`, `curriculum/models.py` | Bilinmeyen ders asla sessizce TARIH yapılmamalı, `UNKNOWN` kalmalı. |
| **P1** | **PHASE 9** | Güvenli Konu Eşleyici (Topic Resolver) | `brain/curriculum_matrix.py` | Yanlış konuya sessiz eşleme engellenmeli. |
| **P1** | **PHASE 10**| Bilgi Grafı Döngü Semantiği | `brain/knowledge_graph.py` | Graf salt DAG değil; `CONTRADICTS` ve `CONFUSED_WITH` döngüye izin vermeli, sadece `PRECEDES` asiklik olmalı. |
| **P1** | **PHASE 11**| AtomicClaim - KnowledgeRecord Bağı | `brain/models.py`, `brain/knowledge_store.py` | Kanonik kayıt `claim_id` ve tam kanıt zincirini (`provenance`) saklamalı. |
| **P1** | **PHASE 12**| Tek Yetkili Kanonik Gerçek Kaynağı | `brain/knowledge_store.py` | Vektör veya graf veritabanı bağımsız olarak kanonik gerçeği tanımlayamaz. |
| **P2** | **PHASE 13**| Yeniden Deneme (Retry) Sınıflandırması | `senses/transcript_fetcher.py` | Kalıcı hatalar (404, doğrulama) tekrar denenmemeli; geçici hatalar (timeout) backoff ile denenmeli. |
| **P2** | **PHASE 14**| Whisper / CUDA Ortam Tespiti | `config.py`, `senses/transcript_fetcher.py` | CUDA kontrolü sadece ortam değişkenine değil `torch.cuda.is_available()` gerçeğine dayanmalı. |
| **P2** | **PHASE 15**| Orkestrasyon Ayrımı | `autonomous/harvester.py` | Orkestrasyon ile düşük seviye transkript madenciliği net sınırla ayrılmalı. |
| **P2** | **PHASE 16**| Graf Kalıcılığı Toplu Yazım (Batching) | `brain/knowledge_graph.py:save` | Her kenar eklendiğinde tüm dosya diske yazılmamalı, `batch_add` veya periyodik save yapılmalı. |
| **P2** | **PHASE 17**| Eğitmen Modeli Gözlemlenebilir Sinyaller | `cognition/teacher_learner.py` | Model eğitmenin 'zihnini' değil; gözlemlenebilir pedagojik şifre ve soru kalıplarını modellemeli. |

---

## 7. Phase 0 Çıkış Kriterleri Doğrulaması
- [x] Tüm depo yapısı, giriş noktaları ve veritabanı yazma yolları incelendi.
- [x] Temel testler (`pytest`) çalıştırıldı ve mevcut 2 hata kaydedildi.
- [x] Davranış değiştiren rastgele yama yapılmadı; sistematik `CURRENT_STATE.md` oluşturuldu.
- [x] Tüm P0 ve P1 maddeleri somut dosya ve fonksiyonlarla eşleştirildi.
