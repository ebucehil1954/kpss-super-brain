"""
KPSS Super-Brain: Beceriler ve Pedagojik Stratejiler Kütüphanesi (Skill Library)
Soru çözme yöntemleri, akrostiş şablonları, hoca teknikleri ve ÖSYM soru çözme algoritmaları.
"""
import os
import json
from typing import Dict, Any, List, Optional
from config import super_brain_config

class SkillLibrary:
    def __init__(self, storage_file: Optional[str] = None):
        self.storage_file = storage_file or os.path.join(super_brain_config.DATA_DIR, "skill_library.json")
        self.skills: Dict[str, Dict[str, Any]] = {}
        self._load_or_seed()

    def _load_or_seed(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self.skills = json.load(f)
                    return
            except Exception:
                pass
        self._seed_default_skills()
        self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(self.skills, f, ensure_ascii=False, indent=2)

    def add_skill(self, skill_id: str, title: str, category: str, description: str, steps: List[str], examples: List[Dict[str, Any]]):
        self.skills[skill_id] = {
            "id": skill_id,
            "title": title,
            "category": category, # "QUESTION_SOLVING", "MNEMONIC_GENERATION", "DISTRACTOR_ELIMINATION", "TEACHER_HEURISTIC"
            "description": description,
            "steps": steps,
            "examples": examples
        }
        self.save()

    def get_skills_by_category(self, category: str) -> List[Dict[str, Any]]:
        return [s for s in self.skills.values() if s.get("category") == category]

    def _seed_default_skills(self):
        self.skills["SKILL_ELIMINATE_EXTREMES"] = {
            "id": "SKILL_ELIMINATE_EXTREMES",
            "title": "Keskin İfadeleri Eleme Tekniği",
            "category": "DISTRACTOR_ELIMINATION",
            "description": "ÖSYM sorularında 'sadece', 'yalnızca', 'hiçbir zaman', 'kesinlikle' gibi keskin ifadeler genellikle yanlıştır.",
            "steps": [
                "1. Seçenekteki mutlak/keskin kısıtlayıcı sözcükleri (sadece, asla, yalnızca) tespit et.",
                "2. İstisnaların varlığını kontrol et.",
                "3. İstisna varsa seçeneği çeldirici olarak işaretle."
            ],
            "examples": []
        }

        self.skills["SKILL_CHRONOLOGY_ANCHORS"] = {
            "id": "SKILL_CHRONOLOGY_ANCHORS",
            "title": "Tarihsel Çıpa Olaylar ile Kronoloji Çözümü",
            "category": "QUESTION_SOLVING",
            "description": "Bilinmeyen olayları 1919 Samsun, 1920 TBMM, 1923 Cumhuriyet ve 1930 Serbest Fırka çıpalarına göre sıralama.",
            "steps": [
                "1. Verilen olayları bilinen 4 ana dönüm noktasına yerleştir.",
                "2. Mantıksal sebep-sonuç bağını kur."
            ],
            "examples": []
        }

        self.skills["SKILL_RAMAZAN_YETGIN_STYLE"] = {
            "id": "SKILL_RAMAZAN_YETGIN_STYLE",
            "title": "Ramazan Yetgin ÖSYM Bakış Açısı Heuristiği",
            "category": "TEACHER_HEURISTIC",
            "description": "ÖSYM'nin son yıllarda soru sormadığı ama müfredatta bekleyen ıslahatlar ve ilkler üzerine odaklanma.",
            "steps": [
                "1. 'ÖSYM bunu daha önce sormadı ama sorabilir' dediği vurguları filtrele.",
                "2. Konu anlatımındaki soru tahminlerini vektör bellekle eşleştir."
            ],
            "examples": []
        }

skill_library = SkillLibrary()
