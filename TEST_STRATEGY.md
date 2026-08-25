# 🧪 KPSS Super-Brain: Test Stratejisi (TEST_STRATEGY.md)

Bu doküman, sistemin doğruluğunu, halüsinasyon engelleme gücünü, provenance izlenebilirliğini ve deterministik hesaplamalarını güvence altına alan test mimarisini belgeler.

---

## 1. Test Paketleri ve Kapsam

### 1. `tests/test_agentic_research_and_integrity.py` (6 Test)
- **Test 1**: Transkript Başarısızlığı ve Sahte Veri İzolasyonu.
- **Test 2**: Provenance ve Segment Zaman Damgası Bütünlüğü.
- **Test 3**: Tip Güvenli ToolRegistry ve Timeout Kalkanı.
- **Test 4**: Çelişki Çözüm Motoru ve Resmî Kaynak Üstünlüğü (`OFFICIAL_SOURCE_WINS`).
- **Test 5**: Stateful Research Agent Durum Makinesi ve Olay Günlüğü.
- **Test 6**: Çok Faktörlü Deterministik Hakimiyet Hesaplama.

### 2. `tests/test_super_brain_v2.py` (7 Test)
- OpenManus ReAct otonom arama döngüsü ve 2+ kaynak doğrulaması.
- RefChecker & Z3 SMT AYM 11 üye sayısı halüsinasyonunu anında yakalama.
- SelfCheckGPT çelişki skoru $< 0.85$ engellemesi.
- HungryEngine otonom tetikleme ve müfredat yükseltme.
- Derin ontoloji ve düğüm genişletme.
- Checkpoint ve state kurtarma.
- Worker kilit ve çakışma engelleme.

### 3. `tests/test_curriculum_mastery_and_discovery.py` (5 Test)
- 52 resmi ÖSYM konusunun 3-4 video gereksinimi.
- Çoklu hoca izleme matrisi.
- Çapraz hoca uzman sentezi.
- Manus radar keşfi.
- Temiz JSON ihracatları.

### 4. `tests/test_super_brain.py` (11 Test)
- Z3 formal sözel mantık kısıt çözücüsü.
- RefChecker ve 9 kademeli kalkan.
- SQLite WAL oturumu ve FTS5 araması.

---

## 2. Testleri Çalıştırma

```powershell
python -m pytest tests/
```
Tüm testler %100 başarıyla (29/29 Passed) tamamlanmalıdır.
