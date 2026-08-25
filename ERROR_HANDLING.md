# 🛡️ KPSS Super-Brain: Hata Yönetimi ve Dayanıklılık (ERROR_HANDLING.md)

Bu doküman, transkript çekim hataları, API rate limitleri, proxy rotasyonu, LLM bozuk JSON yanıtları ve worker kilitlerinin hata stratejilerini açıklar.

---

## 1. Hata Sınıflandırması ve Stratejiler

| Hata Türü | Kök Neden | Mühendislik Stratejisi | Son Durum |
|---|---|---|---|
| `TRANSCRIPT_UNAVAILABLE` | Video altyazısı ve sesi kapalı/engelli | Sahte veri koyma; videoyu açıkça `NO_TRANSCRIPT` yap | Video kuyruğunda işaretlenir, skor artırılmaz |
| `PROXY_429_RATE_LIMIT` | YouTube IP kısıtlaması | 10+ User-Agent ve Proxy rotasyonu işletilir | Yeni proxy ile otomatik tekrar denenir |
| `LLM_MALFORMED_JSON` | Model çıktısı bozuk JSON | Pydantic doğrulaması başarısız olur; kural tabanlı deterministik çıkarım devreye girer | Bozuk veri kaydedilmez |
| `Z3_LOGIC_UNSAT` | Anayasal sayılarda çelişki | Z3 SMT çözücü UNSAT döner; iddia anında reddedilir | `REJECTED` olarak işaretlenir |
| `WORKER_CRASH` | İş parçacığı beklenmedik durdu | `worker_coordinator` kilitleri serbest bırakır; zombi görevler kurtarılır | Görev güvenle yeniden kuyruğa alınır |

---

## 2. Sıfır Sessiz Hata İlkesi

Sistemde `except Exception: pass` blokları yasaklanmıştır. Her istisna:
1. İlgili `error_code` ve mesajıyla loglanır,
2. İlgili `research_events` veya `video_queue` tablosuna işlenir,
3. Üst katmana kesin hata durumu iletilir.
