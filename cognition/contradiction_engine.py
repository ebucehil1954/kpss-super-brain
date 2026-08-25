"""
KPSS Super-Brain: Çelişki Tespit ve Çözüm Motoru (Contradiction Engine)
Farklı öğretmenlerin ders anlatımlarındaki uyuşmazlıkları ve resmî mevzuatla çelişen iddiaları yakalar,
açıkça kayıt altına alır ve 'OFFICIAL_SOURCE_WINS' gibi kurallarla deterministik olarak çözer.
"""
import re
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from brain.models import (
    ContradictionRecord, ContradictionSeverity, ContradictionResolution, AtomicClaim
)
from brain.database import db_session

class ContradictionEngine:
    # Bilinen Kesin Zıtlık Kalıpları
    CONTRADICTION_PAIRS = [
        (r"15\s*üyeden", r"11\s*üyeden", "Anayasa Mahkemesi Üye Sayısı Çelişkisi", ContradictionSeverity.HIGH),
        (r"600\s*milletvekili", r"550\s*milletvekili", "TBMM Milletvekili Sayısı Çelişkisi", ContradictionSeverity.HIGH),
        (r"12\s*yıl", r"6\s*yıl", "AYM Üyeleri Görev Süresi Çelişkisi", ContradictionSeverity.HIGH),
        (r"askeri\s*ıslahat\s*yapılmıştır", r"askeri\s*ıslahat\s*yapılmamıştır", "Lale Devri Askeri Islahat İhtilafı", ContradictionSeverity.MEDIUM),
        (r"başkanlık\s*kararnamesi", r"tüzük", "Mülga Tüzük / Kararname Çelişkisi", ContradictionSeverity.HIGH)
    ]

    @classmethod
    def save_contradiction(cls, record: ContradictionRecord):
        """Çelişkiyi SQLite contradictions tablosuna mühürler."""
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
        Verilen iddia kümesi içindeki çelişkileri tespit eder ve resmî kural üstünlüğüyle çözümler.
        """
        detected: List[ContradictionRecord] = []
        n = len(claims)

        for i in range(n):
            for j in range(i + 1, n):
                c1 = claims[i]
                c2 = claims[j]
                t1 = str(c1.get("text", "")).lower()
                t2 = str(c2.get("text", "")).lower()
                s1 = c1.get("source", "Kaynak 1")
                s2 = c2.get("source", "Kaynak 2")

                for p1, p2, title, severity in cls.CONTRADICTION_PAIRS:
                    match_1 = (re.search(p1, t1) and re.search(p2, t2))
                    match_2 = (re.search(p2, t1) and re.search(p1, t2))

                    if match_1 or match_2:
                        contra_id = f"contra_{hashlib.sha256(f'{t1}:{t2}'.encode('utf-8')).hexdigest()[:12]}"
                        
                        # Çözüm Politikası: Resmî Mevzuat veya 1982 Anayasası Güncel Maddesi Kazanır
                        winning_id = c1.get("claim_id", f"c_{i}") if (re.search(p1, t1) and "15" in p1) or "resmi" in s1.lower() else c2.get("claim_id", f"c_{j}")
                        rationale = f"1982 Anayasası ve resmî KPSS müfredatı uyarınca '{title}' konusunda resmî kaynak önceliklendirilmiştir."

                        record = ContradictionRecord(
                            contradiction_id=contra_id,
                            lesson=lesson,
                            topic=topic,
                            claim_a_id=c1.get("claim_id", f"c_{i}"),
                            claim_a_text=c1.get("text", ""),
                            claim_a_source=s1,
                            claim_b_id=c2.get("claim_id", f"c_{j}"),
                            claim_b_text=c2.get("text", ""),
                            claim_b_source=s2,
                            severity=severity,
                            resolution=ContradictionResolution.OFFICIAL_SOURCE_WINS,
                            winning_claim_id=winning_id,
                            resolution_rationale=rationale,
                            resolved_at=datetime.now().isoformat()
                        )
                        cls.save_contradiction(record)
                        detected.append(record)

        return detected

    @classmethod
    def get_unresolved_contradictions(cls, lesson: Optional[str] = None) -> List[Dict[str, Any]]:
        """Henüz çözümlenmemiş çelişkileri listeler."""
        with db_session() as conn:
            cursor = conn.cursor()
            if lesson:
                cursor.execute("SELECT * FROM contradictions WHERE resolution = 'UNRESOLVED' AND lesson = ?", (lesson,))
            else:
                cursor.execute("SELECT * FROM contradictions WHERE resolution = 'UNRESOLVED'")
            return [dict(r) for r in cursor.fetchall()]

contradiction_engine = ContradictionEngine()
