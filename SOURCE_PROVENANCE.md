# 📜 KPSS Super-Brain: Kaynak ve Provenance İzlenebilirliği (SOURCE_PROVENANCE.md)

Bu doküman, sistemdeki her bilginin kaynağının (`Source`), video zaman damgasının (`TranscriptSegment`) ve matematiksel hash'inin nasıl izlendiğini belgeler.

---

## 1. Provenance İlkeleri

1. **Kaynaksız Bilgi Yasaktır**: Kaynak referansı olmayan hiçbir iddia `VERIFIED` statüsü kazanamaz.
2. **Sahte Fallback İzolasyonu**: Transkript çekilemediğinde web özeti video transkripti yerine konamaz.
3. **Zaman Damgası (Timestamp Alignment)**: İddialar mümkün olan durumlarda YouTube videosunun başlangıç ve bitiş saniyelerine bağlanır.

---

## 2. Kanıt Referans Modeli (`EvidenceRef`)

```json
{
  "source_id": "src_yt_gH7q9X1",
  "source_type": "YOUTUBE_TRANSCRIPT",
  "video_id": "gH7q9X1",
  "segment_id": "seg_gH7q9X1_12",
  "snippet": "1982 Anayasası Madde 146 uyarınca Anayasa Mahkemesi 15 üyeden oluşur.",
  "speaker_or_author": "Emrah Vahap Özkaraca",
  "timestamp_str": "04:12 - 04:35"
}
```

---

## 3. Provenance Doğrulama Akışı

```text
Claim Text
    ↓ (SHA-256 Hash)
provenance_hash
    ↓ (Evidence Connection)
v15_evidence (source_type = 'DOCUMENT' | 'YOUTUBE')
    ├─ DOCUMENT: document_id + 1-indexed page_number + SHA-256 original PDF
    └─ YOUTUBE: video_id + transcript_start_seconds / end_seconds
    ↓ (Database Lookup & Verification)
v15_documents / v15_document_pages / transcript_segments
    ↓
Orijinal PDF Sayfası / Resmi Cevap Anahtarı / Video Zaman Damgası
```

---

## 4. Denetim Durum Makinesi (Audit State Machine)

Aday iddialar doğrudan kanonik depoya giremez; aşağıdaki geçiş matrisini takip eder:

```text
[CANDIDATE] (Yeni çıkarılan ham iddia)
    │
    ├── Kanıt doğrulanamaz veya çelişkili ise ──► [REJECTED]
    ├── Birden fazla kaynaktan destek varsa ───► [SUPPORTED]
    └── Savcı Denetçi onayladığında ───────────► [VERIFIED] (Kanonik Mühürleme)
```

---

## 5. Değişmez Güvenlik Kuralları

1. **Halüsinatif Sayfa Numarası Yasağı**: 1-indexed sayfa numarası gerçekte ayrıştırılmış `v15_document_pages` tablosundaki bir kayda karşılık gelmek zorundadır.
2. **Resmi Cevap Anahtarı Üstünlüğü (Kural 7)**: LLM çözümleri resmi cevap anahtarı ile çelişirse, resmi anahtar asla ezilmez; `LLM_DISAGREEMENT` bayrağı ile kayıt altına alınır.
3. **Tuzak Kanıtı Zorunluluğu**: Bir çeldirici, en az bir gerçek sınav sorusuna (`supporting_question_id`) ve cazibe gerekçesine (`why_attractive`) bağlanmadan tuzak olarak kaydedilemez.
