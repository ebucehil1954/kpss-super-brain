"""
KPSS Super-Brain: Karşıt Hakem Soru Denetçisi (Adversarial Referee Solver - Fail-Safe Double Blind)
Soru üretildikten sonra 2. bağımsız akıl yürütme modeli (DeepSeek-R1 / Qwen2.5) soruyu körlemesine çözer.
Kesin kural: Hakem ve yazar şıkkı uyuşmazsa veya hakem çözemezse soru KESİNLİKLE REDDEDİLİR.
"""
import re
import json
import httpx
from typing import Tuple, Dict, Any, Optional
from config import super_brain_config

class AdversarialRefereeSolver:
    @classmethod
    async def audit_generated_question(cls, question_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Sorunun sadece ve kesinlikle 1 doğru cevabı olduğunu ve çelişki barındırmadığını test eder.
        Fail-Safe İlkesi: Herhangi bir hata veya uyuşmazlık durumunda ASLA onay vermez.
        """
        stem = question_data.get("stem", "")
        options = question_data.get("options", {})
        expected = str(question_data.get("expected_answer", "")).strip().upper()
        
        if not stem or not options or len(options) < 4 or not expected:
            return False, "Eksik soru verisi (Kök, seçenekler veya beklenen cevap eksik)."

        options_text = "\n".join([f"{k}) {v}" for k, v in sorted(options.items())])
        
        prompt = f"""
Sen ÖSYM KPSS Soru İnceleme ve Hakem Heyeti Başkanısın.
GÖREV: Aşağıdaki KPSS sorusunu tamamen bağımsız olarak, sıfırdan adım adım çöz ve YALNIZCA TEK BİR DOĞRU CEVAP ŞIKKI belirle.

DİKKAT:
- Eğer soru hatalıysa, birden fazla doğru cevap varsa veya hiçbir şık doğru değilse "HATALI_SORU" olarak belirt.
- 2017 Anayasa Değişikliği öncesi mülga terimler (Başbakan, Tüzük, Gensoru vb.) veya sahte kanun isimleri varsa soruyu reddet.

SORU METNİ:
{stem}

SEÇENEKLER:
{options_text}

CEVAP FORMATI (SADECE AŞAĞIDAKİ GİBİ DÖNDÜR):
DOĞRU CEVAP: [A, B, C, D veya E]
GEREKÇE: [Adım adım çözüm ve diğer şıkların elenme sebebi]
"""
        
        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                model_to_use = super_brain_config.REASONING_MODEL or super_brain_config.MAIN_MODEL
                
                res = await client.post(
                    f"{super_brain_config.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": model_to_use,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.0}
                    }
                )
                
                # Eğer reasoning modeli timeout/hata verirse main model'e fallback
                if res.status_code != 200 and model_to_use != super_brain_config.MAIN_MODEL:
                    res = await client.post(
                        f"{super_brain_config.OLLAMA_BASE_URL}/api/generate",
                        json={
                            "model": super_brain_config.MAIN_MODEL,
                            "prompt": prompt,
                            "stream": False,
                            "options": {"temperature": 0.0}
                        }
                    )
                
                if res.status_code == 200:
                    output = res.json().get("response", "")
                    
                    # Hatalı soru tespiti
                    if "HATALI_SORU" in output.upper() or "ÇELİŞKİ" in output.upper():
                        return False, f"Hakem Heyeti Soruyu Kusurlu/Çelişkili Buldu: {output[:150]}"
                    
                    match = re.search(r"DOĞRU CEVAP:\s*\[?([A-E])\]?", output, re.IGNORECASE)
                    if not match:
                        match = re.search(r"\b([A-E])\s*(?:şıkkı|seçeneği|doğrudur)", output, re.IGNORECASE)
                    
                    if not match:
                        return False, "Hakem Heyeti net bir şık seçemedi (Belirsiz Soru)."
                    
                    referee_answer = match.group(1).upper()
                    
                    if referee_answer == expected:
                        return True, f"Hakem Onayı Başarılı: Çift Kör Doğrulama ile Doğru Cevap [{expected}] Olarak Teyit Edildi."
                    else:
                        return False, f"Şık Uyuşmazlığı: Yazar [{expected}] öngördü, Hakem [{referee_answer}] buldu."
                else:
                    return False, f"Hakem model yanıt veremedi (HTTP {res.status_code}). Fail-Safe gereği reddedildi."
        except Exception as e:
            # FAIL-SAFE: Hata durumunda ASLA onay verilmez!
            return False, f"Hakem Heyeti denetimi sırasında hata oluştu ({str(e)}). Soru güvenlik gereği elendi."

adversarial_solver = AdversarialRefereeSolver()
