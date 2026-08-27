"""
OpenManus Tool: Dosya Kaydedici (FileSaver)
Ajanın ürettiği notları, raporları ve analizleri yerel dosya sistemine kaydeder.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class FileSaver(BaseTool):
    """
    Metin içeriklerini belirtilen dosya yoluna kaydeden araç.
    """
    name: str = "file_saver"
    description: str = (
        "Verilen metin içeriğini yerel bir dosyaya kaydeder. "
        "Klasör mevcut değilse otomatik olarak oluşturur."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "(Gerekli) Kaydedilecek dosyanın tam veya göreceli dosya yolu."
            },
            "content": {
                "type": "string",
                "description": "(Gerekli) Dosyaya yazılacak metin içeriği."
            },
            "append": {
                "type": "boolean",
                "description": "(Opsiyonel) True ise dosyanın sonuna ekler, False ise üzerine yazar. Varsayılan False.",
                "default": False
            }
        },
        "required": ["file_path", "content"]
    }

    async def execute(self, file_path: str, content: str, append: bool = False) -> ToolResult:
        """
        Dosyayı asenkron veya güvenli bir şekilde yazar.
        """
        try:
            target = Path(file_path).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)

            mode = "a" if append else "w"
            with open(target, mode, encoding="utf-8") as f:
                f.write(content)

            msg = f"Dosya başarıyla kaydedildi: {target} ({len(content)} karakter, mod: {mode})"
            logger.info(msg)
            return ToolResult(output=msg)
        except Exception as e:
            err_msg = f"Dosya kaydetme hatası ({file_path}): {str(e)}"
            logger.error(err_msg)
            return ToolResult(error=err_msg)
