"""
KPSS Super-Brain: Merkezi Prompt Sanitizasyon ve Enjeksiyon Savunma Modülü (PromptSanitizer v1)
Dış kaynaklı YouTube altyazılarından, web sayfalarından veya PDF belgelerinden gelebilecek
Prompt Injection, Jailbreak, ChatML/Llama özel kontrol token'ları ve XML tag kaçışlarını nötralize eder.
"""
from __future__ import annotations

import re
import html
from typing import List, Tuple

# Özel LLM Kontrol ve Ayrıştırma Token'ları
SPECIAL_CONTROL_TOKENS: List[str] = [
    "<|im_start|>",
    "<|im_end|>",
    "<|endoftext|>",
    "<|fim_prefix|>",
    "<|fim_middle|>",
    "<|fim_suffix|>",
    "[INST]",
    "[/INST]",
    "<<SYS>>",
    "<</SYS>>",
    "<s>",
    "</s>",
    "<|begin_of_text|>",
    "<|end_of_text|>",
    "<|start_header_id|>",
    "<|end_header_id|>",
    "<|eot_id|>",
]

# Bilinen Doğrudan Sistem Manipülasyon ve Jailbreak Kalıpları
INJECTION_PATTERNS: List[Tuple[str, str]] = [
    (r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b", "[FILTERED_INSTRUCTION_OVERRIDE]"),
    (r"(?i)\bdisregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:rules|instructions|directives)\b", "[FILTERED_INSTRUCTION_OVERRIDE]"),
    (r"(?i)\byou\s+are\s+now\s+(?:in\s+)?(?:developer|jailbreak|dan|admin|god)\s+mode\b", "[FILTERED_PERSONA_OVERRIDE]"),
    (r"(?i)\bsystem\s+prompt\s*:\s*", "[FILTERED_SYSTEM_PROMPT] "),
    (r"(?i)\bnew\s+(?:system\s+)?rule\s*:\s*", "[FILTERED_NEW_RULE] "),
    (r"(?i)\bdo\s+not\s+follow\s+any\s+safety\s+(?:guidelines|rules)\b", "[FILTERED_SAFETY_OVERRIDE]"),
    (r"(?i)\badmin\s+override\s*:\s*", "[FILTERED_ADMIN_OVERRIDE] "),
    (r"(?i)\bbypass\s+(?:knowledge\s+firewall|verification|security)\b", "[FILTERED_BYPASS_ATTEMPT]"),
]

# XML/HTML Ayraç Kaçışını Engelleme Listesi
XML_TAG_ESCAPES: List[Tuple[str, str]] = [
    (r"</?raw_transcript[^>]*>", "[UNSAFE_TAG_REMOVED]"),
    (r"</?system[^>]*>", "[UNSAFE_TAG_REMOVED]"),
    (r"</?instruction[^>]*>", "[UNSAFE_TAG_REMOVED]"),
    (r"</?context[^>]*>", "[UNSAFE_TAG_REMOVED]"),
]


def sanitize_transcript(text: str, max_length: int = 15000) -> str:
    """
    Ham transkript veya harici metin içeriğini temizler ve güvenli hale getirir:
    1. Özel LLM kontrol token'larını temizler.
    2. Prompt injection / jailbreak girişimlerini nötralize eder.
    3. XML ayraç kaçışlarını etkisiz hale getirir.
    4. Kontrol karakterlerini temizler, ancak Türkçe karakterleri ve biçimlendirmeyi korur.
    """
    if not text or not isinstance(text, str):
        return ""

    sanitized = text

    # 1. Özel LLM Token Temizliği
    for token in SPECIAL_CONTROL_TOKENS:
        if token in sanitized:
            sanitized = sanitized.replace(token, " ")

    # 2. XML / Tag Kaçış Nötralizasyonu
    for pattern, replacement in XML_TAG_ESCAPES:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    # 3. Prompt Injection Kalıpları
    for pattern, replacement in INJECTION_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)

    # 4. Tehlikeli Olmayan Normalizasyon (Görünmez kontrol karakterlerini temizle)
    # \r, \n, \t dışındaki kontrol karakterlerini kaldır
    sanitized = "".join(ch for ch in sanitized if ch in ("\n", "\r", "\t") or (ord(ch) >= 32 and ord(ch) != 127))

    # 5. Uzunluk Sınırı (DoS / Bellek Taşması Koruması)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


def wrap_untrusted_input(sanitized_text: str, tag_name: str = "raw_transcript") -> str:
    """
    Temizlenmiş harici metni LLM'in güvenilmeyen veri olarak ayrıştırabileceği
    açık XML etiket sınırları içine sarar.
    """
    safe_content = sanitized_text.replace(f"<{tag_name}>", "").replace(f"</{tag_name}>", "")
    return f"<{tag_name}>\n{safe_content}\n</{tag_name}>"
