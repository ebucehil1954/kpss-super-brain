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
