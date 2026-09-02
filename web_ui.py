"""
Promius KPSS Super-Brain: Güvenli Web Kontrol ve Gözlem Merkezi (FastAPI + Jinja2 Templates)
Statik HTML string yerine XSS korumalı Jinja2 auto-escaping şablon motoru kullanır.

Çalıştırmak için: python web_ui.py
Erişim: http://127.0.0.1:8500
"""
import os
import uvicorn

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("KPSS_SUPER_BRAIN")

from config import super_brain_config
from api.server import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8500))
    logger.info(f"🌐 [WEB UI] FastAPI Web Arayüzü başlatılıyor: http://127.0.0.1:{port}")
    uvicorn.run("api.server:app", host="0.0.0.0", port=port, log_level="info")
