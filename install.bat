@echo off
chcp 65001 >nul
title Promius KPSS Super-Brain Otomatik Kurulum
echo ===========================================================================
echo 🧠 PROMIUS KPSS SUPER-BRAIN 2.0 - OTOMATİK KURULUM VE HAZIRLIK SİHİRBAZI
echo ===========================================================================
echo.

:: 1. Python Kontrolü
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python bulunamadı! Lütfen Python 3.10 veya 3.11/3.12 yükleyin: https://www.python.org
    pause
    exit /b 1
)
echo ✅ Python tespit edildi.

:: 2. Pip ve Bağımlılıkların Kurulumu
echo 📦 Python kütüphaneleri yükleniyor (requirements.txt)...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ⚠️ Bazı paketler yüklenirken uyarı verdi, devam ediliyor...
) else (
    echo ✅ Tüm Python bağımlılıkları başarıyla yüklendi.
)

:: 3. Ollama Modellerini Çekme
echo.
echo 🤖 Ollama Yapay Zeka Modelleri Kontrol Ediliyor...
ollama --version >nul 2>&1
if %errorlevel% equ 0 (
    echo 📥 1/2: qwen2.5:14b modeli kontrol ediliyor...
    ollama pull qwen2.5:14b
    echo 📥 2/2: deepseek-r1:8b modeli kontrol ediliyor...
    ollama pull deepseek-r1:8b
    echo ✅ Modeller hazır!
) else (
    echo ⚠️ Ollama komutu bulunamadı. Lütfen Ollama'yı kurup modelleri çekin: https://ollama.ai
)

:: 4. Dizinlerin Oluşturulması
echo.
echo 📁 Veri ve çıktı dizinleri hazırlanıyor...
if not exist "data" mkdir data
if not exist "data\exports" mkdir data\exports
if not exist "data\ground_truth" mkdir data\ground_truth
if not exist "outputs" mkdir outputs

echo.
echo ===========================================================================
echo 🎉 KURULUM TAMAMLANDI!
echo 🚀 7/24 Açgözlü Motoru Başlatmak İçin : start_super_brain.bat
echo 🌐 Web Kontrol Panelini Açmak İçin    : start_web_ui.bat
echo ===========================================================================
pause
