# TRANSCRIPT PIPELINE CURRENT STATE & FORENSICS AUDIT

**Tarih:** 2026-08-27  
**Hedef:** YouTube Altyazı Hata Yolu (`TRANSCRIPT_UNAVAILABLE` ➔ `NO_TRANSCRIPT`) Adli İncelemesi  
**Kural:** Sıfır Davranış Değişikliği — Yalnızca Mevcut Kod İncelemesi ve Yol Haritası Dayanağı

---

## 1. Tespit Edilen Mevcut Hata & Belirtiler

Kullanıcı terminal çıktısında görülen hata:
```text
🕳️ [KARADELİK SAHA İŞÇİSİ] Görev Alındı: [COGRAFYA] Türkiye'nin İklimi, Sıcaklık, Basınç, Yağış ve Bitki Örtüsü
🎯 Hedef Hocalar: Bayram Meral, Engin Eraydın, Hakan Bileyen
🔎 Öncelikli Arama: 'KPSS Cografya Türkiye'nin İklimi, Sıcaklık, Basınç, Yağış ve Bitki Örtüsü konu anlatımı'    
  └─ 🌐 Keşif Tamamlandı: 1 adet aday video bulundu.
▶️ [VİDEO TÜKETİLİYOR] 412d8be232e — 'KPSS 2026 COGRAFYA - Türkiye'nin İklimi, Sıcaklık, Basınç, Yağış ve Bitki Örtüsü - Ali Can Demirci' (Ali Can Demirci)
  └─ ⚠️ Altyazı çekilemedi (TRANSCRIPT_UNAVAILABLE). NO_TRANSCRIPT olarak işaretleniyor.
```

### Kök Neden Analizi:
1. **Tekil Altyazı API Bağımlılığı**: `senses/transcript_fetcher.py` yalnızca `youtube_transcript_api` kütüphanesini doğrudan çağırmaktadır. YouTube IP tabanlı bot koruması (HTTP 429 / Sign-in required) devreye girdiğinde veya videoda manuel/otomatik altyazı bulunmadığında doğrudan `Exception` fırlatılmaktadır.
2. **Kör Düğüm (Hardcoded Fallback Disabling)**: `autonomous/harvester.py:195` satırında:
   ```python
   t_res = await transcript_fetcher.fetch_transcript_resilient(vid, enable_whisper_fallback=False)
   ```
   Whisper fallback'i `False` olarak kilitlenmiştir! Bu nedenle yerel Whisper motoru (`senses/whisper_transcriber.py`) hiçbir zaman devreye girememektedir.
3. **Monolitik Hata Çöküşü**: Hatanın nedeni (IP engeli, altyazı yokluğu, özel video vb.) ayrıştırılmadan tek bir `TRANSCRIPT_UNAVAILABLE` koduna indirgenmekte ve video kalıcı olarak `NO_TRANSCRIPT` statüsüne geçirilmektedir.
4. **Eksik Sağlayıcılar (Providers)**: Mimaride olması gereken `yt-dlp subtitles` ve `browser / Playwright caption extraction` sağlayıcıları kod tabanında mevcut değildir.

---

## 2. Mevcut Uçtan Uca Transkript ve Bilgi Akışı

```text
VideoTask (Curriculum / Harvester)
       ↓
senses/transcript_fetcher.py (fetch_transcript_resilient)
       ├─ [1] Disk Önbelleği (data/transcripts/<vid>_transcript.json)
       ├─ [2] Doğrudan YouTubeTranscriptApi.list(vid)
       ├─ [3] Proxy Pool Rotasyonu (Devre dışı veya sınırlı)
       └─ [4] Whisper Fallback (enable_whisper_fallback=False olduğu için ATLANIR)
       ↓
Sonuç: success = False, error = "TRANSCRIPT_UNAVAILABLE"
       ↓
autonomous/harvester.py:261
       └─ curriculum_queue.mark_no_transcript(vid, error_msg="TRANSCRIPT_UNAVAILABLE")
       ↓
curriculum/queue.py:244
       └─ UPDATE curriculum_videos SET status = 'NO_TRANSCRIPT'
```

---

## 3. Kod Tabanında Tespit Edilen "Sessiz Yutma" (Silent Swallowing) Noktaları

Section 10 & 12 gereği yapılan taramada şu kritik noktalar tespit edilmiştir:
- **`senses/transcript_processor.py:178`**:
  ```python
  try:
      async with httpx.AsyncClient(timeout=120.0) as client:
          res = await client.post(...)
          if res.status_code == 200:
              parsed_data = json.loads(res.json().get("response", "{}"))
  except Exception:
      pass  # <--- KRİTİK: LLM hatası sessizce yutuluyor ve parsed_data = {} kalıyor!
  ```
- **`senses/transcript_fetcher.py:114 & 133`**: Önbellek JSON/TXT okuma hataları `except Exception: pass` ile loglanmadan yutuluyor.
- **`senses/transcript_fetcher.py:259`**: Proxy denemesi `except Exception: pass` ile sessizce geçiştiriliyor.

---

## 4. İkinci Kritik Açık: Knowledge Firewall İhlali

`senses/transcript_processor.py` satır 218-234 incelendiğinde:
```python
atomic_claim = AtomicClaim(
    claim_id=claim_id,
    ...,
    verification_status=VerificationStatus.PENDING,
    tags=tags
)
cls._save_atomic_claim_to_db(atomic_claim)
extracted_claims.append(atomic_claim)

# DİKKAT: İddia henüz PENDING olmasına rağmen doğrudan kanonik ambarına ekleniyor:
knowledge_store.add_record(
    text=f_text,
    record_type="FACT",
    lesson=lesson,
    topic=topic,
    ...
)
```
Bu durum, `ANTIGRAVITY_TRANSCRIPT_FIX_MASTER_PROMPT.md` **Kural 13 (Knowledge Firewall)** prensibini doğrudan ihlal etmektedir:
> *CANDIDATE, PENDING, UNKNOWN, DISPUTED, REJECTED durumundaki hiçbir iddia doğrudan kanonik knowledge store'a giremez.*

---

## 5. Mevcut Veri Tabanı ve Durum Şeması

- **Tablo: `curriculum_videos` (`brain/database.py:130`)**:
  - `status TEXT NOT NULL DEFAULT 'PENDING'`: Desteklenen değerler: `PENDING`, `PROCESSING`, `WATCHED`, `NO_TRANSCRIPT`, `FAILED`, `DEAD_LETTER`.
- **Eksik Alanlar**:
  - `provider` (Hangi katmandan transkript alındı: CAPTIONS, YTDLP, BROWSER, WHISPER)
  - `attempt_count`
  - `last_error_code`
  - `last_error_message`
  - `next_retry_at`
  - `is_generated_transcript` (1 / 0)
- **Eksik Tablo**:
  - `transcript_provider_attempts` (Her denemenin başladığı, bittiği süre ve hata kodunun teşhis günlüğü).

---

## 6. Sonuç ve Eylem Kararı

Mevcut sistem tek bir altyazı çekme kütüphanesine bağımlıdır, Whisper katmanı çağrı seviyesinde devreden çıkarılmıştır ve hata izolasyonu yetersizdir. Çok katmanlı `TranscriptGateway` ve katı `Knowledge Firewall` yapısına geçiş zorunludur.
