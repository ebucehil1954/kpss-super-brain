# KPSS Super-Brain — Yeni Özellik ve Geliştirme Önerileri (FEATURE RECOMMENDATIONS)

Bu belge, KPSS Super-Brain sistemini bir "veri ambarı" seviyesinden gerçek bir **"KPSS Otonom Süper-Zekâsı ve Eğitim SaaS Bilgi Motoru"** seviyesine taşıyacak yeni özellikleri 4 öncelik kategorisinde sunar.

---

## 1. CRITICAL (Kritik Öncelikli Özellikler)

### 1.1 Vektör İndeksli Aday Eşleştirme ile Semantik Çelişki Motoru
- **Gerekçe:** O(n²) karşılaştırma darboğazını (Bulgu 3) ortadan kaldırmak için FAISS veya SQLite-VSS entegrasyonu.
- **İşleyiş:** Yeni gelen iddia önce vektör indeksinde en yakın 5 komşusuyla eşleştirilir; yalnızca kosinüs benzerliği > 0.70 olan adaylar derin LLM denetimine gönderilir.

### 1.2 Unified Verification Gateway (Birleşik Doğrulama Kapısı)
- **Gerekçe:** `FactChecker`, `AuditorEngine` (Z3) ve `ProsecutorAuditor` (DeepSeek-R1) arasındaki dağınıklığı ve firewall baypaslarını (Bulgu 1) tek noktada toplamak.
- **İşleyiş:** Tüm iddialar sırasıyla:
  1. Provenance Kontrolü (Segment & Video doğrulaması)
  2. Z3 Mantık Denetimi (Sayısal Anayasa kuralları)
  3. DeepSeek-R1 Savcılık Denetimi
  adımlarından geçmeden asla kanonik hafızaya (`knowledge_records`) mühürlenemez.

### 1.3 Knowledge Versioning (Bilgi Sürümleme ve Mevzuat Değişiklik Takibi)
- **Gerekçe:** KPSS'de anayasa, vergi kanunları ve idare hukuku zamanla değişir (örn: 2017 referandumu ile askeri yargının kaldırılması).
- **İşleyiş:** Her kanonik kayda `valid_from` ve `valid_until` tarih damgası eklenmeli; eski bilgi silinmek yerine "Mülga Mevzuat / Eski Sınav Çeldiricisi" olarak etiketlenmelidir.

---

## 2. HIGH VALUE (Yüksek Değerli Özellikler)

### 2.1 Adaptive Research & Active Learning (Uyarlanabilir Araştırma)
- **İşleyiş:** Ajan yalnızca rastgele veya sırayla video izlemek yerine, deneme sınavlarında sistemin zayıf kaldığı veya soru tahmin olasılığı en yüksek olan konuları `ConsciousnessEngine` üzerinden otomatik önceliklendirir.
- **Etki:** Bilgi ambarı kör noktalarını minimum kaynak tüketimiyle hızla kapatır.

### 2.2 Soru Kalıbı ve Çeldirici Öğrenme Motoru (Question Pattern Learning)
- **İşleyiş:** Çıkmış ÖSYM sorularını analiz ederek kök kalıplarını şablonlaştırır:
  - *"Hangisi X'in özelliklerinden biri değildir?"*
  - *"Yukarıdakilerden hangileri Y durumunda geçerlidir?"*
- Her şablon için doğru cevap mantığı ve çeldirici türleri (`TRAP_TYPES`) Knowledge Graph üzerinden otomatik ilişkilendirilir.

### 2.3 Cross-Source Reasoning & Expert-Level Synthesis (Çapraz Kaynak Sentezi)
- **İşleyiş:** Aynı konuyu anlatan 4 farklı hocanın (örn: Tarihte Ramazan Yetgin, Aydın Yüce, Mehmet Celal Özyıldız) ders anlatımlarını çapraz tablo haline getirerek:
  - Ortak anlatılan temel olgular (Core Knowledge)
  - Yalnızca bir hocanın bahsettiği ince ayrıntılar (Edge Cases)
  - Hocalar arasındaki nüans ve dil sürçmesi farkları
  tek bir sentez belgesinde özetlenir.

---

## 3. FUTURE (Gelecek Vizyonu Özellikleri)

### 3.1 Otonom KPSS Soru Üretim Motoru (Autonomous Question Generation Engine)
- Doğrulanmış kanonik gerçeklerden, Knowledge Graph'taki "OFTEN_CONFUSED_WITH" kavram ikililerinden ve `v15_traps` tuzak şablonlarından yararlanarak ÖSYM zorluk derecesinde %100 özgün KPSS soruları ve 5 seçenekli çeldiriciler üretir.

### 3.2 Dynamic Teacher Persona Emulation (Eğitmen Zihniyeti Simülasyonu)
- Öğrencinin seçtiği eğitmenin (örn: Ramazan Yetgin tarzı hikayeleştirme veya Celal Hoca tarzı şifreleme) pedagojik üslubuyla konuyu anlatan yapay zekâ öğretmen asistanı.

### 3.3 Evidence Ranking & Source Authority Matrix (Kanıt Ağırlıklandırma Matrisi)
- Kaynak türlerine göre hiyerarşik güven katsayısı:
  `Resmi Gazete / Mevzuat (1.0) > ÖSYM Çıkmış Soru (0.98) > Ders Kitabı/MEB (0.95) > YouTube Eğitmen Anlatımı (0.85)`.

---

## 4. EXPERIMENTAL (Deneysel / Araştırma Özellikleri)

### 4.1 Audio Pitch and Emphasis Detection (Ses Tonu ve Vurgu Analizi)
- Whisper transkripsiyonu sırasında eğitmenin ses perdesini (pitch) ve vurgu şiddetini analiz ederek hocanın heyecanlandığı veya "buraya dikkat edin" dediği anları otomatik zaman damgasıyla tespit etme.

### 4.2 Automated Visual Board OCR (Akıllı Tahta Görüntü Analizi)
- Video karelerinden eğitmenin tahtaya yazdığı şemaları, okları ve el yazılarını OCR (Vision LLM) ile okuyup transkriptle birleştirme.
