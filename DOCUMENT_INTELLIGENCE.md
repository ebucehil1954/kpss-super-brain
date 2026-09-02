# 📄 KPSS Super-Brain: Doküman Zekası (DOCUMENT_INTELLIGENCE.md)

Bu doküman, V1.5 mimarisinde PDF, DOCX ve taranmış ders dokümanlarının sisteme güvenle alınmasını, parçalanmasını, sınıflandırılmasını ve kanıt tabanlı iddia çıkarımını belgeler.

---

## 1. Doküman İşleme Hattı (Pipeline)

```text
Yüklenen Dosya (PDF/DOCX)
       ↓
[DocumentManager] (SHA-256 Sağlama, Dosya Depolama, Çift Kayıt Engelleme)
       ↓
[DocumentParser] (Sayfa Sayfa Segmentasyon, Metin Temizleme, OCR Tespiti)
       ↓
[DocumentClassifier] (8 Sınıflı Doküman Tipi, Müfredat Dersi & Konusu)
       ↓
[DocumentAnalyst] (12 Türde Aday İddia Çıkarımı, v15_evidence Bağlantısı)
       ↓
[V15AuditorBridge] (ProsecutorAuditor Doğrulama Kapısı)
       ↓
Kanonik Bilgi Deposu (knowledge_records) & Bilgi Grafiği
```

---

## 2. Temel İlkeler ve Güvenlik Kuralları

1. **Kaynak Hakikat Değildir**: Ham doküman metni doğrudan kanonik bilgi sayılamaz. Savcı denetçiden (`ProsecutorAuditor`) geçmeden sisteme mühürlenemez.
2. **Kaskat Müfredat Çözümleme**: Müfredat eşleme güven eşiğinin altındaysa varsayım yapılmaz; kesinlikle `lesson = 'UNKNOWN'` ve `topic_id = 'UNKNOWN'` atanır.
3. **Idempotency (Tekillik)**: Aynı içeriğe sahip bir PDF tekrar yüklendiğinde SHA-256 kontrolü ile mevcut kayıt döner, mükerrer veri üretilmez.
4. **1-Indexed Sayfa Numaralandırması**: Akademik ve resmi sınav atıflarına uygun olarak tüm sayfa numaraları 1'den başlar.
5. **OCR İşaretlemesi**: Görsel tarama tespit edilen sayfalarda `is_ocr = 1` bayrağı atanır.

---

## 3. İlişkisel Veri Modeli

### `v15_documents`
- `document_id`: Deterministik doküman ID'si (`doc_<hash>`)
- `sha256`: Dosya içeriğinin SHA-256 hash değeri (UNIQUE)
- `filename`: Orijinal dosya adı
- `storage_path`: Dosyanın korumalı disk konumu (`data/documents/...`)
- `classification`: Doküman türü (`COURSE_MATERIAL`, `EXAM`, `QUESTION_BANK`, `OFFICIAL`, `ANSWER_KEY`, `REFERENCE`, `UNKNOWN`)
- `lesson` / `topic_id`: Müfredat bağlamı
- `parsing_status`: `PENDING`, `PARSED`, `FAILED`

### `v15_document_pages`
- `page_id`: Benzersiz sayfa kimliği (`dp_<doc_id>_<page_num>`)
- `document_id`: Üst doküman bağlantısı (FK)
- `page_number`: 1-indexed sayfa numarası
- `raw_text` & `cleaned_text`: Ayrıştırılmış ve temizlenmiş sayfa metni
- `is_ocr`: OCR gereksinimi bayrağı (0 veya 1)

### `v15_evidence`
- `evidence_id`: Birleşik multimodal kanıt kimliği (`ev_<hash>`)
- `source_type`: `DOCUMENT` veya `YOUTUBE`
- `document_id` & `page_number`: Doküman kaynak koordinatları
- `video_id` & `transcript_start_seconds` / `transcript_end_seconds`: Video koordinatları
- `evidence_text`: İddianın dayandığı verbatim kanıt metni

### `v15_candidate_claims`
- `claim_id`: Aday iddia kimliği (`claim_<hash>`)
- `evidence_id`: Zorunlu kanıt bağlantısı (FK)
- `claim_type`: 12 türden biri (`FACT`, `DEFINITION`, `DATE`, `NUMBER`, `CLASSIFICATION`, `RELATION`, `CAUSE_EFFECT`, `COMPARISON`, `EXCEPTION`, `PROCESS`, `RULE`, `TEACHING_INSIGHT`)
- `subject`, `predicate`, `object_val`: Semantik bilgi üçlüsü
- `raw_statement`: Doğal dil ifadesi
- `audit_status`: `CANDIDATE`, `VERIFIED`, `REJECTED`
