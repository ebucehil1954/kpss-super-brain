"""
KPSS Super-Brain: Çıkmış Soru ve Soru Bankası İçe Aktarıcı (Exam Scraper)
Geçmiş yılların ÖSYM sorularını analiz edilebilir standart JSON formatına dönüştürür.
"""
import os
import json
import re
from typing import List, Dict, Any, Optional
from config import super_brain_config
from brain.vector_memory import vector_memory

class ExamScraper:
    @staticmethod
    def parse_raw_question_text(raw_text: str, lesson: str = "TARIH", default_year: int = 2024) -> List[Dict[str, Any]]:
        """
        Ham metinden 5 şıklı ÖSYM soru bloklarını ayıklar.
        """
        questions = []
        # Örnek regex ile soru ayıklama
        blocks = re.split(r'\n(?=\d+[\.\)]\s+)', raw_text)
        
        for idx, b in enumerate(blocks):
            if not b.strip():
                continue
            
            # Şıkları yakala
            options = {}
            opt_matches = re.findall(r'([A-E])\)\s*([^\n]+)', b)
            for opt_char, opt_val in opt_matches:
                options[opt_char.upper()] = opt_val.strip()

            if len(options) >= 4:
                # Soru kökünü şıklardan önceki kısım olarak al
                stem_match = re.split(r'A\)', b)[0]
                stem = re.sub(r'^\d+[\.\)]\s*', '', stem_match).strip()
                
                questions.append({
                    "id": f"kpss_q_{default_year}_{idx+1}",
                    "year": default_year,
                    "lesson": lesson,
                    "topic": "KPSS Çıkmış Soru",
                    "stem": stem,
                    "options": options,
                    "expected_answer": "A", # Varsayılan
                    "raw_block": b
                })
                
        return questions

    @classmethod
    def load_past_exam_dataset(cls) -> List[Dict[str, Any]]:
        """
        `data/past_exams/` altındaki tüm JSON dosyalarını yükler.
        """
        dataset = []
        folder = super_brain_config.PAST_EXAMS_DIR
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.endswith(".json"):
                    try:
                        with open(os.path.join(folder, file), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                dataset.extend(data)
                            elif isinstance(data, dict):
                                dataset.append(data)
                    except Exception:
                        pass
        return dataset

exam_scraper = ExamScraper()
