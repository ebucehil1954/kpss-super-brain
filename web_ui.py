"""
Promius KPSS Super-Brain: Güvenli Web Kontrol ve Gözlem Merkezi (FastAPI + Jinja2 Templates)
Statik HTML string yerine XSS korumalı Jinja2 auto-escaping şablon motoru kullanır.

Çalıştırmak için: python web_ui.py
Erişim: http://127.0.0.1:8000 (veya http://127.0.0.1:8500)
"""
import os
import sys
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("KPSS_SUPER_BRAIN")

from config import super_brain_config
from api.server import app

# Jinja2 Şablon Dizini Yapılandırması (Auto-escaping varsayılan olarak aktiftir)
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
async def serve_control_panel(request: Request):
    """
    Güvenli Jinja2 şablonu ile Mission Control panelini render eder.
    Tüm dinamik değerler Jinja2 tarafından otomatik olarak escape edilir.
    """
    context = {
        "request": request,
        "title": "Promius KPSS Super-Brain",
        "app_name": "PROMIUS KPSS SUPER-BRAIN",
        "default_confidence": "95.0",
        "min_sources": "8-10"
    }
    return templates.TemplateResponse("index.html", context)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🌐 [WEB UI] FastAPI + Jinja2 Güvenli Arayüz başlatılıyor: http://127.0.0.1:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
