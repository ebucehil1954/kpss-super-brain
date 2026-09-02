# KPSS Super-Brain — Belge ve Sınav Zekâsı Denetimi (DOCUMENT & EXAM AUDIT)

> **Denetim Raporu:** Sınav kitapçığı ayrıştırıcı, çok sütunlu soru segmentasyonu, çeldirici/tuzak analizi ve soru kalıbı öğrenimi

---

## 1. Sınav ve Soru Ayrıştırma Altyapısı (Exam Parser)

[exam_parser.py](file:///c:/Users/PC1/Desktop/promius/kpss-super-brain/ingestion/exam_parser.py) motoru KPSS sınav kitapçıklarının karmaşık yapısını adli hassasiyetle parçalara ayırır:

```text
[PDF / Metin Sınav Kitapçığı]
            │
            ▼
[Question Header Detector]: Soru 1., 2-, 3) tespiti
            │
            ▼
[Soru Gövdesi Ayrıştırma]:
  ├── Öncüller (Roman Numerals: I., II., III., IV.)
  ├── Soru Kökü (Stem)
  └── Olumsuz İfade Tespiti ("değildir", "yoktur", "savunulamaz")
            │
            ▼
[Seçenek Ayrıştırıcı]:
  ├── 5 Seçenek Garantisi (A, B, C, D, E)
  └── Sayfa Sonu / Sütun Kayması Kurtarma
            │
            ▼
[SQLite Mühürleme]:
  ├── v15_exams
  ├── v15_questions
  └── v15_question_options (is_correct, is_trap, trap_type)
```

---

## 2. Çeldirici ve Tuzak Zekâsı (Trap & Distractor Intelligence)

[trap_detector.py](file:///c:/Users/PC1/Desktop/promius/kpss-super-brain/cognition/trap_detector.py):
ÖSYM'nin soru hazırlama mantığında kullandığı 6 temel bilişsel çeldirici kategorize edilmiştir:

1. `CHRONOLOGY_CONFUSION`: Kronolojik yanılgı (tarihsel olayların sırasını ters verme)
2. `SIMILAR_TERM_CONFUSION`: Benzer terim karmaşası (İltizam vs Malikane, İmar vs İskan)
3. `EXCEPTION_TRAP`: İstisna tuzağı (genel anayasa kuralı yerine özel istisnayı sorma)
4. `CAUSE_RESULT_REVERSAL`: Sebep-sonuç tersyüzü (sonucu sebep gibi sunma)
5. `CONCEPT_SWAP`: Kavram takası (iki mahkemenin veya padişahın yetkilerini yer değiştirme)
6. `NUMBER_SWAP`: Sayı / oran kaydırma (TBMM 3/5 yerine 2/3 çeldiricisi)

### 2.1 Tuzak Mühürleme Kuralı
- Bir tuzak kaydının oluşturulabilmesi için **en az bir gerçek soruya (`supporting_question_id`)** ve **çeldiricilik gerekçesine (`why_attractive`)** dayanması zorunludur. Spekülatif tuzak üretilmez.

---

## 3. Kritik Soruların Değerlendirmesi

### Soru 12: Sınavlardan yalnızca soruları mı depoluyor, yoksa soru kalıplarını, distractor'ları ve sınav mantığını da öğrenebiliyor mu?
**Cevap:** **EVET (Distractor ve Tuzak Mantığı Ayrıştırılıyor).**
- *Kanıt 1:* `v15_question_options` tablosunda her bir seçeneğin `is_trap` bayrağı ve `trap_type` sınıflandırması vardır.
- *Kanıt 2:* Soru kökündeki olumsuz ifadeler (`is_negative_stem = 1`) otomatik tespit edilir.
- *Kanıt 3:* Çözülen sorulardaki çeldirici seçenekler `v15_traps` tablosuna beslenerek daha sonra soru türetiminde distractor şablonu olarak kullanılır.
