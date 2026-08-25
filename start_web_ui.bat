@echo off
chcp 65001 >nul
title Promius KPSS Super-Brain Web UI (Port 8500)
cd /d %~dp0
echo ===========================================================================
echo 🌐 PROMIUS KPSS SUPER-BRAIN WEB KONTROL PANELİ BAŞLATILIYOR
echo ===========================================================================
echo 📍 Adres: http://127.0.0.1:8500
echo.
start http://127.0.0.1:8500
python main.py --web --port 8500
pause
