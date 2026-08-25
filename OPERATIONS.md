# ⚙️ KPSS Super-Brain: Operasyon ve Çalıştırma Rehberi (OPERATIONS.md)

Bu doküman, sistemin yerel ortamda veya sunucuda nasıl çalıştırılacağını, izleneceğini ve yönetileceğini açıklar.

---

## 1. Gereksinimler ve Kurulum

- Python 3.10+ (veya 3.14)
- Ollama (Yerel LLM servisi: `http://localhost:11434`)
- Bağımlılıklar:
  ```powershell
  pip install -r requirements.txt
  ```

---

## 2. Sistemi Başlatma

### A. Otonom Araştırma ve Açgözlü Sindirme Motoru (Hungry Engine)
```powershell
python main.py
```
- YouTube keşif radarını, transkript işçilerini, durum denetleyicilerini ve checkpoint döngüsünü başlatır.

### B. İnteraktif Web Kontrol Paneli (Web UI)
```powershell
python web_ui.py
# veya
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```
- Tarayıcıdan `http://localhost:8000` adresine girerek konu hakimiyet matrisini, video kuyruğunu, çelişki raporlarını ve profesör ders notlarını inceleyebilirsiniz.

---

## 3. Sağlık ve Doğrulama Komutları

```powershell
# Hızlı Sistem Sağlık Kontrolü
python test_system.py

# Kapsamlı Test Paketi
python -m pytest tests/
```
