"""
OpenManus Tool: Semantik ve Sayısal Çelişki Tespit Aracı (Contradiction Checker)
İki metin arasındaki anlamsal ve sayısal çelişkileri üç aşamada test eder:
1. Z3 SMT Formal Logic Çözücü (Sayısal kural regex tespiti, 500ms timeout)
2. Sentence-Transformers (all-MiniLM-L6-v2) Vektör Benzerliği (> 0.75 eşiği)
3. Ollama qwen2.5:14b LLM Hakemi ("Bu iki cümle çelişiyor mu? Sadece EVET veya HAYIR de.")
"""
from __future__ import annotations

import re
import json
from typing import Dict, Any, Optional, Tuple
import numpy as np

from app.logger import logger
from app.tool.base import BaseTool, ToolResult

# SentenceTransformer Modeli için Global Cache
_EMBED_MODEL = None


def _get_embed_model():
    """SentenceTransformer modelini singleton olarak yükler."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBED_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            logger.info("SentenceTransformer (all-MiniLM-L6-v2) başarıyla yüklendi.")
        except Exception as e:
            logger.error(f"SentenceTransformer yüklenirken hata oluştu: {e}")
            _EMBED_MODEL = False
    return _EMBED_MODEL if _EMBED_MODEL is not False else None


class ContradictionCheckerTool(BaseTool):
    """
    İki KPSS konu anlatımı veya iddia ifadesi arasındaki çelişkiyi denetleyen araç.
    """
    name: str = "contradiction_checker"
    description: str = (
        "İki metin arasındaki sayısal veya semantik çelişkileri tespit eder. "
        "Sayısal değerlerde Z3 SMT çözücüsünü (500ms timeout), semantik benzerlik 0.75'in "
        "üzerinde olduğunda Ollama qwen2.5:14b LLM hakemini kullanır."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "text1": {
                "type": "string",
                "description": "(Gerekli) Karşılaştırılacak 1. kaynak veya iddia metni."
            },
            "text2": {
                "type": "string",
                "description": "(Gerekli) Karşılaştırılacak 2. kaynak veya iddia metni."
            }
        },
        "required": ["text1", "text2"]
    }

    def _extract_numerical_predicate(self, text: str) -> Optional[Tuple[str, int]]:
        """
        Metin içerisindeki sayısal mevzuat/tarih kuralını ve sayı değerini regex ile tespit eder.
        """
        t = text.lower()
        rules = [
            (r"(?:anayasa mahkemesi|aym)\s*(?:üye sayısı|üyeleri|toplam üye)", "aym_uye_sayisi"),
            (r"(?:anayasa mahkemesi|aym)\s*(?:görev süresi|üyelerinin süresi)", "aym_gorev_suresi"),
            (r"(?:anayasa mahkemesi|aym)\s*(?:seçilme yaşı|yaş sınırı)", "aym_secilme_yasi"),
            (r"(?:anayasa mahkemesi|aym)\s*(?:emeklilik yaşı)", "aym_emeklilik_yasi"),
            (r"(?:tbmm|meclis|milletvekili)\s*(?:üye sayısı|toplam üye|sandalye|milletvekili sayısı)", "tbmm_uye_sayisi"),
            (r"(?:toplantı yeter|toplantı yeter sayısı)", "toplanti_yeter_sayisi"),
            (r"(?:karar yeter|karar yeter sayısı)", "karar_yeter_sayisi"),
            (r"(?:genel af|özel af|af ilanı)\s*(?:çoğunluğu|için üye)", "af_yeter_sayisi"),
            (r"(?:milletvekili|milletvekilliği)\s*(?:seçilme yaşı|yaşı)", "mv_secilme_yasi"),
            (r"(?:cumhurbaşkanı|cb)\s*(?:seçilme yaşı|yaşı)", "cb_secilme_yasi"),
            (r"(?:cumhurbaşkanı|cb)\s*(?:görev süresi)", "cb_gorev_suresi"),
            (r"(?:cumhurbaşkanı|cb)\s*(?:dönem sınırı|kez seçilebilir)", "cb_donem_siniri"),
            (r"(?:hsk|hâkimler ve savcılar)\s*(?:üye sayısı|üyeleri)", "hsk_uye_sayisi"),
            (r"(?:hsk|hâkimler ve savcılar)\s*(?:daire sayısı)", "hsk_daire_sayisi"),
            (r"(?:danıştay)\s*(?:daire sayısı)", "danistay_daire_sayisi"),
            (r"(?:yargıtay)\s*(?:daire sayısı)", "yargitay_daire_sayisi"),
            (r"(?:seçim dönemi|seçimler kaç yılda)", "secim_donemi")
        ]

        for pattern, pred_key in rules:
            if re.search(pattern, t):
                numbers = re.findall(r"\b\d+\b", t)
                if numbers:
                    return pred_key, int(numbers[0])

        # Genel sayısal eşleşme: Sayı geçiyorsa ve ortak kelimeler varsa
        numbers = re.findall(r"\b\d+\b", t)
        if numbers:
            words = [w for w in re.findall(r"\b[a-zçğıöşü]{4,}\b", t)]
            if words:
                key = "_".join(words[:2])
                return key, int(numbers[0])

        return None

    def _check_z3_contradiction(self, text1: str, text2: str) -> Optional[Dict[str, Any]]:
        """
        Metinlerde sayısal değerler geçtiğinde Z3 SMT Solver ile 500ms timeout sınırında
        biçimsel matematiksel çelişkiyi (UNSAT) denetler.
        """
        # Her iki metinde de sayısal değer olup olmadığını regex ile doğrula
        has_num1 = bool(re.search(r"\b\d+\b", text1))
        has_num2 = bool(re.search(r"\b\d+\b", text2))
        if not (has_num1 and has_num2):
            return None

        pred1 = self._extract_numerical_predicate(text1)
        pred2 = self._extract_numerical_predicate(text2)

        if not pred1 or not pred2:
            return None

        key1, val1 = pred1
        key2, val2 = pred2

        # Aynı yüklem veya konu üzerinde farklı sayılar iddia ediliyorsa
        if key1 == key2 and val1 != val2:
            try:
                import z3
                solver = z3.Solver()
                # 500ms timeout sınırı
                solver.set("timeout", 500)

                x = z3.Int(key1)
                solver.add(x == val1)
                solver.add(x == val2)

                check_res = solver.check()
                if check_res == z3.unsat:
                    reason_msg = (
                        f"Z3 Formal SMT Çözücü (500ms): '{key1}' kuralı için "
                        f"{val1} != {val2} sayısal çelişkisi kesinleşti (UNSAT)."
                    )
                    logger.warning(f"🚨 [Z3 CONTRADICTION] {reason_msg}")
                    return {
                        "contradiction": True,
                        "reason": reason_msg,
                        "method": "z3"
                    }
            except Exception as e:
                logger.error(f"Z3 Solver yürütülürken hata oluştu: {e}")
                # Z3 kütüphanesi hatasında deterministik fallback
                return {
                    "contradiction": True,
                    "reason": f"Sayısal Değer Uyuşmazlığı: {key1} için ({val1} != {val2})",
                    "method": "z3"
                }

        return None

    async def _query_ollama_decision(self, text1: str, text2: str) -> Dict[str, Any]:
        """
        Ollama (qwen2.5:14b) üzerinden OpenAI istemcisi (veya HTTPX fallback) ile
        'Bu iki cümle çelişiyor mu? Sadece EVET veya HAYIR de.' sorusunu yöneltir.
        """
        prompt = (
            f"1. Cümle: \"{text1}\"\n"
            f"2. Cümle: \"{text2}\"\n\n"
            f"Bu iki cümle çelişiyor mu? Sadece EVET veya HAYIR de."
        )

        model_name = "qwen2.5:14b"
        raw_response = ""

        # 1. Öncelik: OpenAI SDK ile Ollama v1 API
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",
                timeout=15.0
            )
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=20
            )
            if response.choices and len(response.choices) > 0:
                raw_response = response.choices[0].message.content or ""
        except Exception as openai_err:
            logger.error(f"OpenAI SDK ile Ollama çağrısı başarısız oldu: {openai_err}. HTTPX deneniyor.")

        # 2. İkincil Fallback: Doğrudan HTTPX ile istek
        if not raw_response:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=15.0) as http_client:
                    res = await http_client.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": model_name,
                            "prompt": prompt,
                            "stream": False,
                            "options": {"temperature": 0.0, "num_predict": 20}
                        }
                    )
                    if res.status_code == 200:
                        data = res.json()
                        raw_response = data.get("response", "")
                    else:
                        logger.error(f"Ollama HTTP {res.status_code} döndürdü: {res.text}")
            except Exception as http_err:
                logger.error(f"HTTPX üzerinden Ollama çağrısı başarısız oldu: {http_err}")

        cleaned_answer = raw_response.strip().upper()
        logger.info(f"Ollama Hakem Yanıtı: '{cleaned_answer}'")

        if "EVET" in cleaned_answer:
            return {
                "contradiction": True,
                "reason": f"Ollama ({model_name}) hakemi çelişki tespit etti (Yanıt: EVET).",
                "method": "llm"
            }
        elif "HAYIR" in cleaned_answer:
            return {
                "contradiction": False,
                "reason": f"Ollama ({model_name}) hakemi çelişki olmadığına karar verdi (Yanıt: HAYIR).",
                "method": "llm"
            }
        else:
            # Model tam format dışına çıktıysa ama cevap verdiyse
            is_contradictory = "EVET" in cleaned_answer or "ÇELİŞ" in cleaned_answer
            return {
                "contradiction": is_contradictory,
                "reason": f"Ollama ({model_name}) hakem çıktısı: {raw_response.strip()}",
                "method": "llm"
            }

    async def execute(self, text1: str, text2: str) -> ToolResult:
        """
        İki metin arasındaki çelişkiyi test eder ve JSON formatında döndürür.
        """
        logger.info(
            f"⚖️ [CONTRADICTION CHECKER] İfadeler inceleniyor:\n"
            f"Metin 1: '{text1[:90]}...'\nMetin 2: '{text2[:90]}...'"
        )

        # 1. Aşama: Sayısal Değerler İçin Z3 SMT Çözücü Kontrolü (500ms timeout)
        z3_result = self._check_z3_contradiction(text1, text2)
        if z3_result is not None:
            logger.info(f"Z3 yöntemiyle çelişki sonucu alındı: {z3_result}")
            return ToolResult(output=json.dumps(z3_result, ensure_ascii=False, indent=2))

        # 2. Aşama: Sentence-Transformers Vektör Benzerliği (Eşik: 0.75)
        embedder = _get_embed_model()
        similarity = 0.0

        if embedder is not None:
            try:
                emb1 = embedder.encode(text1)
                emb2 = embedder.encode(text2)
                norm1 = np.linalg.norm(emb1)
                norm2 = np.linalg.norm(emb2)
                if norm1 > 0 and norm2 > 0:
                    similarity = float(np.dot(emb1, emb2) / (norm1 * norm2))
                    similarity = round(similarity, 4)
            except Exception as e:
                logger.error(f"Vektör embedding hesaplama hatası: {e}")

        logger.info(f"Metinler arası MiniLM semantik benzerlik: {similarity}")

        # Eğer benzerlik 0.75'in altındaysa (veya embedder yoksa ve sayısal değilse)
        if similarity <= 0.75 and embedder is not None:
            similarity_result = {
                "contradiction": False,
                "reason": (
                    f"Metinlerin semantik benzerliği eşik değerin altındadır "
                    f"({similarity:.2f} <= 0.75); ifadeler farklı konuları ele almaktadır."
                ),
                "method": "similarity"
            }
            logger.info(f"Benzerlik 0.75 altında kaldı, çelişki yok sayıldı.")
            return ToolResult(output=json.dumps(similarity_result, ensure_ascii=False, indent=2))

        # 3. Aşama: Benzerlik > 0.75 ise Ollama (qwen2.5:14b) Hakem Sorgulaması
        llm_result = await self._query_ollama_decision(text1, text2)
        logger.info(f"LLM hakem yöntemiyle çelişki sonucu alındı: {llm_result}")

        return ToolResult(output=json.dumps(llm_result, ensure_ascii=False, indent=2))
