# ⚙️ KPSS Super-Brain: Operasyon ve Çalıştırma Rehberi (OPERATIONS.md)

Bu doküman, KPSS Super-Brain sisteminin kurulum, ortam yapılandırması (.env) ve çalıştırma adımlarını içerir.

---

## 1. Kurulum (Installation)

1. **Python 3.11** veya üzeri bir Python sürümünün kurulu olduğundan emin olun.
2. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
3. Yerel Ollama LLM servisini başlatın ve gerekli modelleri çekin:
   ```bash
   ollama serve
   ollama pull qwen2.5:7b
   ollama pull all-minilm
   ```

---

## 2. Ortam Değişkenleri (.env)

Proje kök dizininde `.env` dosyası oluşturun (veya varsayılan değerleri kullanın):

```env
# Ollama Yerel LLM Bağlantısı
OLLAMA_BASE_URL=http://127.0.0.1:11434
SUPER_BRAIN_MAIN_MODEL=qwen2.5:7b
SUPER_BRAIN_EMBEDDING_MODEL=all-minilm

# Veritabanı ve Çalışma Ayarları
DATABASE_URL=sqlite:///data/brain.db
LOG_LEVEL=INFO

# YouTube ve STT Ayarları (Opsiyonel)
WHISPER_ENABLED=true
WHISPER_DEVICE=auto
```

---

## 3. Çalıştırma Adımları (Execution)

### A. Ana Otonom Araştırma Motoru
```bash
python main.py
```
- YouTube keşif radarını, transkript işleme hattını ve otonom araştırma döngüsünü başlatır.

### B. 7/24 Açgözlü Öğrenme Süreci (Daemon)
```bash
python daemon.py
```
- Arka planda kesintisiz video sindirme ve müfredat hakimiyeti tamamlama sürecini çalıştırır (`CTRL+C` ile veri kaybı olmadan güvenle kapanır).

### C. Web Kontrol Paneli (Web UI)
```bash
python web_ui.py
```
- `http://localhost:8000` adresinden canlı müfredat matrisini, çelişki analizlerini ve soru tahminlerini görselleştirir.

---

## 4. Test ve Bütünlük Doğrulama

```bash
# Tüm birim ve entegrasyon testlerini çalıştırma
python -m pytest tests/ -q

# Kod derleme ve sözdizimi denetimi
python -m compileall .
```
