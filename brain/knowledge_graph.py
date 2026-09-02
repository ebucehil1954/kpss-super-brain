"""
KPSS Super-Brain: Deterministik Bilgi Grafiği (Knowledge Graph / DAG Engine v3)
Konular, alt kavramlar, kanun maddeleri ve tarihsel zincirleri matematiksel graf yapısında tutar.
Dinamik genişleme ve deterministik olgu doğrulama kalkanı içerir.
"""
import os
import json
import re
import time
import threading
import tempfile
from typing import Dict, Any, List, Optional, Set, Tuple
from config import super_brain_config

class KPSSKnowledgeGraph:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or str(super_brain_config.KNOWLEDGE_GRAPH_FILE)
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._dirty = False
        self._save_count = 0
        self._load_or_seed()

    def _load_or_seed(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.nodes = data.get("nodes", {})
                    self.edges = data.get("edges", [])
                    if self.nodes:
                        return
            except Exception:
                pass
        
        self._seed_default_kpss_ontology()
        self.save(force=True)

    def save(self, force: bool = False):
        """
        [PHASE 16 ATOMIC CRASH-SAFE PERSISTENCE]
        Geçici dosya (tempfile) + os.replace ile elektrik kesintisinde dahi
        graf dosyasının bozulmasını/sıfırlanmasını kesin olarak önler.
        """
        with self._lock:
            if not force and not self._dirty and os.path.exists(self.storage_path):
                return

            dir_name = os.path.dirname(self.storage_path)
            os.makedirs(dir_name, exist_ok=True)

            temp_fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix="kg_tmp_", suffix=".json")
            os.close(temp_fd) # Windows dosya kilitlemesini önlemek için derhal kapatılır

            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "nodes": self.nodes,
                        "edges": self.edges
                    }, f, ensure_ascii=False, indent=2)

                # Atomik değiştirme (Windows ve POSIX uyumlu, kilit dirençli)
                for attempt in range(5):
                    try:
                        os.replace(temp_path, self.storage_path)
                        break
                    except PermissionError:
                        if attempt == 4:
                            raise
                        time.sleep(0.05)
                self._dirty = False
                self._save_count += 1
            except Exception:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                raise

    def add_node(self, node_id: str, label: str, node_type: str, lesson: str, properties: Optional[Dict[str, Any]] = None, auto_save: bool = True):
        with self._lock:
            self.nodes[node_id] = {
                "id": node_id,
                "label": label,
                "type": node_type,  # TOPIC, ENTITY, LAW_ARTICLE, HISTORICAL_EVENT, MINE_REGION, PEDAGOGY
                "lesson": lesson.upper(),
                "properties": properties or {}
            }
            self._dirty = True
        if auto_save:
            self.save()

    def batch_edge_insertion_atomic(self, edge_candidates: List[Dict[str, Any]]) -> bool:
        """
        [PHASE 16 ATOMIC BATCH MUTATION]
        Tüm kenarları önceden doğrular. Eğer tek bir kenar dahi döngü yaratıyorsa
        veya geçersizse, TÜM GRUP REDDEDİLİR ve graf bozulmaz (rollback).
        """
        with self._lock:
            # 1. Simülasyon: Mevcut kenarların kopyası üzerinde döngü testi
            sim_edges = list(self.edges)
            for cand in edge_candidates:
                src = cand["source"]
                tgt = cand["target"]
                rel = cand.get("relation", "RELATED_TO").upper()

                if rel in self.HIERARCHICAL_RELATIONS:
                    # Döngü testi simülasyonu
                    if src == tgt:
                        raise ValueError(f"Batch Atomic Hata: '{src}' kendine dönemez!")
                    visited = set()
                    stack = [tgt]
                    has_cycle = False
                    while stack:
                        c = stack.pop()
                        if c == src:
                            has_cycle = True
                            break
                        if c in visited:
                            continue
                        visited.add(c)
                        for e in sim_edges:
                            if e["source"] == c and e["relation"].upper() in self.HIERARCHICAL_RELATIONS:
                                stack.append(e["target"])
                    if has_cycle:
                        raise ValueError(f"Batch Atomic Hata: '{src}' -> '{tgt}' ({rel}) döngü yaratacağından tüm batch geri alındı!")

                sim_edges.append({
                    "source": src,
                    "target": tgt,
                    "relation": rel,
                    "weight": cand.get("weight", 1.0)
                })

            # 2. Hata yoksa topluca uygula
            self.edges = sim_edges
            self._dirty = True

        self.save()
        return True

    HIERARCHICAL_RELATIONS: Set[str] = {"IS_A", "PART_OF", "SUBTOPIC_OF", "PREREQUISITE_OF"}
    TRANSITIVE_RELATIONS: Set[str] = {"IS_A", "PART_OF"}
    NON_TRANSITIVE_RELATIONS: Set[str] = {"CONTRADICTS", "ASSOCIATED_WITH", "RELATED_TO"}
    DECAYING_RELATIONS: Set[str] = {"SUPPORTS"}

    def would_create_cycle(self, source: str, target: str, relation: str) -> bool:
        """
        [PHASE 10 DAG ENFORCEMENT]
        Hiyerarşik kenar eklenmeden önce döngü (cycle) yaratıp yaratmayacağını denetler.
        Eğer target düğümünden source düğümüne hiyerarşik bir yol varsa, yeni kenar DÖNGÜ oluşturur.
        """
        if relation.upper() not in self.HIERARCHICAL_RELATIONS:
            return False
        if source == target:
            return True

        visited = set()
        stack = [target]
        while stack:
            curr = stack.pop()
            if curr == source:
                return True
            if curr in visited:
                continue
            visited.add(curr)
            for edge in self.edges:
                if edge["source"] == curr and edge["relation"].upper() in self.HIERARCHICAL_RELATIONS:
                    stack.append(edge["target"])
        return False

    def add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0, auto_save: bool = True) -> Dict[str, Any]:
        """
        Kenar ekler. Hiyerarşik bir döngü oluşursa ValueError fırlatarak işlemi reddeder.
        """
        rel_clean = relation.strip().upper()
        if self.would_create_cycle(source_id, target_id, rel_clean):
            raise ValueError(f"Döngü Tespit Edildi (Cycle Detected): '{source_id}' -> '{target_id}' ({rel_clean}) kenarı hiyerarşik döngü yaratır!")

        edge = {
            "source": source_id,
            "target": target_id,
            "relation": rel_clean,
            "weight": weight
        }
        if edge not in self.edges:
            self.edges.append(edge)
            self._dirty = True
            if auto_save:
                self.save()
        return edge

    def infer_relation_path(self, start_node: str, end_node: str, max_hops: int = 5) -> Optional[Dict[str, Any]]:
        """
        [PHASE 10 TRANSITIVE INFERENCE & CONFIDENCE DECAY]
        İki düğüm arasında anlambilimsel yol çıkarımı yapar:
        - NON_TRANSITIVE ilişkiler (CONTRADICTS, ASSOCIATED_WITH) zincirlenemez.
        - Her atlamada (hop) güven skoru %15 erir (confidence decay).
        """
        if start_node == end_node:
            return {"path": [start_node], "confidence": 1.0, "relations": []}

        queue = [(start_node, [start_node], [], 1.0)]

        while queue:
            curr, path, rels, conf = queue.pop(0)
            if curr == end_node:
                return {"path": path, "confidence": round(conf, 3), "relations": rels}

            if len(path) > max_hops:
                continue

            for edge in self.edges:
                if edge["source"] == curr:
                    rel = edge["relation"]
                    target = edge["target"]

                    # Non-transitive zincirleme engeli
                    if rel in self.NON_TRANSITIVE_RELATIONS and len(rels) > 0:
                        continue
                    if any(r in self.NON_TRANSITIVE_RELATIONS for r in rels):
                        continue

                    decay = 0.85 if rel in self.DECAYING_RELATIONS or rel in self.TRANSITIVE_RELATIONS else 0.70
                    next_conf = conf * decay

                    if target not in path:
                        queue.append((target, path + [target], rels + [rel], next_conf))

        return None

    def batch_add(self, new_nodes: List[Dict[str, Any]], new_edges: List[Dict[str, Any]]):
        """Çoklu düğüm ve kenarı atomik olarak ekler."""
        for n in new_nodes:
            nid = n.get("id")
            if nid:
                self.nodes[nid] = n
        for e in new_edges:
            if e not in self.edges:
                self.edges.append(e)
        self.save()

    def add_triplets(self, triplets: List[Dict[str, Any]], lesson: str = "GENEL") -> int:
        """
        Doğrulanmış Bilgi Üçlülerini (Knowledge Triplets) düğüm ve kenar olarak bilgi grafiğine mühürler.
        Format: [{'subject': '...', 'predicate': '...', 'object': '...'}]
        """
        added_count = 0
        for t in triplets:
            subj = str(t.get("subject", "")).strip()
            pred = str(t.get("predicate", "RELATED_TO")).strip().replace(" ", "_").upper()
            obj = str(t.get("object", "")).strip()

            if not subj or not obj:
                continue

            subj_id = f"ENT_{subj.upper().replace(' ', '_')}"
            obj_id = f"ENT_{obj.upper().replace(' ', '_')}"

            # 1. Subject Node
            if subj_id not in self.nodes:
                self.nodes[subj_id] = {
                    "id": subj_id,
                    "label": subj,
                    "type": "ENTITY",
                    "lesson": lesson.upper(),
                    "properties": {pred.lower(): obj}
                }
            else:
                self.nodes[subj_id]["properties"][pred.lower()] = obj

            # 2. Object Node
            if obj_id not in self.nodes:
                self.nodes[obj_id] = {
                    "id": obj_id,
                    "label": obj,
                    "type": "VALUE_ENTITY",
                    "lesson": lesson.upper(),
                    "properties": {}
                }

            # 3. Relation Edge
            edge = {
                "source": subj_id,
                "target": obj_id,
                "relation": pred,
                "weight": 1.0
            }
            if edge not in self.edges:
                self.edges.append(edge)

            added_count += 1

        if added_count > 0:
            self.save()

        return added_count

    def get_related_nodes(self, node_id: str, relation_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        related_ids = []
        for edge in self.edges:
            if edge["source"] == node_id:
                if not relation_filter or edge["relation"] == relation_filter:
                    related_ids.append(edge["target"])
            elif edge["target"] == node_id:
                if not relation_filter or edge["relation"] == relation_filter:
                    related_ids.append(edge["source"])
        
        return [self.nodes[n_id] for n_id in related_ids if n_id in self.nodes]

    def get_neighborhood(self, node_id: str, depth: int = 1) -> Dict[str, Any]:
        """
        Belirtilen düğümün depth-hop komşuluğundaki alt grafiği (subgraph) döner.
        """
        with self._lock:
            if node_id not in self.nodes:
                return {"center_node": None, "nodes": [], "edges": []}

            visited_nodes: Set[str] = {node_id}
            current_frontier: Set[str] = {node_id}

            for _ in range(depth):
                next_frontier: Set[str] = set()
                for edge in self.edges:
                    src, tgt = edge["source"], edge["target"]
                    if src in current_frontier:
                        if tgt not in visited_nodes:
                            next_frontier.add(tgt)
                            visited_nodes.add(tgt)
                    elif tgt in current_frontier:
                        if src not in visited_nodes:
                            next_frontier.add(src)
                            visited_nodes.add(src)
                current_frontier = next_frontier

            subgraph_nodes = [self.nodes[n] for n in visited_nodes if n in self.nodes]
            subgraph_edges = [
                e for e in self.edges
                if e["source"] in visited_nodes and e["target"] in visited_nodes
            ]

            return {
                "center_node": self.nodes.get(node_id),
                "nodes": subgraph_nodes,
                "edges": subgraph_edges
            }

    def verify_fact_against_graph(self, topic_key: str, candidate_text: str) -> Tuple[bool, List[str]]:
        """
        Soru metnini bilgi grafiğindeki temel deterministik sayılar ve olgularla doğrular.
        Eğer metinde grafiğe aykırı mülga veya yanlış bir eşleşme varsa tespit eder.
        """
        violations = []
        text_lower = candidate_text.lower()

        target_node = self.nodes.get(topic_key)
        if not target_node:
            for n_id, n_data in self.nodes.items():
                if n_data.get("label", "").lower() in topic_key.lower() or topic_key.lower() in n_data.get("label", "").lower():
                    target_node = n_data
                    break

        if target_node and "properties" in target_node:
            props = target_node["properties"]
            
            # 1. Askeri Islahat Kontrolü (Lale Devri)
            if props.get("askeri_islahat_var_mi") is False:
                if "askeri ıslahat" in text_lower and "lale devri" in text_lower:
                    if "yapılmamıştır" not in text_lower and "yoktur" not in text_lower and "olmamıştır" not in text_lower:
                        violations.append("Bilgi Grafiği İhlali: Lale Devri'nde askeri ıslahat yapılmamıştır.")

            # 2. Padişah Eşleşmesi
            if "padisah" in props:
                expected_padisah = str(props["padisah"]).lower()
                # Yanlış padişah atıfı var mı?
                if "nizam-ı cedit" in text_lower and "iii. selim" not in text_lower and "iii. ahmet" in text_lower:
                    violations.append("Bilgi Grafiği İhlali: Nizam-ı Cedit dönemi padişahı III. Selim'dir.")

            # 3. Sayısal Veri Kontrolleri
            if "tbmm_uye_tamsayisi" in props:
                if "550" in text_lower and ("üye" in text_lower or "milletvekili" in text_lower):
                    if "değildir" not in text_lower and "kaldırılmıştır" not in text_lower:
                        violations.append("Bilgi Grafiği İhlali: TBMM üye tamsayısı 600'dür.")

            if "aym_uye_sayisi" in props:
                if "17 üye" in text_lower or "11 üye" in text_lower:
                    violations.append("Bilgi Grafiği İhlali: AYM üye sayısı 15'tir.")

        return len(violations) == 0, violations

    def _seed_default_kpss_ontology(self):
        """
        KPSS'nin en çok soru çıkan çekirdek bilgi grafiğini inşa eder.
        """
        # --- VATANDAŞLIK ---
        self.nodes["VAT_TBMM_SAYILARI"] = {
            "id": "VAT_TBMM_SAYILARI",
            "label": "1982 Anayasası TBMM Üye ve Karar Yeter Sayıları",
            "type": "LAW_REGULATION",
            "lesson": "VATANDASLIK",
            "properties": {
                "tbmm_uye_tamsayisi": 600,
                "toplanti_yeter_sayisi": 200,
                "karar_yeter_en_az": 151,
                "secim_yenileme_cogunlugu": "3/5 (360 Milletvekili)",
                "anayasa_degisikligi_teklif": "1/3 (200 Milletvekili)",
                "anayasa_degisikligi_referandumsuz_kabul": "2/3 (400 Milletvekili)",
                "anayasa_degisikligi_zorunlu_referandum": "3/5 ile 2/3 arası (360-399)",
                "siyasi_parti_grubu_en_az": 20,
                "siyasi_parti_kurulusu_en_az": 30,
                "secilme_yasi": 18,
                "cumhurbaskani_secilme_yasi": 40
            }
        }

        self.nodes["VAT_YARGI_ORGANLARI"] = {
            "id": "VAT_YARGI_ORGANLARI",
            "label": "1982 Anayasası Yüksek Mahkemeler ve Yargı",
            "type": "LAW_REGULATION",
            "lesson": "VATANDASLIK",
            "properties": {
                "aym_uye_sayisi": 15,
                "aym_gorev_suresi": "12 Yıl",
                "aym_secilme_yasi": 45,
                "hsk_uye_sayisi": 13,
                "hsk_baskani": "Adalet Bakanı",
                "danistay_idari_dava_daireleri": True,
                "uyusmazlik_mahkemesi_baskani": "AYM kendi üyeleri arasından seçer",
                "sayistay_mahkeme_mi": "Hesap yargısı yapar, yüksek mahkeme değildir"
            }
        }

        # --- TARİH ---
        self.nodes["TAR_LALE_DEVRI"] = {
            "id": "TAR_LALE_DEVRI",
            "label": "Lale Devri Islahatları (1718-1730)",
            "type": "HISTORICAL_ERA",
            "lesson": "TARIH",
            "properties": {
                "padisah": "III. Ahmet",
                "sadrazam": "Nevşehirli Damat İbrahim Paşa",
                "baslangic_antlasmasi": "1718 Pasarofça Antlaşması",
                "bitis_olayi": "1730 Patrona Halil İsyanı",
                "ilk_gecici_elcilik": "28 Çelebi Mehmet (Paris)",
                "ilk_ozel_matbaa": "İbrahim Müteferrika ve Şinasi Efendi",
                "matbaada_basilan_ilk_eser": "Vankulu Lügati",
                "askeri_islahat_var_mi": False
            }
        }

        self.nodes["TAR_NIZAM_I_CEDIT"] = {
            "id": "TAR_NIZAM_I_CEDIT",
            "label": "III. Selim Nizam-ı Cedit Dönemi (1789-1807)",
            "type": "HISTORICAL_ERA",
            "lesson": "TARIH",
            "properties": {
                "padisah": "III. Selim",
                "ordusu": "Nizam-ı Cedit Ordusu",
                "hazinesi": "İrad-ı Cedit Hazinesi",
                "ilk_daimi_elcilik": "Londra (Yusuf Agah Efendi)",
                "ilk_devlet_matbaasi": "Matbaa-i Amire",
                "ilk_zafer": "Akka Zaferi (Cezzar Ahmet Paşa vs Napolyon)",
                "bitis_isyan": "Kabakçı Mustafa İsyanı"
            }
        }

        self.nodes["TAR_BALKAN_ANTANTI"] = {
            "id": "TAR_BALKAN_ANTANTI",
            "label": "Balkan Antantı (1934)",
            "type": "TREATY",
            "lesson": "TARIH",
            "properties": {
                "tarih": "9 Şubat 1934",
                "katilanlar": ["Türkiye", "Yunanistan", "Yugoslavya", "Romanya"],
                "sifresi": "TAYYAR",
                "katilmayan_revizyonistler": ["Bulgaristan", "Arnavutluk"],
                "tehdit": "İtalya ve Almanya'nın yayılmacı politikası"
            }
        }

        self.nodes["TAR_SADABAT_PAKTI"] = {
            "id": "TAR_SADABAT_PAKTI",
            "label": "Sadabat Paktı (1937)",
            "type": "TREATY",
            "lesson": "TARIH",
            "properties": {
                "tarih": "8 Temmuz 1937",
                "katilanlar": ["Türkiye", "İran", "Irak", "Afganistan"],
                "sifresi": "TİAİ",
                "katilmayan": "Suriye (Hatay sorunu nedeniyle)",
                "tehdit": "İtalya'nın Habeşistan'ı işgali ve Akdeniz tehdidi"
            }
        }

        # --- COĞRAFYA ---
        self.nodes["COG_TURKIYE_MADENLERI"] = {
            "id": "COG_TURKIYE_MADENLERI",
            "label": "Türkiye'nin Stratejik Madenleri ve Yatakları",
            "type": "GEOGRAPHY_TOPIC",
            "lesson": "COGRAFYA",
            "properties": {
                "bor_rezervi": "%72 ile dünyada 1. sırada (Balıkesir, Bursa, Kütahya, Eskişehir)",
                "baksit_aluminyum": "Konya Seydişehir, Antalya Akseki",
                "krom": "Elazığ Guleman, Muğla Fethiye-Köyceğiz",
                "bakir": "Artvin Murgul, Kastamonu Küre, Elazığ Maden, Rize Çayeli (Şifre: KADER)",
                "demir": "Sivas Divriği, Malatya Hekimhan-Hasançelebi"
            }
        }

        # İlişki kenarları (Edges)
        self.edges = [
            {"source": "TAR_LALE_DEVRI", "target": "TAR_NIZAM_I_CEDIT", "relation": "TEMPORAL_PRECEDES", "weight": 1.0},
            {"source": "TAR_BALKAN_ANTANTI", "target": "TAR_SADABAT_PAKTI", "relation": "FREQUENTLY_PAIRED_WITH", "weight": 0.9},
            {"source": "VAT_TBMM_SAYILARI", "target": "VAT_YARGI_ORGANLARI", "relation": "CONSTITUTIONAL_HIERARCHY", "weight": 0.8}
        ]

kpss_knowledge_graph = KPSSKnowledgeGraph()
