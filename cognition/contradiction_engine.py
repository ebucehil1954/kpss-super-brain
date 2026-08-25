"""
KPSS Super-Brain: Çelişki Tespit ve Çözüm Motoru (Contradiction Engine v6)
Farklı öğretmenlerin ders anlatımlarındaki uyuşmazlıkları ve resmî mevzuatla çelişen iddiaları yakalar.
Kurallar:
- Resmî vs Gayriresmî -> OFFICIAL_SOURCE_WINS
- Öğretmen vs Öğretmen (konsensüs yok) -> UNRESOLVED
- Bağımsız >= 3 kaynak mutabakatı -> MULTI_SOURCE_CONSENSUS
- Belirsiz/İkisi de resmî -> MANUAL_REVIEW_REQUIRED
- DB idempotency & gerçek SQLite sorgulu count_unresolved_high_severity
"""
from __future__ import annotations

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
        (r"15\s*üye", r"11\s*üye", "Anayasa Mahkemesi Üye Sayısı Çelişkisi", ContradictionSeverity.HIGH),
        (r"600\s*milletvekili", r"550\s*milletvekili", "TBMM Milletvekili Sayısı Çelişkisi", ContradictionSeverity.HIGH),
        (r"12\s*yıl", r"6\s*yıl", "AYM Üyeleri Görev Süresi Çelişkisi", ContradictionSeverity.HIGH),
        (r"askeri\s*ıslahat\s*yapılmıştır", r"askeri\s*ıslahat\s*yapılmamıştır", "Lale Devri Askeri Islahat İhtilafı", ContradictionSeverity.MEDIUM),
        (r"başkanlık\s*kararnamesi", r"tüzük", "Mülga Tüzük / Kararname Çelişkisi", ContradictionSeverity.HIGH)
    ]

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
        Verilen iddia kümesi içindeki çelişkileri tespit eder ve kaynak tipine göre çözümler.
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
                        # Deterministik ve simetrik ID üretimi (idempotent)
                        t_min = min(t1, t2)
                        t_max = max(t1, t2)
                        contra_id = f"contra_{hashlib.sha256(f'{lesson}:{topic}:{title}:{t_min}:{t_max}'.encode('utf-8')).hexdigest()[:12]}"
                        
                        is_off1 = cls._is_official_source(c1)
                        is_off2 = cls._is_official_source(c2)

                        # Çözüm Politikası Ayrımı:
                        if is_off1 and not is_off2:
                            resolution = ContradictionResolution.OFFICIAL_SOURCE_WINS
                            winning_id = c1.get("claim_id", f"c_{i}")
                            rationale = f"Resmî kaynak '{s1}', '{title}' konusunda gayriresmî iddiaya üstün kılınmıştır."
                            resolved_at = datetime.now().isoformat()
                        elif is_off2 and not is_off1:
                            resolution = ContradictionResolution.OFFICIAL_SOURCE_WINS
                            winning_id = c2.get("claim_id", f"c_{j}")
                            rationale = f"Resmî kaynak '{s2}', '{title}' konusunda gayriresmî iddiaya üstün kılınmıştır."
                            resolved_at = datetime.now().isoformat()
                        elif not is_off1 and not is_off2:
                            # 2. Bağımsız Çoklu Kaynak Konsensüsü (MULTI_SOURCE_CONSENSUS)
                            sources_1 = {c.get("source") or c.get("speaker_or_author") for c in claims if (re.search(p1, str(c.get("text", "")).lower()) and not re.search(p2, str(c.get("text", "")).lower())) and (c.get("source") or c.get("speaker_or_author"))}
                            sources_2 = {c.get("source") or c.get("speaker_or_author") for c in claims if (re.search(p2, str(c.get("text", "")).lower()) and not re.search(p1, str(c.get("text", "")).lower())) and (c.get("source") or c.get("speaker_or_author"))}
                            
                            if len(sources_1) >= 3 and len(sources_2) <= 1:
                                resolution = ContradictionResolution.MULTI_SOURCE_CONSENSUS
                                winning_id = c1.get("claim_id", f"c_{i}")
                                rationale = f"{len(sources_1)} bağımsız eğitmen mutabakatı ile '{title}' konusunda çoğunluk iddia kabul edilmiştir."
                                resolved_at = datetime.now().isoformat()
                            elif len(sources_2) >= 3 and len(sources_1) <= 1:
                                resolution = ContradictionResolution.MULTI_SOURCE_CONSENSUS
                                winning_id = c2.get("claim_id", f"c_{j}")
                                rationale = f"{len(sources_2)} bağımsız eğitmen mutabakatı ile '{title}' konusunda çoğunluk iddia kabul edilmiştir."
                                resolved_at = datetime.now().isoformat()
                            else:
                                # İki öğretmen/gayriresmî kaynak çelişiyor ve konsensüs yok: UNRESOLVED kalmalı
                                resolution = ContradictionResolution.UNRESOLVED
                                winning_id = None
                                rationale = f"İki bağımsız eğitmen ('{s1}' ve '{s2}') '{title}' konusunda çelişmektedir. Resmî mevzuat teyidi bekleniyor."
                                resolved_at = None
                        else:
                            resolution = ContradictionResolution.MANUAL_REVIEW_REQUIRED
                            winning_id = None
                            rationale = f"Her iki iddia da resmî kaynak olarak işaretlenmiş, inceleme gereklidir."
                            resolved_at = None

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
                            resolution=resolution,
                            winning_claim_id=winning_id,
                            resolution_rationale=rationale,
                            resolved_at=resolved_at
                        )
                        cls.save_contradiction(record)
                        detected.append(record)

        return detected

    @classmethod
    def count_unresolved_high_severity(cls, lesson: Optional[str] = None, topic: Optional[str] = None) -> int:
        """Çözümlenmemiş YÜKSEK (HIGH) seviyeli çelişki sayısını doğrudan veritabanından döner."""
        with db_session() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) as cnt FROM contradictions WHERE resolution = 'UNRESOLVED' AND severity = 'HIGH'"
            params = []
            if lesson:
                query += " AND (lesson = ? OR lesson = 'GENEL')"
                params.append(lesson)
            if topic:
                query += " AND (topic = ? OR topic = 'GENEL')"
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
                cursor.execute("SELECT * FROM contradictions WHERE resolution = 'UNRESOLVED' AND lesson = ?", (lesson,))
            else:
                cursor.execute("SELECT * FROM contradictions WHERE resolution = 'UNRESOLVED'")
            return [dict(r) for r in cursor.fetchall()]

contradiction_engine = ContradictionEngine()
