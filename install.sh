#!/usr/bin/env bash
echo "==========================================================================="
echo "🧠 PROMIUS KPSS SUPER-BRAIN 2.0 - LINUX/MAC KURULUM SİHİRBAZI"
echo "==========================================================================="

# Python Kontrolü
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 bulunamadı! Lütfen Python 3.10+ yükleyin."
    exit 1
fi

# Pip Bağımlılıkları
echo "📦 Bağımlılıklar yükleniyor (requirements.txt)..."
pip3 install -r requirements.txt

# Ollama Modelleri
if command -v ollama &> /dev/null; then
    echo "🤖 Ollama modelleri çekiliyor..."
    ollama pull qwen2.5:14b
    ollama pull deepseek-r1:8b
fi

mkdir -p data/exports data/ground_truth outputs
chmod +x start.sh

echo "🎉 Kurulum tamamlandı! Başlatmak için: ./start.sh"
