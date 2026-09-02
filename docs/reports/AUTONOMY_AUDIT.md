# KPSS Super-Brain — Otonomi ve Ajan Mimarisi Denetimi (AUTONOMY AUDIT)

> **Denetim Raporu:** Otonom döngüler, durum makinesi (FSM), bilinç motoru, OpenManus köprüsü ve öğretmen öğrenimi

---

## 1. Otonom Döngüler ve Orkestrasyon

### 1.1 HungryEngine (Doyumsuz Bilgi Motoru)
[autonomous/hungry_engine.py](file:///c:/Users/PC1/Desktop/promius/kpss-super-brain/autonomous/hungry_engine.py):
- 4 paralel döngü yönetir:
  1. `youtube_discovery_loop`: Müfredat eksikliklerine göre yeni video arama
  2. `synthesis_loop`: Çelişkileri çözme ve graf ilişkilerini kurma
  3. `self_eval_loop`: Bilgi ambarı olgunluğunu denetleme
  4. `task_worker_loop`: Araştırma görevlerini tüketme

### 1.2 ResearchAgent Stateful FSM (Sonlu Durum Makinesi)
[autonomous/research_agent.py](file:///c:/Users/PC1/Desktop/promius/kpss-super-brain/autonomous/research_agent.py):
Durum geçişleri SQLite `research_events` tablosunda adli olarak takip edilir:

```text
[GOAL_CREATED] ──► [PLANNING] ──► [DISCOVERING] ──► [ACQUIRING] ──► [VERIFYING]
                                                                        │
[COMPLETED] ◄── [GAP_ANALYSIS] ◄── [COMPARING] ◄────────────────────────┘
     ▲                │
     │                ▼
(Approved)   [RESEARCHING_GAPS] (Iteration < MAX_ITERATIONS)
                      │
                      ▼
[FAILED] ◄──── (Approved == False and Max Iterations Reached)
```

**Katı Kural (Hard Invariant):** `COMPLETED` durumu yalnızca ve yalnızca `CompletionEvaluator.approved == True` olduğunda verilebilir. Beklenmeyen bir hata durumunda durum daima `FAILED` olarak mühürlenir (sahte başarı raporlanamaz).

---

## 2. ConsciousnessEngine (Otonom Bilinç ve CoT)

[autonomous/consciousness.py](file:///c:/Users/PC1/Desktop/promius/kpss-super-brain/autonomous/consciousness.py):
Ajanın neden belirli bir konuyu seçtiğini üst-akıl deliberasyon (Chain of Thought) adımlarıyla gerekçelendirir:
1. Durum Bilinci: Mevcut doğrulanmış kayıt sayısı ve olgunluk skoru
2. Eksik Tespiti: En kritik kör nokta (örneğin 0 kayıtlı konu)
3. Pedagojik Tercih: Hedef hoca seçimi
4. Eylem Planı: Video çekimi veya kanonik mühürleme
Her karar `learning_events` epizodik hafızasına yazılır.

---

## 3. Kritik Soruların Değerlendirmesi

### Soru 2: OpenManus gerçekten araştırma worker'ı olarak kullanılıyor mu, yoksa yalnızca yüzeysel bir entegrasyon mu var?
**Cevap:** **YÜZEYSEL VE KONTROLLÜ BİR KÖPRÜDÜR (Tam Agentic Değil).**
- *Kod Kanıtı:* `openmanus_bridge/client.py L21-63` incelendiğinde:
  - `execute_research(task)` çağrıldığında OpenManus'un tam agentic tarayıcı (browser-use) ve sandbox terminal döngüsü çalıştırılmamaktadır.
  - Bunun yerine arka planda doğrudan `yt_dlp.YoutubeDL` ile sorgu aratılmakta ve sonuçlar `OpenManusResultParser` ile şemalandırılmaktadır.
  - *Gerekçe:* Kod docstring'inde "OpenManus Boundary Guard: OpenManus asla doğrudan veritabanına kanonik bilgi yazamaz" kuralı konulmuştur. Bu güvenlik açısından doğrudur, ancak OpenManus'un webde serbest araştırma yeteneği henüz tam otonom devreye alınmamıştır; kontrollü bir arama sağlayıcısı gibi çalışmaktadır.

### Soru 11: Öğretmenlerin gerçekten gözlemlenebilir anlatım örüntülerini öğreniyor mu?
**Cevap:** **EVET (Pedagojik Profilleme Aktif).**
- *Kod Kanıtı:* `cognition/teacher_learner.py` modülü izlenen her videodan sonra:
  - Öğretmenin sık kullandığı şifreleri (`mnemonics_used_json`)
  - En çok vurguladığı konuları (`favorite_topics_json`)
  - Soru tahmin geçmişini (`prediction_history_json`)
  - Kullandığı retorik/pedagojik üslubu (`strip_teacher_rhetoric` ile olgudan arındırarak)
  SQLite `teacher_profiles` tablosunda güncellemektedir.
