"""
KPSS Super-Brain: Kavramlar Arası Korelasyon ve İlişki Grafı Motoru (Correlation Engine)
Öğrenilen bilgileri birbirinden yalıtılmış bırakmaz:
Kavramlar arasında 'OFTEN_CONFUSED_WITH' (Karıştırılanlar), 'PREREQUISITE_OF' (Ön Koşul),
'CONTRASTS' (Zıtlık) ve 'REGULATED_BY' (Hukuki Dayanak) ilişkilerini kurarak
Soru Üretim Motoru için temel epistemik ağı oluşturur.
"""
from __future__ import annotations

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from brain.knowledge_graph import KPSSKnowledgeGraph
from brain.database import db_session

logger = logging.getLogger("correlation_engine")


class CorrelationEngine:
    """
    Kavramları birbirine bağlayan ve çeldirici soru tuzaklarını haritalandıran motor.
    """

    # ÖSYM'nin en sık sorduğu klasik çeldirici kavram ikilileri
    CANONICAL_CONFUSED_PAIRS = [
        # Vatandaşlık
        {
            "concept_a": "Toplantı Yeter Sayısı",
            "concept_b": "Karar Yeter Sayısı",
            "difference": "Toplantı için üye tamsayısının 1/3'ü (200) gerekir; karar için katılanların salt çoğunluğu (en az 151) gerekir.",
            "lesson": "VATANDASLIK",
            "topic": "1982 Anayasası Yasama Organı"
        },
        {
            "concept_a": "Vali",
            "concept_b": "Kaymakam",
            "difference": "Vali istisnai memurdur ve yetki genişliğine sahiptir; Kaymakam güvenceli meslek memurudur, yetki genişliği yoktur.",
            "lesson": "VATANDASLIK",
            "topic": "İdare Hukuku ve Türkiye'nin İdari Teşkilat Yapısı"
        },
        {
            "concept_a": "İptal Davası (Soyut Norm Denetimi)",
            "concept_b": "İtiraz Yolu (Somut Norm Denetimi / Def'i)",
            "difference": "İptal davası doğrudan 60 gün içinde açılır; İtiraz yolu ise görülmekte olan bir dava sırasında mahkemece AYM'ye taşınır.",
            "lesson": "VATANDASLIK",
            "topic": "1982 Anayasası Yargı Organı ve Yüksek Mahkemeler"
        },
        {
            "concept_a": "Gaiplik",
            "concept_b": "Ölüm Karinesi",
            "difference": "Ölüm karinesinde ceset bulunamaz ama ölümüne kesin gözle bakılır (mahallin en büyük mülki amiri kütüğe ölü yazar); gaiplikte ise mahkeme kararı ve bekleme süreleri (1 yıl / 5 yıl) şarttır.",
            "lesson": "VATANDASLIK",
            "topic": "Temel Hukuk Kavramları ve Hukukun Dalları"
        },
        # Coğrafya
        {
            "concept_a": "Çatalca-Kocaeli Platosu",
            "concept_b": "Taşeli Platosu",
            "difference": "Çatalca-Kocaeli aşınım (peneplen) platosudur ve sanayi yoğunlukludur; Taşeli karstik platodur ve yerleşme seyrektir.",
            "lesson": "COGRAFYA",
            "topic": "Türkiye'nin Fiziki Özellikleri, Jeolojik Yapısı ve Yer Şekilleri"
        },
        {
            "concept_a": "Çukurova (Delta Ovası)",
            "concept_b": "Konya Ovası (Tektonik/Tabaka Ovası)",
            "difference": "Çukurova Seyhan ve Ceyhan akarsularının alüvyon biriktirmesiyle oluşan deltadır; Konya ovası tektonik kökenlidir.",
            "lesson": "COGRAFYA",
            "topic": "Türkiye'nin Fiziki Özellikleri, Jeolojik Yapısı ve Yer Şekilleri"
        },
        # Tarih
        {
            "concept_a": "Tanzimat Fermanı (1839)",
            "concept_b": "Islahat Fermanı (1856)",
            "difference": "Tanzimat tüm Osmanlı tebaasına eşit haklar getirirken; Islahat Fermanı özellikle gayrimüslimlere ayrıcalıklar tanımıştır.",
            "lesson": "TARIH",
            "topic": "19. ve 20. Yüzyıl Osmanlı Devleti (Dağılma Dönemi Islahatları)"
        },
        {
            "concept_a": "I. TBMM",
            "concept_b": "II. TBMM",
            "difference": "I. TBMM kurucu, ihtilalci ve savaş meclisidir (güçler birliği); II. TBMM ise inkılap meclisidir ve Lozan'ı onaylamıştır.",
            "lesson": "TARIH",
            "topic": "I. TBMM Dönemi ve Ayaklanmalar"
        }
    ]

    def __init__(self, graph: Optional[KPSSKnowledgeGraph] = None):
        self.graph = graph or KPSSKnowledgeGraph()
        self._ensure_canonical_pairs_in_graph()

    def _ensure_canonical_pairs_in_graph(self):
        """Temel ÖSYM çeldirici çiftlerini grafiğe mühürler."""
        for p in self.CANONICAL_CONFUSED_PAIRS:
            self.add_confused_pair(
                concept_a=p["concept_a"],
                concept_b=p["concept_b"],
                difference=p["difference"],
                lesson=p["lesson"],
                topic=p["topic"]
            )

    def add_confused_pair(
        self,
        concept_a: str,
        concept_b: str,
        difference: str,
        lesson: str,
        topic: str
    ) -> None:
        """İki karıştırılan kavram arasında çift yönlü 'OFTEN_CONFUSED_WITH' ilişkisi kurar."""
        id_a = f"CONC_{re.sub(r'[^A-Za-z0-9_]', '', concept_a.upper().replace(' ', '_'))}"
        id_b = f"CONC_{re.sub(r'[^A-Za-z0-9_]', '', concept_b.upper().replace(' ', '_'))}"

        # Düğümleri ekle
        self.graph.add_node(
            node_id=id_a,
            label=concept_a,
            node_type="CONCEPT",
            lesson=lesson,
            properties={"topic": topic, "confused_with": concept_b}
        )
        self.graph.add_node(
            node_id=id_b,
            label=concept_b,
            node_type="CONCEPT",
            lesson=lesson,
            properties={"topic": topic, "confused_with": concept_a}
        )

        # Karşılıklı kenarları ekle
        self.graph.add_edge(id_a, id_b, relation="OFTEN_CONFUSED_WITH", weight=1.0)
        self.graph.add_edge(id_b, id_a, relation="OFTEN_CONFUSED_WITH", weight=1.0)

    def discover_correlations_from_db(self) -> int:
        """
        knowledge_records tablosundaki TRAP ve FACT kayıtlarını tarayarak
        metin içindeki karşıtlık ve karıştırma ifadelerinden dinamik ilişkiler çıkarır.
        """
        added_edges = 0
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_records WHERE record_type = 'TRAP'")
            trap_rows = cursor.fetchall()

            for row in trap_rows:
                text = row["text"]
                lesson = row["lesson"]
                topic = row["topic"]

                # 'X ile Y'yi karıştırmayın' kalıpları
                match = re.search(r"([A-ZÇĞİÖŞÜa-zçğıöşü\s]{3,30})\s+(?:ile|ve)\s+([A-ZÇĞİÖŞÜa-zçğıöşü\s]{3,30})\s+(?:karıştır|ayrım|fark)", text, re.IGNORECASE)
                if match:
                    ca = match.group(1).strip()
                    cb = match.group(2).strip()
                    if len(ca) > 3 and len(cb) > 3 and ca.lower() != cb.lower():
                        self.add_confused_pair(ca, cb, difference=text, lesson=lesson, topic=topic)
                        added_edges += 1

        return added_edges

    def get_confused_pairs(self, lesson_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Soru üretimi için en kritik karıştırılan kavram çiftlerini döner."""
        results = []
        seen_pairs = set()

        for edge in self.graph.edges:
            if edge.get("relation") == "OFTEN_CONFUSED_WITH":
                src = edge["source"]
                tgt = edge["target"]
                pair_key = tuple(sorted([src, tgt]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                node_a = self.graph.nodes.get(src, {})
                node_b = self.graph.nodes.get(tgt, {})
                l_a = node_a.get("lesson", "GENEL")

                if lesson_filter and l_a.upper() != lesson_filter.upper():
                    continue

                diff = node_a.get("properties", {}).get("difference") or node_b.get("properties", {}).get("difference") or ""
                results.append({
                    "concept_a": node_a.get("label", src),
                    "concept_b": node_b.get("label", tgt),
                    "lesson": l_a,
                    "topic": node_a.get("properties", {}).get("topic", "Genel"),
                    "difference": diff
                })

        return results

    def get_graph_stats(self) -> Dict[str, Any]:
        """Korelasyon grafiğinin istatistiklerini döner."""
        relation_counts: Dict[str, int] = {}
        for e in self.graph.edges:
            r = e.get("relation", "OTHER")
            relation_counts[r] = relation_counts.get(r, 0) + 1

        return {
            "total_nodes": len(self.graph.nodes),
            "total_edges": len(self.graph.edges),
            "confused_pairs_count": len(self.get_confused_pairs()),
            "relation_types": relation_counts
        }


correlation_engine = CorrelationEngine()
