# KPSS Super-Brain — YouTube ve Transkript Altyapısı Denetimi (YOUTUBE & TRANSCRIPT AUDIT)

> **Denetim Raporu:** YouTube keşif pipeline'ı, transkript altyazı motoru, fallback sırası, Circuit Breaker ve adli provenance mühürleme

---

## 1. YouTube Keşif Hattı (Discovery Pipeline)

### 1.1 Arama ve Kuyruğa Alma Aşamaları
1. **OpenManus Araştırma Köprüsü:** `harvester.py` L58-85 önce `openmanus_bridge_client.execute_research(task)` üzerinden yapılandırılmış arama çalıştırır.
2. **Resmi YouTube Data API v3:** `youtube_api_client.py` tanımlıysa ve kota varsa resmi API kullanılır (IP engelsiz, hızlı).
3. **yt-dlp Fallback:** API yoksa veya sonuç boşsa `yt_dlp` headless arama modunda devreye girer.
4. **ChannelScanner Doğrulaması:** Videonun hedef hocaya veya onaylı kanallara ait olup olmadığı `channel_scanner.verify_channel_identity()` ile süzülür.

### 1.2 Kuyruk ve Mükerrer Kontrolü (Deduplication)
- `curriculum_queue.enqueue_video(video_data, strict_validation=True)`:
  - 11 haneli video_id regex kontrolü (`^[a-zA-Z0-9_-]{11}$`)
  - Daha önce izlenmiş veya kuyrukta olan videoların mükerrer kaydını engelleme
  - Yanlış veya sahte URL formatlarını reddetme (`test_phase1_fake_youtube_ids.py` ile doğrulanmıştır)

---

## 2. TranscriptGateway ve 4 Kademeli Fallback

[transcript_gateway.py](file:///c:/Users/PC1/Desktop/promius/kpss-super-brain/senses/transcript_gateway.py) mimarisi adli standartlara uygun olarak tasarlanmıştır:

```text
[Video ID]
    │
    ├─► [0. Disk Cache]: {_video_id}_transcript.json (Önbellek varsa anında döner)
    │
    ├─► [1. YouTubeCaptionProvider]: youtube_transcript_api (Resmi ve otomatik altyazı)
    │     └─ Hata? Circuit Breaker Failure +1 -> Kademeye 2 geç
    │
    ├─► [2. YtDlpSubtitleProvider]: yt-dlp VTT/SRT altyazı akışı
    │     └─ Hata? Circuit Breaker Failure +1 -> Kademeye 3 geç
    │
    ├─► [3. BrowserTranscriptProvider]: Headless Browser sayfa kazıma / Player Response
    │     └─ Hata? Circuit Breaker Failure +1 -> Kademeye 4 geç
    │
    └─► [4. WhisperProvider]: Yalnızca ses akışı indirme + Yerel Whisper STT
          └─ Hata? -> TRANSCRIPT_DEFERRED (Kuyruk kilitlenmez, video ertelenir)
```

### 2.1 Circuit Breaker (Devre Kesici) Performansı
- **Eşik:** 3 ardışık hata
- **Bekleme Süresi (Cooldown):** 120 saniye
- **Hızlı Tetikleme (Trip Breaker):** `HTTP 429 Too Many Requests` veya bot tespiti durumunda 3 hatayı beklemeden devre derhal `OPEN` durumuna alınır.
- **Değerlendirme:** Harici IP engellerinin tüm sistemi kitlemesini önleyen son derece olgun bir kalıptır.

---

## 3. Zaman Damgası ve Segment Mühürleme (Provenance Linkage)

[transcript_fetcher.py L41-80](file:///c:/Users/PC1/Desktop/promius/kpss-super-brain/senses/transcript_fetcher.py#L41-L80):
- Her transkript kelime kelime segmentlere bölünür:
  - `segment_id = f"seg_{video_id}_{idx}"`
  - `start_seconds`, `end_seconds`
  - `segment_hash = hashlib.sha256(f"{video_id}:{start}:{end}:{text}".encode()).hexdigest()[:16]`
- Segmentler doğrudan SQLite `transcript_segments` tablosuna mühürlenir.
- Bir iddia çıkarıldığında (`TranscriptProcessor L211`), iddia metni transkript segmentleriyle fuzzy ve kelime bazlı eşleştirilerek gerçek `segment_id` ve `timestamp_str` (örn: `14:20 - 14:55`) kanıt referansına bağlanır.

---

## 4. Kritik Soruların Değerlendirmesi

### Soru 8: YouTube verilerinde sahte ID, URL, transcript veya provenance üretme ihtimali var mı?
**Cevap:** **HAYIR (Güvenlik Önlemleri Tam).**
- *Kanıt 1:* `TranscriptFetcher.extract_video_id` 11 haneli katı regex uygular.
- *Kanıt 2:* Boş veya 50 karakterden kısa transkriptler asla önbelleğe veya veritabanına yazılmaz (`TRANSCRIPT_UNAVAILABLE` döner).
- *Kanıt 3:* `ProvenanceValidator` segment ve video eşleşmesini zorunlu kılar.

### Soru 7: Tek bir video, transcript veya network hatası bütün sistemi durdurabilir mi?
**Cevap:** **HAYIR.**
- *Kanıt:* `harvester.py L295-308` tüm video işleme sürecini izole etmiştir. Bir videoda ağ kesilirse veya altyazı bulunamazsa video `TRANSCRIPT_FAILED_TEMPORARY` olarak işaretlenir, sayaç artırılır ve bir sonraki videoya geçilir. Worker çökmez.
