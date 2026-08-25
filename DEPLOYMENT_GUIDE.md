# 🏛️ Promius KPSS Super-Brain v4 — Başka PC'ye Kurulum ve 7/24 Çalıştırma Kılavuzu

Bu belge, **Promius KPSS Super-Brain** otonom yapay zeka öğretmen sistemini sürekli açık kalacak başka bir bilgisayara (Windows PC, Laptop veya Linux/Ubuntu Sunucu) taşımak, kurmak ve 7/24 kesintisiz çalıştırmak için hazırlanmış eksiksiz rehberdir.

---

## 💻 1. Minimum & Önerilen Donanım Gereksinimleri

| Bileşen | Minimum Gereksinim | Önerilen (İdeal Performans) |
|---|---|---|
| **İşletim Sistemi** | Windows 10/11 (64-bit) veya Ubuntu 22.04+ | Windows 11 / Ubuntu 22.04 LTS |
| **İşlemci (CPU)** | 4 Çekirdek (Intel i5/Ryzen 5) | 8+ Çekirdek (Intel i7/Ryzen 7) |
| **Bellek (RAM)** | 16 GB RAM | 32 GB RAM |
| **Ekran Kartı (GPU)** | CPU üzerinde çalışabilir (yavaş) | NVIDIA RTX 3060 / 4060 (8GB+ VRAM) |
| **Depolama** | 20 GB Boş SSD Alanı | 50 GB NVMe SSD |

---

## 📦 2. Adım Adım Kurulum Kılavuzu

### 1. Adım: Projeyi Diğer Bilgisayara Taşıyın
`kpss-super-brain` klasörünün tamamını bir USB belleğe, harici diske veya Google Drive'a kopyalayın ve hedef bilgisayara yapıştırın:
* **Örnek Hedef Dizin (Windows):** `C:\promius\kpss-super-brain`
* **Örnek Hedef Dizin (Linux):** `/home/ubuntu/kpss-super-brain`

---

### 2. Adım: Hedef Bilgisayara Temel Araçları Yükleyin

1. **Python 3.10, 3.11 veya 3.12** yükleyin:
   * Windows için indirin: [https://www.python.org/downloads/](https://www.python.org/downloads/)
   * ⚠️ **ÖNEMLİ:** Kurulum esnasında alttaki **`Add Python to PATH`** kutucuğunu mutlaka işaretleyin!

2. **Ollama (Yerel Yapay Zeka Motoru)** yükleyin:
   * Windows / Mac / Linux için indirin: [https://ollama.ai/download](https://ollama.ai/download)
   * Kurulum tamamlandıktan sonra Ollama arka planda otomatik çalışacaktır.

---

### 3. Adım: Tek Tıkla Otomatik Kurulumu Çalıştırın

#### 🪟 Windows İçin:
1. `kpss-super-brain` klasörünü açın.
2. **`install.bat`** dosyasına çift tıklayın.
3. Sihirbaz sırasıyla şunları yapacaktır:
   - Tüm Python kütüphanelerini (`requirements.txt`) otomatik yükler.
   - Ollama modellerini (`qwen2.5:14b` ve `deepseek-r1:8b`) otomatik olarak indirir.
   - Gerekli tüm veri ve ambar klasörlerini hazırlar.

#### 🐧 Linux / Ubuntu Sunucu İçin:
Terminali açıp şu komutları çalıştırın:
```bash
cd /home/ubuntu/kpss-super-brain
chmod +x install.sh start.sh
./install.sh
```

---

## 🚀 3. Sistemi 7/24 Kesintisiz Başlatma Yöntemleri

### Yöntem 1: Tek Tıkla Masaüstü Başlatıcı (En Pratik)
* **7/24 Açgözlü Öğrenme Motoru:** Klasördeki **`start_super_brain.bat`** dosyasına çift tıklayın.
* **Web Kontrol Paneli:** Klasördeki **`start_web_ui.bat`** dosyasına çift tıklayın (Tarayıcınızda `http://127.0.0.1:8500` açılacaktır).

---

### Yöntem 2: Windows Açılışında Otomatik Başlatma (Elektrik Gelse Bile Devam)
Bilgisayar yeniden başladığında veya elektrik kesilip geldiğinde yapay zekanın kendi kendine açılması için:
1. Klavyeden **`Win + R`** tuşlarına basın.
2. Açılan pencereye **`shell:startup`** yazıp `Enter`'a basın (Başlangıç klasörü açılır).
3. `kpss-super-brain` klasöründeki **`start_super_brain.bat`** dosyasının **Kısayolunu** oluşturup bu Başlangıç klasörünün içine yapıştırın.
4. 🎉 Artık bilgisayar her açıldığında süper zeka arka planda kaldığı yerden öğrenmeye devam edecektir.

---

### Yöntem 3: Linux / Ubuntu Systemd Servisi (Profesyonel Sunucu)
`/etc/systemd/system/superbrain.service` dosyası oluşturun:
```ini
[Unit]
Description=Promius KPSS Super-Brain 7/24 Engine
After=network.target

[Service]
User=root
WorkingDirectory=/home/ubuntu/kpss-super-brain
ExecStart=/usr/bin/python3 main.py --hungry
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Servisi etkinleştirin ve başlatın:
```bash
sudo systemctl daemon-reload
sudo systemctl enable superbrain
sudo systemctl start superbrain
```

---

## 📊 4. Yapay Zeka Son Çıktılarını Uygulamanızda Nasıl Kullanacaksınız?

Sistem çalıştıkça `outputs/` ve `data/exports/` dizinlerine doğrulanmış verileri otomatik doldurur:

### 1. Hazır JSON Dosyaları (`outputs/` Dizini)
| Dosya | İçerik ve Format | Uygulamada Nasıl Kullanılır? |
|---|---|---|
| `outputs/exam_questions.json` | 5 Şıklı, Çözümlü, Hakem Onaylı Sorular | Mobil uygulamanızda **"Günün Denemesi"**, Soru Bankası |
| `outputs/daily_facts.json` | MEB & Resmi Gazete Hap Bilgileri | Mobil uygulamanızda **"Flashcards (Hafıza Kartları)"** |
| `outputs/mnemonics.json` | Eğitmen Hafıza Şifreleri (TAYYAR, KADER vb.) | Mobil uygulamanızda **"Şifreli Konu Notları"** |
| `outputs/latest_summary.md` | Canlı Zeka Raporu ve Olgunluk Skoru | Admin Paneli / Discord / Telegram Günlük Raporu |

### 2. Canlı REST API Entegrasyonu
Diğer bilgisayarınızın yerel IP adresini kullanarak kendi uygulamanızdan canlı istek atabilirsiniz:
* **Canlı Hakemli Soru Üret:** `POST http://<IP>:8500/api/professor/generate-question`
* **Doğrulanmış Bilgi Ambarını Çek:** `GET http://<IP>:8500/api/knowledge/records?lesson=VATANDASLIK`
* **Anlık Bilinç ve Karar Durumunu Çek:** `GET http://<IP>:8500/api/consciousness`

---

## 🛡️ Sıkça Sorulan Sorular ve Sorun Giderme

1. **Bilgisayar kapanırsa ne olur?**
   - Sistem SQLite tabanlı `StatePersistence` mimarisine sahiptir. Tekrar açıldığında hangi videoda ve hangi konuda kaldıysa **sıfır kayıpla tam oradan devam eder**.
2. **YouTube IP engeli yer mi?**
   - Hayır. Sistem `ProxyPool` rotasyonu ve yerel GPU Whisper STT (ses indirme) katmanlarıyla donatılmıştır; engellere takılmadan 7/24 çalışır.
3. **Halüsinasyon / yanlış bilgi üretir mi?**
   - 9 katmanlı kalkan (Mülga kanun, Z3 mantık çözücü, tarihsel anakronizm vb.) sayesinde şüpheli her bilgi anında imha edilir, sadece %100 doğrulanmış veriler çıktılara yansır.
