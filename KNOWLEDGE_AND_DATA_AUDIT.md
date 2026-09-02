# KPSS Super-Brain — Bilgi ve Veri Modeli Denetimi (KNOWLEDGE & DATA AUDIT)

> **Denetim Raporu:** Veri modelleri, Knowledge Firewall, Knowledge Graph, dinamik ağırlıklar ve bilgi korelasyonu

---

## 1. Epistemik Veri Hiyerarşisi ve Şemalar

```text
[Raw Video/Document] ──► [EvidenceRef] (Segment, Timestamp, Snippet)
                               │
                               ▼
                      [AtomicClaim] (Subject, Predicate, Object, Confidence, PENDING)
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
[Contradiction Check / Z3 / R1]            [ProvenanceValidator]
            │                                     │
            ▼                                     ▼
    [VerificationRecord]                  [KnowledgeRecord] (CANON)
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                     [KPSSKnowledgeGraph]
              (Nodes: Concept, Edges: Prerequisite, Confused_With)
```

---

## 2. Knowledge Firewall (Bilgi Güvenlik Duvarı) Değerlendirmesi

### 2.1 İki Kademeli Ambar Ayrımı
1. **Staging Tablosu (`atomic_claims`):** YouTube ve dokümanlardan çıkarılan ham iddialar buraya `PENDING` durumunda kaydedilir.
2. **Kanonik Tablo (`knowledge_records`):** Yalnızca doğrulama süzgecinden geçen, kanıt zinciri tam olan kayıtlar buraya aktarılır.
3. **Güven Skoru Artırımı (Reinforcement Invariant):**
   - Tek kaynaktan gelen iddiaların güven tavanı: `0.90`
   - Çapraz öğretmen mutabakatı (farklı hoca): `+0.05` (Maks `0.95`)
   - Resmî mevzuat eşleşmesi: `+0.04` (Maks `0.99`)

### 2.2 Mimari İhlal (Bkz. Bulgu 1)
`prosecutor_auditor.py` L189'da REJECTED iddialardan türetilen TRAP metinleri, Knowledge Firewall'ı atlayarak doğrudan `knowledge_records` tablosuna yazılmaktadır. Bu açık derhal kapatılmalıdır.

---

## 3. KPSSKnowledgeGraph (Bilgi Grafı) Analizi

[knowledge_graph.py](file:///c:/Users/PC1/Desktop/promius/kpss-super-brain/brain/knowledge_graph.py):
- **Graf Motoru:** Ağ düğümleri (`CONCEPT`, `TOPIC`, `LESSON`, `EXAM_QUESTION`) ve kenarları (`PREREQUISITE_OF`, `OFTEN_CONFUSED_WITH`, `CONTRASTS`, `REGULATED_BY`).
- **Döngü Engelleme (Cycle Prevention):** `PREREQUISITE_OF` ilişkisi bir DAG (Directed Acyclic Graph) oluşturmalıdır. `has_cycle()` fonksiyonu DFS ile döngü kontrolü yapar; döngü tespit edilirse kenar eklenmez.
- **Kalıcılık:** `threading.RLock()` ile bellek içi işlemler kilitlenir. Diske yazılırken geçici dosyaya dump edilir ve `os.replace` ile atomik olarak hedef dosyanın üzerine yazılır (elektrik kesintisi veya çökmede dosya bozulmaz).

---

## 4. Dinamik Ağırlık Öğrenme Modeli (Dynamic Weight Optimizer)

[mastery.py](file:///c:/Users/PC1/Desktop/promius/kpss-super-brain/brain/mastery.py):
- Sabit sezgisel katsayılar yerine `scikit-learn LogisticRegression` ve `StandardScaler` kullanılarak soru çözme sonuçlarından kaynak ağırlıkları optimize edilir:
  - Resmî Mevzuat katkısı
  - ÖSYM Çıkmış Soru katkısı
  - Eğitmen çeşitliliği katkısı
  - Eğitmenler arası mutabakat katkısı
  - PDF/Ders notu katkısı
  - Güncellik katkısı
- Katsayılar softmax normalizasyonu ile [0, 1] arasına çekilir.

---

## 5. Kritik Soruların Değerlendirmesi

### Soru 10: Sistem gerçekten bilgi korelasyonu kuruyor mu, yoksa yalnızca verileri birbirinden bağımsız mı saklıyor?
**Cevap:** **GERÇEK KORELASYON KURUYOR.**
- *Kanıt 1:* `correlation_engine.py`, 8 kanonik karıştırılan kavram çifti (`OFTEN_CONFUSED_WITH`) tanımlamıştır (Toplantı Yeter vs Karar Yeter, Vali vs Kaymakam vb.).
- *Kanıt 2:* Veritabanındaki TRAP kayıtlarından regex ve semantik desenlerle yeni kavram karşıtlıkları dinamik olarak Knowledge Graph'a kenar olarak eklenmektedir (`discover_correlations_from_db`).

### Soru 15: Sistem uzun süre 7/24 çalıştığında veri bozulması, memory leak veya self-reinforcing hallucination riski oluşabilir mi?
**Cevap:**
- **Veri Bozulması:** DÜŞÜK. WAL mode + atomik dosya kaydetme veri bozulmasını engeller.
- **Memory Leak:** DÜŞÜK - ORTA. Graf nesnesi tümüyle bellekte tutulmaktadır; düğüm sayısı 50.000'i aşarsa RAM kullanımı artabilir.
- **Self-reinforcing Hallucination:** Standart fact'lerde ENGELLENMİŞTİR (aynı kaynaktan artış kısıtlıdır). Ancak Savcı TRAP bypass'ı (Bulgu 1) düzeltilmezse sentetik tuzaklarda halüsinasyon birikimi riski mevcuttur.
