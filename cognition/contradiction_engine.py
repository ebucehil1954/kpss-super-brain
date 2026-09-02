"""
KPSS Super-Brain: Semantik Çelişki Tespit ve Çözüm Motoru (Contradiction Engine v7 - AI Brain)
Farklı öğretmenlerin ders anlatımlarındaki uyuşmazlıkları ve resmî mevzuatla çelişen iddiaları
sentence-transformers/all-MiniLM-L6-v2 vektör benzerliği (> 0.75) ve yerel Ollama LLM (qwen2.5:7b) ile tespit eder.
"""
from __future__ import annotations

import re
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
import httpx

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("KPSS_SUPER_BRAIN")

from brain.models import (
    ContradictionRecord, ContradictionSeverity, ContradictionResolution, AtomicClaim
)
from brain.database import db_session
from config import super_brain_config

# Lazy-loaded embedding model
_EMBEDDING_MODEL = None

def _get_embedding_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ sentence-transformers/all-MiniLM-L6-v2 modeli yüklendi.")
        except Exception as e:
            logger.warning(f"SentenceTransformer yüklenemedi: {e}. Vektör fallback devrede.")
            _EMBEDDING_MODEL = "FALLBACK"
    return _EMBEDDING_MODEL

def _compute_cosine_similarity(text1: str, text2: str) -> float:
    """İki metnin semantik kosinüs benzerliğini hesaplar."""
    model = _get_embedding_model()
    if model != "FALLBACK" and hasattr(model, "encode"):
        try:
            embs = model.encode([text1, text2])
            v1, v2 = embs[0], embs[1]
            dot = np.dot(v1, v2)
            norm = np.linalg.norm(v1) * np.linalg.norm(v2)
            return float(dot / norm) if norm > 0 else 0.0
        except Exception as e:
            logger.error(f"Hata: Embedding çıkarımı başarısız: {e}", exc_info=True)

    w1 = set(re.findall(r"\w+", text1.lower()))
    w2 = set(re.findall(r"\w+", text2.lower()))
    if not w1 or not w2:
        return 0.0
    intersection = len(w1 & w2)
    union = len(w1 | w2)
    return float(intersection / union) if union > 0 else 0.0

def _extract_predicate_and_number(text: str) -> Optional[Tuple[str, set]]:
    """Metindeki sayısal anayasa/müfredat yüklemini ve sayı kümesini ayrıştırır."""
    t = text.lower()
    nums = set(re.findall(r"\b\d+\b", t))
    if not nums:
        return None
        
    if "toplantı yeter" in t:
        return ("toplanti_yeter", nums)
    if "karar yeter" in t:
        return ("karar_yeter", nums)
    if "seçim" in t and ("yıl" in t or "dönem" in t or "5" in nums or "4" in nums):
        return ("secim_donemi", nums)
    if "seçilme yaş" in t or ("yaş" in t and "milletvekili" in t):
        return ("secilme_yasi", nums)
    if "aym" in t or "anayasa mahkemesi" in t:
        if "görev" in t or "yıl" in t:
            return ("aym_gorev_suresi", nums)
        if "üye" in t:
            return ("aym_uye_sayisi", nums)
    if "tbmm" in t and ("üye" in t or "milletvekili" in t):
        return ("tbmm_uye_sayisi", nums)
    if "hsk" in t and "üye" in t:
        return ("hsk_uye_sayisi", nums)
        
    return None

_OLLAMA_AVAILABLE = None

def _is_ollama_available() -> bool:
    global _OLLAMA_AVAILABLE
    if _OLLAMA_AVAILABLE is None:
        try:
            with httpx.Client(timeout=2.0) as client:
                r = client.get(f"{super_brain_config.OLLAMA_BASE_URL}/api/tags")
                _OLLAMA_AVAILABLE = (r.status_code == 200)
        except Exception:
            _OLLAMA_AVAILABLE = False
    return _OLLAMA_AVAILABLE

def check_contradiction(text1: str, text2: str, precomputed_sim: Optional[float] = None) -> Dict[str, Any]:
    """
    İki metnin all-MiniLM-L6-v2 kosinüs benzerliğini çıkarır.
    Benzerlik > 0.75 ise Ollama (qwen2.5:7b) ile semantik çelişki denetimi yapar.
    """
    if precomputed_sim is not None:
        sim = float(precomputed_sim)
    else:
        sim = _compute_cosine_similarity(text1, text2)
    
    # 1. Belirli Sayısal Yüklem Uyuşmazlığı Denetimi
    pred1 = _extract_predicate_and_number(text1)
    pred2 = _extract_predicate_and_number(text2)

    has_predicate_num_conflict = False
    conflict_desc = ""
    if pred1 and pred2 and pred1[0] == pred2[0]:
        if pred1[1] != pred2[1]:
            has_predicate_num_conflict = True
            conflict_desc = f"'{pred1[0]}' konusunda sayısal değer uyuşmazlığı: {pred1[1]} vs {pred2[1]}"

    # Benzerlik eşiği altındaysa ve aynı yüklemde sayısal uyuşmazlık yoksa konular farklıdır
    if sim < 0.75 and not has_predicate_num_conflict:
        return {
            "is_contradictory": False,
            "similarity": sim,
            "severity": "NONE",
            "explanation": "Kosinüs benzerliği eşik altında (< 0.75), konular farklı."
        }

    # Kosinüs benzerliği > 0.75 veya sayısal çelişki: Ollama qwen2.5:7b aktifse sor
    if _is_ollama_available():
        ollama_url = f"{super_brain_config.OLLAMA_BASE_URL}/api/generate"
        prompt = f"""Sen tarafsız bir KPSS mantık ve anayasa denetleyicisisin.
Aşağıdaki iki ifadeyi karşılaştır:
Metin 1: "{text1}"
Metin 2: "{text2}"

Bu iki ifade KPSS sınav müfredatı ve olgusal gerçeklik bakımından birbiriyle ÇELİŞİYOR MU (aynı soruya farklı cevaplar mı veriyor)?
Sadece aşağıdaki JSON formatında cevap ver:
{{"is_contradictory": true/false, "severity": "HIGH/MEDIUM/LOW", "explanation": "Kısa açıklama"}}"""

        try:
            with httpx.Client(timeout=25.0) as client:
                resp = client.post(ollama_url, json={
                    "model": super_brain_config.FALLBACK_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                })
                if resp.status_code == 200:
                    raw_json = resp.json().get("response", "")
                    m = re.search(r"\{.*\}", raw_json, re.DOTALL)
                    if m:
                        parsed = json.loads(m.group(0))
                        return {
                            "is_contradictory": bool(parsed.get("is_contradictory", False)),
                            "similarity": sim,
                            "severity": str(parsed.get("severity", "HIGH")).upper(),
                            "explanation": str(parsed.get("explanation", ""))
                        }
        except Exception as e:
            logger.debug(f"Ollama contradiction check hatası/zaman aşımı: {e}")

    # Ollama erişilemediğinde deterministik kural denetimi
    if has_predicate_num_conflict:
        return {
            "is_contradictory": True,
            "similarity": sim,
            "severity": "HIGH",
            "explanation": conflict_desc
        }

    if ("yapılmıştır" in text1 and "yapılmamıştır" in text2) or ("yapılmamıştır" in text1 and "yapılmıştır" in text2):
        return {
            "is_contradictory": True,
            "similarity": sim,
            "severity": "MEDIUM",
            "explanation": "Olumlu/olumsuz ifade zıtlığı."
        }

    return {
        "is_contradictory": False,
        "similarity": sim,
        "severity": "NONE",
        "explanation": "Metinler arasında doğrudan olgusal zıtlık bulunamadı."
    }

class ContradictionEngine:
    """
    KPSS Super-Brain Semantik Çelişki Motoru.
    """
    OFFICIAL_KEYWORDS = ["mevzuat", "resmi", "resmî", "anayasa", "kanun", "tuik", "tüik", "mta", "osym", "ösym", "meb"]

    @classmethod
    def _is_official_source(cls, claim: Dict[str, Any]) -> bool:
        """İddianın resmî bir mevzuat/kurum kaynağından gelip gelmediğini doğrular."""
        src = str(claim.get("source", "")).lower()
        speaker = str(claim.get("speaker_or_author", "")).lower()
        refs = claim.get("evidence_refs", [])
        
        if any(kw in src for kw in cls.OFFICIAL_KEYWORDS) or any(kw in speaker for kw in cls.OFFICIAL_KEYWORDS):
            return True
            
        for ref in refs:
            r_src = str(ref.get("source_id", "") if isinstance(ref, dict) else getattr(ref, "source_id", "")).lower()
            r_type = str(ref.get("source_type", "") if isinstance(ref, dict) else getattr(ref, "source_type", "")).lower()
            if any(kw in r_src for kw in cls.OFFICIAL_KEYWORDS) or "legislation" in r_type or "official" in r_type:
                return True
        return False

    @classmethod
    def save_contradiction(cls, record: ContradictionRecord):
        """Çelişkiyi SQLite contradictions tablosuna idempotent olarak mühürler."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO contradictions (
                contradiction_id, lesson, topic, claim_a_id, claim_a_text, claim_a_source,
                claim_b_id, claim_b_text, claim_b_source, severity, resolution,
                winning_claim_id, resolution_rationale, created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.contradiction_id, record.lesson, record.topic,
                record.claim_a_id, record.claim_a_text, record.claim_a_source,
                record.claim_b_id, record.claim_b_text, record.claim_b_source,
                record.severity.value, record.resolution.value,
                record.winning_claim_id, record.resolution_rationale,
                record.created_at, record.resolved_at
            ))

    @classmethod
    def detect_and_resolve_contradictions(
        cls,
        lesson: str,
        topic: str,
        claims: List[Dict[str, Any]]
    ) -> List[ContradictionRecord]:
        """
        Vektör benzerliği (> 0.75) ve LLM semantik analizi ile çelişkileri tespit eder ve çözümler.
        """
        detected: List[ContradictionRecord] = []
        n = len(claims)
        if n < 2:
            return detected

        texts = [str(c.get("text", "")) for c in claims]
        predicates = [_extract_predicate_and_number(t) for t in texts]

        # [AŞAMA 2 OPTİMİZASYON]: Toplu Vektörleşme (Batch Encoding) ile O(n) Benzerlik Matrisi
        sim_matrix = None
        model = _get_embedding_model()
        if model != "FALLBACK" and hasattr(model, "encode"):
            try:
                embs = model.encode(texts)
                norms = np.linalg.norm(embs, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                embs_norm = embs / norms
                sim_matrix = np.dot(embs_norm, embs_norm.T)
            except Exception as e:
                logger.error(f"Batch embedding hatası: {e}", exc_info=True)

        for i in range(n):
            for j in range(i + 1, n):
                c1 = claims[i]
                c2 = claims[j]
                t1 = texts[i]
                t2 = texts[j]
                s1 = c1.get("source", "Kaynak 1")
                s2 = c2.get("source", "Kaynak 2")

                pred1 = predicates[i]
                pred2 = predicates[j]
                has_pred_conflict = bool(pred1 and pred2 and pred1[0] == pred2[0] and pred1[1] != pred2[1])

                sim = float(sim_matrix[i, j]) if sim_matrix is not None else None

                # Hızlı Aday Filtreleme: Benzerlik < 0.75 ve sayısal yüklem çelişkisi yoksa
                # ve doğrudan zıtlık kalıbı içermiyorsa kontrolü derhal atla
                has_antonym = ("yapılmıştır" in t1 and "yapılmamıştır" in t2) or ("yapılmamıştır" in t1 and "yapılmıştır" in t2)
                if sim is not None and sim < 0.75 and not has_pred_conflict and not has_antonym:
                    continue

                contra_result = check_contradiction(t1, t2, precomputed_sim=sim)
                if contra_result["is_contradictory"]:
                    severity_str = contra_result.get("severity", "HIGH")
                    severity = ContradictionSeverity.HIGH if severity_str == "HIGH" else (ContradictionSeverity.MEDIUM if severity_str == "MEDIUM" else ContradictionSeverity.LOW)
                    
                    t_min = min(t1.lower(), t2.lower())
                    t_max = max(t1.lower(), t2.lower())
                    contra_id = f"contra_{hashlib.sha256(f'{lesson}:{topic}:{t_min}:{t_max}'.encode('utf-8')).hexdigest()[:12]}"

                    is_off1 = cls._is_official_source(c1)
                    is_off2 = cls._is_official_source(c2)

                    if is_off1 and not is_off2:
                        resolution = ContradictionResolution.OFFICIAL_SOURCE_WINS
                        winning_id = c1.get("claim_id", f"c_{i}")
                        rationale = f"Resmî mevzuat '{s1}', gayriresmî iddiaya üstün kılınmıştır. ({contra_result.get('explanation')})"
                        resolved_at = datetime.now().isoformat()
                    elif is_off2 and not is_off1:
                        resolution = ContradictionResolution.OFFICIAL_SOURCE_WINS
                        winning_id = c2.get("claim_id", f"c_{j}")
                        rationale = f"Resmî mevzuat '{s2}', gayriresmî iddiaya üstün kılınmıştır. ({contra_result.get('explanation')})"
                        resolved_at = datetime.now().isoformat()
                    elif not is_off1 and not is_off2:
                        # Bağımsız kaynak konsensüsü
                        nums1 = set(re.findall(r"\b\d+\b", t1))
                        nums2 = set(re.findall(r"\b\d+\b", t2))
                        sources_1 = {c.get("source") or c.get("speaker_or_author") for c in claims if (nums1 and set(re.findall(r"\b\d+\b", str(c.get("text", "")))) == nums1) and (c.get("source") or c.get("speaker_or_author"))}
                        sources_2 = {c.get("source") or c.get("speaker_or_author") for c in claims if (nums2 and set(re.findall(r"\b\d+\b", str(c.get("text", "")))) == nums2) and (c.get("source") or c.get("speaker_or_author"))}
                        
                        if len(sources_1) >= 3 and len(sources_2) <= 1:
                            resolution = ContradictionResolution.MULTI_SOURCE_CONSENSUS
                            winning_id = c1.get("claim_id", f"c_{i}")
                            rationale = f"{len(sources_1)} bağımsız eğitmen mutabakatı ile çoğunluk iddia kabul edilmiştir."
                            resolved_at = datetime.now().isoformat()
                        elif len(sources_2) >= 3 and len(sources_1) <= 1:
                            resolution = ContradictionResolution.MULTI_SOURCE_CONSENSUS
                            winning_id = c2.get("claim_id", f"c_{j}")
                            rationale = f"{len(sources_2)} bağımsız eğitmen mutabakatı ile çoğunluk iddia kabul edilmiştir."
                            resolved_at = datetime.now().isoformat()
                        else:
                            resolution = ContradictionResolution.UNRESOLVED
                            winning_id = None
                            rationale = f"İki bağımsız eğitmen ('{s1}' ve '{s2}') çelişmektedir. Resmî mevzuat teyidi bekleniyor."
                            resolved_at = None
                    else:
                        resolution = ContradictionResolution.MANUAL_REVIEW_REQUIRED
                        winning_id = None
                        rationale = "Her iki iddia da resmî kaynak olarak işaretlenmiş, manuel inceleme gereklidir."
                        resolved_at = None

                    record = ContradictionRecord(
                        contradiction_id=contra_id,
                        lesson=lesson,
                        topic=topic,
                        claim_a_id=c1.get("claim_id", f"c_{i}"),
                        claim_a_text=t1,
                        claim_a_source=s1,
                        claim_b_id=c2.get("claim_id", f"c_{j}"),
                        claim_b_text=t2,
                        claim_b_source=s2,
                        severity=severity,
                        resolution=resolution,
                        winning_claim_id=winning_id,
                        resolution_rationale=rationale,
                        created_at=datetime.now().isoformat(),
                        resolved_at=resolved_at
                    )
                    cls.save_contradiction(record)
                    detected.append(record)

        return detected

    @classmethod
    def count_unresolved_high_severity(cls, lesson: Optional[str] = None, topic: Optional[str] = None) -> int:
        """Çözümlenmemiş YÜKSEK (HIGH) seviyeli çelişki sayısını veritabanından sorgular."""
        with db_session() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) as cnt FROM contradictions WHERE resolution = 'UNRESOLVED' AND severity = 'HIGH'"
            params = []
            if lesson:
                query += " AND (lesson = ? OR lesson = 'GENEL')"
                params.append(lesson)
            if topic:
                query += " AND topic = ?"
                params.append(topic)
            
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    @classmethod
    def get_unresolved_contradictions(cls, lesson: Optional[str] = None) -> List[Dict[str, Any]]:
        """Henüz çözümlenmemiş çelişkileri listeler."""
        with db_session() as conn:
            cursor = conn.cursor()
            if lesson:
                query = "SELECT * FROM contradictions WHERE resolution = 'UNRESOLVED' AND (lesson = ? OR lesson = 'GENEL')"
                cursor.execute(query, (lesson,))
            else:
                cursor.execute("SELECT * FROM contradictions WHERE resolution = 'UNRESOLVED'")
            return [dict(r) for r in cursor.fetchall()]

contradiction_engine = ContradictionEngine()
