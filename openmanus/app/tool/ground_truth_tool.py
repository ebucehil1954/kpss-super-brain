"""
OpenManus Tool: Dinamik Ground Truth Doğrulama Aracı (Ground Truth Tool)
Proje kökündeki canonical_facts/ klasöründeki tüm .jsonl dosyalarını dinamik okur,
ve verilen iddiayı (claim) tam eşleşme veya fuzzy matching ile (%90 üzeri) doğrulayarak
"DOĞRU" veya "BİLİNMİYOR" döndürür.
"""
from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

from app.logger import logger
from app.tool.base import BaseTool, ToolResult

# Fuzzy matching kütüphanesi için kademeli içe aktarım
try:
    from fuzzywuzzy import fuzz
except ImportError:
    try:
        from thefuzz import fuzz
    except ImportError:
        import difflib

        class _DifflibFuzzFallback:
            @staticmethod
            def ratio(s1: str, s2: str) -> int:
                return int(difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio() * 100)

            @staticmethod
            def partial_ratio(s1: str, s2: str) -> int:
                s1, s2 = s1.lower(), s2.lower()
                if not s1 or not s2:
                    return 0
                if s1 in s2 or s2 in s1:
                    return 100
                short, long = (s1, s2) if len(s1) <= len(s2) else (s2, s1)
                best = 0
                for i in range(len(long) - len(short) + 1):
                    sub = long[i : i + len(short)]
                    sim = difflib.SequenceMatcher(None, short, sub).ratio()
                    if sim > best:
                        best = sim
                return int(best * 100)

            @staticmethod
            def token_set_ratio(s1: str, s2: str) -> int:
                t1 = set(re.findall(r"\w+", s1.lower()))
                t2 = set(re.findall(r"\w+", s2.lower()))
                if not t1 or not t2:
                    return 0
                intersection = " ".join(sorted(t1 & t2))
                diff1 = " ".join(sorted(t1 - t2))
                diff2 = " ".join(sorted(t2 - t1))
                c1 = (intersection + " " + diff1).strip()
                c2 = (intersection + " " + diff2).strip()
                return int(difflib.SequenceMatcher(None, c1, c2).ratio() * 100)

        fuzz = _DifflibFuzzFallback()


class GroundTruthTool(BaseTool):
    """
    KPSS ve mevzuat iddialarını canonical_facts/ veritabanından dinamik doğrulayan araç.
    """
    name: str = "ground_truth_verifier"
    description: str = (
        "Verilen bir KPSS iddiasını (claim) canonical_facts/ klasöründeki resmi kanıtlarla "
        "karşılaştırır. Tam eşleşme veya %90 üzeri benzerlik durumunda 'DOĞRU', aksi takdirde 'BİLİNMİYOR' döndürür."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "claim": {
                "type": "string",
                "description": "(Gerekli) Doğrulanacak KPSS iddiası veya önerme metni."
            }
        },
        "required": ["claim"]
    }

    def _get_canonical_dir(self) -> Path:
        """
        canonical_facts dizinini dinamik olarak arar; yoksa proje kökünde oluşturur.
        """
        candidate_paths = [
            Path.cwd() / "canonical_facts",
            Path(__file__).resolve().parent.parent.parent / "canonical_facts",
            Path(__file__).resolve().parent.parent.parent.parent / "canonical_facts"
        ]

        for p in candidate_paths:
            if p.exists() and p.is_dir():
                return p

        # Hiçbiri yoksa varsayılan proje kökünde oluştur
        target_dir = Path(__file__).resolve().parent.parent.parent / "canonical_facts"
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"canonical_facts klasörü oluşturuldu: {target_dir}")
        except Exception as e:
            logger.error(f"canonical_facts dizini oluşturulamadı: {e}")
        return target_dir

    def load_ground_truth(self) -> Dict[str, Dict[str, Any]]:
        """
        canonical_facts/ klasöründeki tüm .jsonl dosyalarını okuyarak bir dict yapısı oluşturur.
        """
        canonical_dir = self._get_canonical_dir()
        db: Dict[str, Dict[str, Any]] = {}

        if not canonical_dir.exists():
            logger.warning(f"canonical_facts dizini mevcut değil: {canonical_dir}")
            return db

        jsonl_files = list(canonical_dir.glob("*.jsonl"))
        logger.info(f"Yüklenen canonical_facts dosya sayısı: {len(jsonl_files)} ({canonical_dir})")

        for filepath in jsonl_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line_idx, line in enumerate(f, start=1):
                        clean_line = line.strip()
                        if not clean_line:
                            continue
                        try:
                            record = json.loads(clean_line)
                            fact_text = record.get("fact")
                            topic = record.get("topic", "Genel")
                            source = record.get("source", filepath.name)
                            attributes = record.get("attributes", {})

                            # Eğer doğrudan "fact" alanı yoksa, konu ve niteliklerden sentetik gerçek üret
                            if not fact_text and topic and attributes:
                                attr_summary = ", ".join([f"{k}: {v}" for k, v in attributes.items()])
                                fact_text = f"{topic} ({attr_summary})"

                            if fact_text:
                                norm_key = fact_text.strip().lower()
                                db[norm_key] = {
                                    "original_fact": fact_text,
                                    "topic": topic,
                                    "attributes": attributes,
                                    "source": source,
                                    "file": filepath.name
                                }
                        except json.JSONDecodeError as json_err:
                            logger.error(f"JSONL parse hatası ({filepath.name} satır {line_idx}): {json_err}")
            except Exception as file_err:
                logger.error(f"Dosya okunamadı ({filepath}): {file_err}")

        logger.info(f"Toplam {len(db)} kanonik bilgi maddesi belleğe alındı.")
        return db

    def verify(self, claim: str) -> str:
        """
        Claim'i, ground truth içinde arar.
        Tam eşleşme veya fuzzy matching ile %90 ve üzeri eşleşirse 'DOĞRU',
        bulamazsa 'BİLİNMİYOR' döndürür.
        """
        if not claim or not claim.strip():
            return "BİLİNMİYOR"

        clean_claim = claim.strip().lower()
        db = self.load_ground_truth()

        if not db:
            logger.warning("Ground truth veritabanı boş, iddia doğrulanamıyor.")
            return "BİLİNMİYOR"

        # 1. Aşama: Tam eşleşme veya doğrudan alt dize eşleşmesi
        for norm_fact, meta in db.items():
            if clean_claim == norm_fact or clean_claim in norm_fact or norm_fact in clean_claim:
                logger.info(f"✅ [GROUND TRUTH: TAM EŞLEŞME] '{claim}' -> '{meta['original_fact']}'")
                return "DOĞRU"

        # 2. Aşama: Fuzzy matching (%90 üzeri benzerlik)
        highest_score = 0
        best_match_fact = None

        for norm_fact, meta in db.items():
            # Ratio, partial_ratio ve token_set_ratio üzerinden en yüksek puanı al
            r1 = fuzz.ratio(clean_claim, norm_fact)
            r2 = fuzz.token_set_ratio(clean_claim, norm_fact)
            score = max(r1, r2)

            if score > highest_score:
                highest_score = score
                best_match_fact = meta["original_fact"]

        logger.info(f"Fuzzy matching en yüksek benzerlik skoru: %{highest_score} (Eşleşen: '{best_match_fact}')")

        if highest_score >= 90:
            logger.info(f"✅ [GROUND TRUTH: DOĞRU (FUZZY)] İddia %{highest_score} benzerlikle doğrulandı.")
            return "DOĞRU"

        logger.info(f"ℹ️ [GROUND TRUTH: BİLİNMİYOR] İddia için %90 veya üzeri eşleşme bulunamadı (En yüksek: %{highest_score}).")
        return "BİLİNMİYOR"

    def verify_with_details(self, claim: str) -> Dict[str, Any]:
        """
        Claim doğrulamasını sonuç, eşleşen kaynak ve benzerlik skoru ile detaylı döndürür.
        """
        verdict = self.verify(claim)
        db = self.load_ground_truth()
        clean_claim = claim.strip().lower()

        best_score = 0
        best_meta: Optional[Dict[str, Any]] = None

        for norm_fact, meta in db.items():
            if clean_claim == norm_fact or clean_claim in norm_fact or norm_fact in clean_claim:
                best_score = 100
                best_meta = meta
                break
            score = max(fuzz.ratio(clean_claim, norm_fact), fuzz.token_set_ratio(clean_claim, norm_fact))
            if score > best_score:
                best_score = score
                best_meta = meta

        result = {
            "status": verdict,
            "claim": claim,
            "confidence_score": best_score,
            "matched_fact": best_meta["original_fact"] if (best_meta and best_score >= 90) else None,
            "provenance": best_meta["source"] if (best_meta and best_score >= 90) else None,
            "topic": best_meta["topic"] if (best_meta and best_score >= 90) else None
        }
        return result

    async def execute(self, claim: str) -> ToolResult:
        """
        Claim'i doğrular ve JSON formatında ToolResult çıktısı verir.
        """
        logger.info(f"🔍 [GROUND TRUTH TOOL] İddia doğrulanıyor: '{claim}'")
        try:
            details = self.verify_with_details(claim)
            return ToolResult(output=json.dumps(details, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"GroundTruthTool execute sırasında hata: {e}")
            return ToolResult(error=f"GroundTruthTool execution failed: {str(e)}")
