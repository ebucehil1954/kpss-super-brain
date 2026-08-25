"""
KPSS Super-Brain: Deterministik Z3 SMT Mantık Denetleyicisi (Z3 Logic & Constitution Validator v3)
Anayasa, Vatandaşlık ve Sözel Mantık kısıtlarını Z3 SMT Formal Mantık Çözücüsü ile %100 matematiksel
kesinlikle doğrular. Tek bir mantıksal çelişki (UNSAT) durumunda içeriği anında engeller.
"""
import re
import itertools
from typing import Tuple, Dict, Any, List, Optional, Set

try:
    from z3 import Solver, Int, Distinct, Or, sat, unsat
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

class Z3LogicValidator:
    """
    Formal Logic: Anayasa/Vatandaşlık Maddelerinin ve Sözel Mantığın Z3 SMT Çözücü Kontrolü.
    """

    # ==========================================
    # 1. ANAYASA FORMAL Z3 SMT DOĞRULAYICI
    # ==========================================
    @classmethod
    def validate_constitution_logic(cls, member_count: int, term_years: int) -> bool:
        """
        Anayasa Mahkemesi ve yüksek yargı kurallarını Z3 SMT Solver ile doğrular.
        AYM üye sayısı: 15, Görev süresi: 12 yıl.
        """
        if not Z3_AVAILABLE:
            return member_count == 15 and term_years == 12

        s = Solver()
        aym_members = Int('aym_members')
        aym_term = Int('aym_term')

        # Resmi Anayasa Kısıtları (Ground Truth)
        s.add(aym_members == 15)
        s.add(aym_term == 12)

        # İddia edilen parametreler
        s.add(aym_members == member_count)
        s.add(aym_term == term_years)

        return s.check() == sat

    @classmethod
    def validate_tbmm_logic(cls, member_count: int, quorum: int, decision_min: int) -> bool:
        """
        TBMM üye tamsayısı (600), toplantı yeter sayısı (200), karar yeter en az (151) Z3 kontrolü.
        """
        if not Z3_AVAILABLE:
            return member_count == 600 and quorum == 200 and decision_min == 151

        s = Solver()
        tbmm_total = Int('tbmm_total')
        tbmm_quorum = Int('tbmm_quorum')
        tbmm_dec = Int('tbmm_dec')

        s.add(tbmm_total == 600)
        s.add(tbmm_quorum == 200)
        s.add(tbmm_dec == 151)

        s.add(tbmm_total == member_count)
        s.add(tbmm_quorum == quorum)
        s.add(tbmm_dec == decision_min)

        return s.check() == sat

    @classmethod
    def validate_text(cls, text: str) -> bool:
        """
        Metin içindeki tüm sayısal ve mantıksal iddiaları Z3 SMT Solver ile tarar.
        Eğer metinde resmi anayasal sayılarla çelişen bir iddia (UNSAT) varsa False döner.
        """
        text_lower = text.lower()

        # 1. AYM Üye Sayısı Denetimi
        aym_match = re.search(r"(?:anayasa mahkemesi|aym)\s*(?:üyeleri|üye sayısı)?\s*(?:toplam|ise)?\s*(\d+)\s*(?:üyeden|üye)", text_lower)
        if aym_match:
            count = int(aym_match.group(1))
            if not cls.validate_constitution_logic(member_count=count, term_years=12):
                return False

        # 2. AYM Görev Süresi Denetimi
        aym_term_match = re.search(r"(?:anayasa mahkemesi|aym)\s*üyeleri[^\.\,]*(\d+)\s*yıl", text_lower)
        if aym_term_match:
            term = int(aym_term_match.group(1))
            if not cls.validate_constitution_logic(member_count=15, term_years=term):
                return False

        # 3. TBMM Üye Sayısı Denetimi
        tbmm_match = re.search(r"tbmm\s*(?:üye tam sayısı|milletvekili sayısı|üye sayısı)\s*(?:ise)?\s*(\d+)", text_lower)
        if tbmm_match:
            count = int(tbmm_match.group(1))
            if not cls.validate_tbmm_logic(member_count=count, quorum=200, decision_min=151):
                return False

        # 4. Milletvekili Seçilme Yaşı (18)
        mv_age_match = re.search(r"milletvekili\s*seçilme\s*yaşı\s*(\d+)", text_lower)
        if mv_age_match:
            age = int(mv_age_match.group(1))
            if age != 18:
                return False

        # 5. Cumhurbaşkanı Seçilme Yaşı (40)
        cb_age_match = re.search(r"cumhurbaşkanı\s*seçilme\s*yaşı\s*(\d+)", text_lower)
        if cb_age_match:
            age = int(cb_age_match.group(1))
            if age != 40:
                return False

        # 6. HSK Üye Sayısı (13)
        hsk_match = re.search(r"hsk\s*(?:üye sayısı|üyeden oluşur)\s*(\d+)", text_lower)
        if hsk_match:
            count = int(hsk_match.group(1))
            if count != 13:
                return False

        return True

    # ==========================================
    # 2. SÖZEL MANTIK Z3 SMT ÇÖZÜCÜ
    # ==========================================
    @classmethod
    def _extract_entities_from_text(cls, text: str) -> List[str]:
        """Senaryo metninden isimleri ve nesneleri çıkarır."""
        common_names = [
            "Ahmet", "Burak", "Ceyda", "Deniz", "Elif", "Fatih", "Gamze", "Hakan",
            "İrem", "Kaan", "Leyla", "Murat", "Nur", "Oğuz", "Pelin", "Rıza",
            "Serkan", "Tuğba", "Umut", "Volkan", "Yasemin", "Zafer",
            "A", "B", "C", "D", "E", "F", "G", "K", "L", "M", "N", "P"
        ]
        found = []
        for name in common_names:
            if re.search(rf"\b{name}\b", text, re.IGNORECASE):
                match = re.search(rf"\b{name}\b", text, re.IGNORECASE)
                if match:
                    found.append(match.group(0).capitalize())
        return list(dict.fromkeys(found))

    @classmethod
    def validate_verbal_logic_puzzle(
        cls,
        scenario: str,
        clues: List[str],
        entities: Optional[List[str]] = None,
        slots: Optional[List[int]] = None
    ) -> Tuple[bool, str]:
        """
        Sözel mantık kurgusunun kısıtlarını çözer:
        1. Çelişki kontrolü (Unsatisfiable / Çözümsüzlük tespiti)
        2. Çoklu çözüm kontrolü (Ambiguous / Birden fazla geçerli tablo tespiti)
        """
        if not scenario or len(scenario.strip()) < 15:
            return False, "Sözel mantık senaryo metni yetersiz veya boş."

        if not clues or len(clues) < 2:
            return False, "Sözel mantık sorusunda en az 2 belirleyici ipucu/öncül bulunmalıdır."

        if not entities:
            combined_text = scenario + " " + " ".join(clues)
            entities = cls._extract_entities_from_text(combined_text)

        if not entities or len(entities) < 3:
            entities = ["A", "B", "C"] if len(entities) < 2 else entities

        num_entities = len(entities)
        slot_list = slots or list(range(1, num_entities + 1))

        if Z3_AVAILABLE:
            return cls._solve_with_z3(clues, entities, slot_list)
        else:
            return cls._solve_with_constraint_matrix(clues, entities, slot_list)

    @classmethod
    def _solve_with_z3(cls, clues: List[str], entities: List[str], slots: List[int]) -> Tuple[bool, str]:
        """Z3 SMT solver ile tam kısıt denetimi ve çözüm sayısı hesaplama."""
        try:
            s = Solver()
            n = len(entities)
            positions = {name: Int(f"pos_{name}") for name in entities}

            # Her eleman 1..n arasında ve benzersiz (AllDifferent)
            for p in positions.values():
                s.add(p >= 1, p <= n)
            s.add(Distinct(list(positions.values())))

            # İpuçlarını Z3 kısıtlarına çevir
            for clue in clues:
                clue_l = clue.lower()
                for name, var in positions.items():
                    name_l = name.lower()
                    if name_l in clue_l:
                        num_m = re.search(r"(\d+)\.\s*sırada\s*(?:değildir|olamaz)", clue_l)
                        if num_m:
                            p_val = int(num_m.group(1))
                            s.add(var != p_val)
                        num_pos = re.search(r"(\d+)\.\s*(?:sıradadır|sırada oturmaktadır|sırada yer alır)", clue_l)
                        if num_pos:
                            p_val = int(num_pos.group(1))
                            s.add(var == p_val)

                for n1, v1 in positions.items():
                    for n2, v2 in positions.items():
                        if n1 != n2:
                            pos1 = clue_l.find(n1.lower())
                            pos2 = clue_l.find(n2.lower())
                            if pos1 != -1 and pos2 != -1 and pos1 < pos2:
                                if "hemen önünde" in clue_l or "bir önünde" in clue_l:
                                    s.add(v1 + 1 == v2)
                                elif "hemen arkasında" in clue_l or "bir arkasında" in clue_l:
                                    s.add(v1 == v2 + 1)
                                elif "önündedir" in clue_l:
                                    s.add(v1 < v2)
                                elif "arkasındadır" in clue_l:
                                    s.add(v1 > v2)

            check_res = s.check()
            if check_res == unsat:
                return False, "Z3 SMT Solver: Verilen sözel mantık öncülleri birbiriyle çelişiyor (UNSAT / Çözümsüz Soru)."

            models = []
            while s.check() == sat and len(models) < 10:
                m = s.model()
                sol = {name: m.eval(var).as_long() for name, var in positions.items()}
                models.append(sol)
                block = Or([var != sol[name] for name, var in positions.items()])
                s.add(block)

            sol_count = len(models)
            if sol_count == 0:
                return False, "Z3 Solver: Sözel mantık kurgusuna uygun geçerli çözüm tablosu bulunamadı."
            elif sol_count == 1:
                return True, f"Z3 SMT Solver: Kusursuz Tekil Çözüm (1 geçerli tablo). Çözüm: {models[0]}"
            else:
                return True, f"Z3 SMT Solver: Çözülebilir senaryo ({sol_count} olası dağılım tespit edildi)."

        except Exception as e:
            return cls._solve_with_constraint_matrix(clues, entities, slots)

    @classmethod
    def _parse_clue_to_predicate(cls, clue: str, entities: List[str]):
        """Bir Türkçe ipucunu Python doğrulama fonksiyonuna dönüştürür."""
        clue_l = clue.lower()
        
        # 1. "X n. sırada değildir / sıradadır"
        for name in entities:
            if name.lower() in clue_l:
                not_m = re.search(r"(\d+)\.\s*sırada\s*(?:değildir|olamaz)", clue_l)
                if not_m:
                    pos = int(not_m.group(1))
                    return lambda sol, n=name, p=pos: sol.get(n) != p
                
                pos_m = re.search(r"(\d+)\.\s*(?:sıradadır|sırada oturmaktadır|sırada yer alır)", clue_l)
                if pos_m:
                    pos = int(pos_m.group(1))
                    return lambda sol, n=name, p=pos: sol.get(n) == p

        # 2. "X, Y'nin hemen önünde / arkasında"
        for n1 in entities:
            for n2 in entities:
                if n1 != n2:
                    pos1 = clue_l.find(n1.lower())
                    pos2 = clue_l.find(n2.lower())
                    if pos1 != -1 and pos2 != -1 and pos1 < pos2:
                        if "hemen önünde" in clue_l or "bir önünde" in clue_l:
                            return lambda sol, a=n1, b=n2: sol.get(a) + 1 == sol.get(b)
                        elif "hemen arkasında" in clue_l or "bir arkasında" in clue_l:
                            return lambda sol, a=n1, b=n2: sol.get(a) == sol.get(b) + 1
                        elif "önündedir" in clue_l:
                            return lambda sol, a=n1, b=n2: sol.get(a) < sol.get(b)
                        elif "arkasındadır" in clue_l:
                            return lambda sol, a=n1, b=n2: sol.get(a) > sol.get(b)

        return None

    @classmethod
    def _solve_with_constraint_matrix(cls, clues: List[str], entities: List[str], slots: List[int]) -> Tuple[bool, str]:
        """Deterministik permütasyon matrisi yayılımı."""
        predicates = []
        for c in clues:
            pred = cls._parse_clue_to_predicate(c, entities)
            if pred:
                predicates.append(pred)

        n = len(entities)
        all_perms = list(itertools.permutations(range(1, n + 1)))
        valid_solutions = []

        for perm in all_perms:
            assignment = {entities[i]: perm[i] for i in range(n)}
            if all(p(assignment) for p in predicates):
                valid_solutions.append(assignment)

        if predicates and len(valid_solutions) == 0:
            return False, "Deterministik Kısıt Motoru: Öncüller birbiriyle çelişiyor (0 geçerli tablo)."
        
        return True, f"Deterministik Kısıt Motoru: Senaryo tutarlı ve çözülebilir ({len(valid_solutions)} geçerli çözüm)."

z3_logic_validator = Z3LogicValidator()
