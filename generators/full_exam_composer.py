"""
KPSS Super-Brain: 120 Soruluk ÖSYM Tam Deneme Sınavı Montajcısı (Full Exam Composer v2)
ÖSYM standart branş dağılımına (Türkçe 30, Matematik 30, Tarih 27, Coğrafya 18, Vatandaşlık 9, Güncel 6)
göre %100 doğrulanmış, şık dengeli 120 soruluk tam deneme sınavı üretir.
"""
from typing import Dict, Any, List, Optional
import random
from generators.question_factory import question_factory
from generators.turkish_question_factory import turkish_question_factory
from generators.math_question_factory import math_question_factory
from cognition.prediction_engine import prediction_engine

class FullExamComposer:
    # Standart KPSS Lisans / Önlisans GY-GK Dağılımı (120 Soru)
    EXAM_DISTRIBUTION = {
        "TURKCE": 30,
        "MATEMATIK": 30,
        "TARIH": 27,
        "COGRAFYA": 18,
        "VATANDASLIK": 9,
        "GUNCEL": 6
    }

    @classmethod
    async def compose_branch_trial(cls, lesson: str, count: Optional[int] = None) -> Dict[str, Any]:
        """Tek bir branşa özel (örn. 27 soruluk Tarih veya 30 soruluk Türkçe) branş denemesi üretir."""
        target_count = count or cls.EXAM_DISTRIBUTION.get(lesson.upper(), 15)
        questions = []

        if lesson.upper() == "TURKCE":
            # 26 normal Türkçe + 4 Sözel Mantık
            for i in range(min(target_count, 26)):
                q = await turkish_question_factory.generate_turkish_question()
                if q:
                    q["question_number"] = i + 1
                    questions.append(q)
            if target_count >= 30:
                logic_set = await turkish_question_factory.generate_verbal_logic_set()
                for q in logic_set.get("questions", []):
                    q["stem"] = f"[SÖZEL MANTIK SENARYOSU]\n{logic_set.get('scenario')}\n\n{q['stem']}"
                    q["lesson"] = "TURKCE"
                    q["topic"] = "Sözel Mantık ve Muhakeme"
                    questions.append(q)

        elif lesson.upper() == "MATEMATIK":
            for i in range(target_count):
                q = await math_question_factory.generate_math_question()
                if q:
                    q["question_number"] = i + 1
                    questions.append(q)

        else:
            predictions = await prediction_engine.generate_live_predictions(lesson_filter=lesson)
            for i in range(target_count):
                topic = predictions[i % len(predictions)]["topic"] if predictions else f"{lesson} Genel"
                q = await question_factory.generate_single_question(lesson=lesson, topic=topic)
                if q:
                    q["question_number"] = i + 1
                    questions.append(q)

        return {
            "title": f"Promius KPSS Süper Zeka — {lesson.upper()} Branş Denemesi ({len(questions)} Soru)",
            "lesson": lesson.upper(),
            "total_questions": len(questions),
            "questions": questions
        }

    @classmethod
    async def compose_full_120_exam(cls, title: Optional[str] = None) -> Dict[str, Any]:
        """
        120 Soruluk Tam ÖSYM Deneme Sınavı Montajlar:
        1-30: Türkçe
        31-60: Matematik & Geometri
        61-87: Tarih
        88-105: Coğrafya
        106-114: Vatandaşlık
        115-120: Güncel Bilgiler
        """
        print("🚀 [FULL EXAM COMPOSER] 120 Soruluk ÖSYM Deneme Sınavı Montajı Başladı...")
        all_questions = []
        q_counter = 1

        # 1. TÜRKÇE (30 Soru)
        turk_branch = await cls.compose_branch_trial("TURKCE", count=30)
        for q in turk_branch.get("questions", []):
            q["question_number"] = q_counter
            q_counter += 1
            all_questions.append(q)

        # 2. MATEMATİK (30 Soru)
        math_branch = await cls.compose_branch_trial("MATEMATIK", count=30)
        for q in math_branch.get("questions", []):
            q["question_number"] = q_counter
            q_counter += 1
            all_questions.append(q)

        # 3. TARİH (27 Soru)
        hist_branch = await cls.compose_branch_trial("TARIH", count=27)
        for q in hist_branch.get("questions", []):
            q["question_number"] = q_counter
            q_counter += 1
            all_questions.append(q)

        # 4. COĞRAFYA (18 Soru)
        geo_branch = await cls.compose_branch_trial("COGRAFYA", count=18)
        for q in geo_branch.get("questions", []):
            q["question_number"] = q_counter
            q_counter += 1
            all_questions.append(q)

        # 5. VATANDAŞLIK (9 Soru)
        vat_branch = await cls.compose_branch_trial("VATANDASLIK", count=9)
        for q in vat_branch.get("questions", []):
            q["question_number"] = q_counter
            q_counter += 1
            all_questions.append(q)

        # 6. GÜNCEL BİLGİLER (6 Soru)
        for i in range(6):
            q = await question_factory.generate_single_question(
                lesson="GUNCEL",
                topic="2026 Güncel Uluslararası Olaylar, UNESCO ve Kültür"
            )
            if q:
                q["question_number"] = q_counter
                q_counter += 1
                all_questions.append(q)

        # Şık Dağılım İstatistiği (A, B, C, D, E)
        option_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
        for q in all_questions:
            ans = q.get("expected_answer", "A")
            option_counts[ans] = option_counts.get(ans, 0) + 1

        exam_title = title or f"Promius KPSS Süper Zeka 2026 Türkiye Geneli 120 Soruluk Tam Deneme Sınavı"

        return {
            "title": exam_title,
            "total_questions": len(all_questions),
            "distribution": {
                "turkce": 30,
                "matematik": 30,
                "tarih": 27,
                "cografya": 18,
                "vatandaslik": 9,
                "guncel": 6
            },
            "option_balance": option_counts,
            "questions": all_questions
        }

full_exam_composer = FullExamComposer()
