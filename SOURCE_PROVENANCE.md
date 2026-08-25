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
EvidenceRef -> Video ID / Segment ID
    ↓ (Database Lookup)
SQLite `transcript_segments` / `sources`
    ↓
Original YouTube Video Timestamp / Mevzuat URL
```
