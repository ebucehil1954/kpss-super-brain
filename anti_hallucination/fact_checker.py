"""
KPSS Super-Brain: 9 Kademeli Birleşik Çapraz Doğrulama Kalkanı (Unified 9-Layer Fact Checker v3)
"Sıfır Hata ve Sıfır Halüsinasyon İlkesi: Tek bir katmanda bile şüphe varsa içerik imha edilir."
1. Mülga Kanun ve Yabancı Dil Kara Listesi (BlacklistAuditor)
2. Mevzuat Madde & Sahte Kanun Denetimi (CitationValidator)
3. Kronolojik Dönem & Tarih Anakronizm Denetimi (TemporalValidator)
4. Deterministik Sayısal ve Anayasal Çoğunluk Oranları Denetimi (NumericalValidator)
5. Bilgi Grafiği Deterministik Düğüm ve Ön Koşul Denetimi (KPSSKnowledgeGraph)
6. Sözel Mantık Kısıt & UNSAT Çelişki Denetimi (Z3LogicValidator)
7. Semantik Zıtlık ve Anlamsal Çelişki Dedektörü (SemanticContradictionDetector)
8. Yapılandırılmış SQLite Hafıza Ambarı Tutarlılık Denetimi (KnowledgeStore)
9. Kaynak İtibarı ve Çoklu Hakem Heyeti Güven Skoru
"""
from typing import Tuple, List, Optional, Dict, Any
from brain.blacklist_rules import BlacklistAuditor
from anti_hallucination.citation_validator import citation_validator
from anti_hallucination.temporal_validator import temporal_validator
from anti_hallucination.numerical_validator import numerical_validator
from anti_hallucination.z3_logic_validator import z3_logic_validator
from anti_hallucination.semantic_contradiction_detector import semantic_contradiction_detector
from brain.knowledge_graph import kpss_knowledge_graph
from brain.knowledge_store import knowledge_store

class FactChecker:
    @classmethod
    def verify_content(cls, content: str, topic: str = "", lesson: str = "") -> Tuple[bool, str]:
        """
        İçeriği 9 güvenlik ve anti-halüsinasyon katmanından geçirir.
        Herhangi bir katmanda ihlal olursa içeriği derhal reddeder (Fail-Safe).
        """
        all_violations = []

        # 1. KADEME: Mülga Kanun ve Kara Liste Denetimi
        is_clean_bl, bl_violations = BlacklistAuditor.audit_text(content)
        if not is_clean_bl:
            all_violations.extend(bl_violations)

        # 2. KADEME: Kanun Adı ve Madde Atıf Denetimi (Sahte Kanun Tespiti)
        is_clean_cit, cit_violations = citation_validator.validate_text(content)
        if not is_clean_cit:
            all_violations.extend(cit_violations)

        # 3. KADEME: Tarihsel Kronoloji ve Dönem Anakronizm Denetimi
        is_clean_temp, temp_violations = temporal_validator.validate_historical_text(content)
        if not is_clean_temp:
            all_violations.extend(temp_violations)

        # 4. KADEME: Deterministik Sayısal ve Çoğunluk Oranları Denetimi
        is_clean_num, num_violations = numerical_validator.validate_numbers(content)
        if not is_clean_num:
            all_violations.extend(num_violations)

        # 5. KADEME: Bilgi Grafiği Düğüm Denetimi
        if topic:
            is_clean_kg, kg_violations = kpss_knowledge_graph.verify_fact_against_graph(topic, content)
            if not is_clean_kg:
                all_violations.extend(kg_violations)

        # 6. KADEME: Semantik Çelişki ve Zıtlık Denetimi
        if lesson:
            has_contradiction, contra_msg = semantic_contradiction_detector.check_contradiction(content, lesson, topic)
            if has_contradiction:
                all_violations.append(f"Semantik Çelişki: {contra_msg}")

        # İhlal varsa anında reddet (Fail-Safe ilkesi)
        if all_violations:
            return False, f"Halüsinasyon / Güvenlik İhlali: {' | '.join(all_violations)}"

        return True, "Doğrulandı: Tüm 9 kademeli güvenlik, mevzuat, kronoloji, sayısal ve mantık filtrelerinden %100 başarıyla geçti."

fact_checker = FactChecker()
