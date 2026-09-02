# 🧬 KPSS Super-Brain: Bilgi ve İddia Modeli (KNOWLEDGE_MODEL.md)

Bu doküman, sistemdeki tüm atomik bilgi nesnelerinin (Claim), kanıt referanslarının (EvidenceRef) ve kavram hiyerarşisinin veri yapısını açıklar.

---

## 1. Atomik İddia Modeli (`AtomicClaim`)

Her bilgi parçası, kaynak referansı ve zaman geçerliliği ile birlikte Pydantic v2 modeli olarak temsil edilir:

```python
class AtomicClaim(BaseModel):
    claim_id: str                   # Benzersiz ve deterministik hash ID (claim_a1b2c3d4)
    text: str                       # Kesin sınav iddiası metni
    lesson: str                     # VATANDASLIK, TARIH, COGRAFYA, vb.
    topic: str                      # 1982 Anayasası Yasama Organı
    subtopic: str                   # TBMM Toplantı ve Karar Yeter Sayıları
    claim_type: ClaimType           # FACT, DEFINITION, LEGAL_RULE, DATE, NUMBER, MNEMONIC, TRAP, vb.
    subject: Optional[str]          # Bilgi grafiği öznesi (Örn: Anayasa Mahkemesi)
    predicate: Optional[str]        # İlişki (Örn: UYE_SAYISI)
    object_val: Optional[str]       # Değer (Örn: 15)
    evidence_refs: List[EvidenceRef]# Kaynak ve video segment bağlantıları
    confidence: float               # 0.0 - 1.0 arası hesaplanmış güven skoru
    temporal_status: str            # ACTIVE, REPEALED, HISTORICAL, SUPERSEDED
    verification_status: str        # VERIFIED, REJECTED, CONTRADICTORY, UNVERIFIED
    provenance_hash: str            # sha256(lesson:topic:text)
```

---

## 2. Desteklenen İddia Türleri (`ClaimType`)

| Tür | Açıklama | Örnek |
|---|---|---|
| `FACT` | Olgusal kesin sınav bilgisi | "TBMM 600 milletvekilinden oluşur." |
| `LEGAL_RULE` | Anayasa ve mevzuat normu | "Kanun teklif etmeye milletvekilleri yetkilidir." |
| `DATE` | Tarihsel olay veya yürürlük yılı | "1982 Anayasası 7 Kasım 1982'de yürürlüğe girmiştir." |
| `NUMBER` | Sayısal karar/toplantı nisabı | "TBMM karar yetersayısı 151'den az olamaz." |
| `MNEMONIC` | Akrostiş ve hafıza şifresi | "[KODLAMA] OYAK: Olağanüstü Yönetim Usulleri..." |
| `TRAP` | ÖSYM'nin kurduğu çeldirici tuzak | "TUZAK: Başbakanlık mülga edilmiştir, yürürlükte değildir." |
| `TEACHER_INSIGHT` | Duayen eğitmenin pedagojik vurgusu | "Ramazan Yetgin: Bu padişahın divan üyelerine dikkat!" |

---

## 3. Çok Modlu Kanıt Modeli (`UnifiedEvidence`)

Sistem YouTube video segmentleri ile PDF/DOCX doküman sayfalarını tek bir kanıt tablosunda (`v15_evidence`) birleştirir:

```python
class UnifiedEvidence(BaseModel):
    evidence_id: str                # ev_<uuid>
    source_type: str                # DOCUMENT | YOUTUBE
    document_id: Optional[str]      # PDF/Ders dokümanı referansı
    page_number: Optional[int]      # 1-indexed sayfa numarası
    video_id: Optional[str]         # YouTube video ID
    transcript_start_seconds: Optional[float]
    transcript_end_seconds: Optional[float]
    evidence_text: str              # Kaynaktan çıkarılan ham kanıt alıntısı
    content_hash: str               # sha256(evidence_text)
```

---

## 4. Sınav ve Soru Varlıkları Modeli

ÖSYM ve deneme sınavı kitapçıklarının atomik soru modellemesi:

1. `ExamRecord`: Sınav üst verisi (`exam_code`, `year`, `total_questions`, `has_official_key`).
2. `QuestionRecord`: Soru kökü, öncüller (`premises`), olumsuzluk bayrağı (`is_negative`), 1-indexed `page_number`.
3. `QuestionOptionRecord`: 5 seçeneğin verbatim metni (`A`-`E`), `is_correct_official`, `is_trap`, `trap_type`.
4. `AnswerKeyRecord`: Birinci sınıf kanıt niteliğindeki resmi cevap anahtarı (Kural 7).
5. `QuestionPatternRecord`: 11 soyut ÖSYM soru kalıbı taksonomisi.
6. `TrapRecord`: Destekleyici soru ve çeldirici gerekçesi (`why_attractive`) zorunlu bilişsel yanılgı modeli.

---

## 5. Türetilmiş Bilgi Grafiği Varlıkları (Kural 6)

Grafik SQLite kanonik tablolarından sıfırdan yeniden üretilebilir (derived representation):
- **Düğümler (Nodes)**: `CONCEPT`, `CLAIM`, `DOCUMENT`, `VIDEO`, `QUESTION`, `PATTERN`, `TRAP`, `TEACHER_INSIGHT`
- **Kenarlar (Edges)**: `RELATES_TO`, `TESTS`, `USES_PATTERN`, `EXEMPLIFIES_TRAP`, `CONFUSED_WITH`, `EVIDENCED_BY`, `SOURCE_DOC`
