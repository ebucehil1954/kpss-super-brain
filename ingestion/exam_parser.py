"""
KPSS Super-Brain V1.5: Sınav ve Soru Ayrıştırıcı (Exam & Question Parser)
Çok sütunlu soru sınır tespiti, kök/öncül/seçenek ayrıştırma ve eksiksiz seçenek garantisi.
"""
import re
import json
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from brain.models import (
    ExamRecord,
    QuestionRecord,
    QuestionOptionRecord
)
from brain.database import db_session, initialize_database
from curriculum.document_classifier import document_classifier

logger = logging.getLogger("exam_parser")


class ExamParsingError(Exception):
    """Sınav ayrıştırma hatası."""
    pass


class ExamParser:
    """
    V1.5 Sınav Kitapçığı ve Soru Segmentasyon Motoru.
    Her soru için 5 seçeneğin (A, B, C, D, E) eksiksiz çıkarılmasını ve sayfa bağını garanti eder.
    """

    QUESTION_HEADER_PATTERN = re.compile(
        r'(?:^|\n\s*)(?:Soru\s+)?(\d{1,3})[\.\-\)]\s*',
        re.IGNORECASE
    )

    OPTION_PATTERN = re.compile(
        r'(?:^|\n|\s+)([A-Ea-e])[\)\.\-]\s*([^\n\r]+(?:\n(?![A-Ea-e][\)\.\-]|\d{1,3}[\.\-\)])[^\n\r]+)*)',
        re.MULTILINE
    )

    NEGATIVE_KEYWORDS = [
        "değildir", "degildir", "yoktur", "ulaşılamaz", "ulasilamaz", "savunulamaz", "gösterilemez", "gosterilemez",
        "hangisi söylenemez", "hangisi soylenemez", "söylenemez", "soylenemez", "yer almaz", "beklenemez", "çıkarılamaz", "cikarilamaz", "yanlıştır", "yanlistir"
    ]

    ROMAN_NUMERAL_PATTERN = re.compile(
        r'(?:^|\n)\s*(I{1,3}|IV|V|VI)\.\s*([^\n\r]+)',
        re.MULTILINE
    )

    def __init__(self):
        initialize_database()

    def create_or_get_exam(
        self,
        exam_id: str,
        exam_name: str,
        exam_code: str,
        year: int,
        document_id: Optional[str] = None
    ) -> ExamRecord:
        """Sınav kaydını oluşturur veya mevcut olanı döner."""
        now_str = datetime.now().isoformat()
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM v15_exams WHERE exam_id = ?", (exam_id,))
            row = cursor.fetchone()
            if row:
                return ExamRecord(**dict(row))

            cursor.execute("""
            INSERT INTO v15_exams (
                exam_id, document_id, exam_name, exam_code, year,
                total_questions, has_official_key, created_at
            ) VALUES (?, ?, ?, ?, ?, 0, 0, ?)
            """, (exam_id, document_id, exam_name, exam_code, year, now_str))

        return ExamRecord(
            exam_id=exam_id,
            document_id=document_id,
            exam_name=exam_name,
            exam_code=exam_code,
            year=year,
            total_questions=0,
            has_official_key=False,
            created_at=now_str
        )

    def parse_question_block(
        self,
        block_text: str,
        question_num: int,
        exam_id: str,
        document_id: str,
        page_number: int,
        default_lesson: str = "TARIH"
    ) -> QuestionRecord:
        """
        Tek bir soru metin bloğunu kök, öncüller ve A-E seçeneklerine ayırır.
        """
        now_str = datetime.now().isoformat()
        question_id = f"q_{exam_id}_{question_num}"

        # 1. Öncülleri (I., II., III.) tespit et
        premises = []
        for match in self.ROMAN_NUMERAL_PATTERN.finditer(block_text):
            premises.append(f"{match.group(1)}. {match.group(2).strip()}")

        # 2. Seçenekleri (A-E) tespit et
        options_dict: Dict[str, str] = {}
        # Seçenek bloklarını bul
        opt_matches = list(self.OPTION_PATTERN.finditer(block_text))
        
        stem_end_idx = len(block_text)
        if opt_matches:
            stem_end_idx = opt_matches[0].start()

        for m in opt_matches:
            key = m.group(1).upper()
            text = m.group(2).strip()
            # Sonraki seçeneğin başlangıcını temizle
            text = re.sub(r'\s+[A-E][\)\.\-].*$', '', text, flags=re.DOTALL).strip()
            options_dict[key] = text

        # 3. Kök ve Paragraf Metnini Ayıkla
        stem_raw = block_text[:stem_end_idx].strip()
        # Soru numarasını baştan temizle
        stem_clean = re.sub(r'^(?:Soru\s+)?\d{1,3}[\.\-\)]\s*', '', stem_raw, flags=re.IGNORECASE).strip()

        # 4. Olumsuzluk tespiti
        is_negative = any(neg in stem_clean.lower() for neg in self.NEGATIVE_KEYWORDS)

        # 5. Müfredat Konusu Çözümleme
        lesson, topic, _ = document_classifier.map_curriculum_topic(
            text_sample=f"{stem_clean} {' '.join(options_dict.values())}",
            explicit_lesson=default_lesson
        )

        # 6. Eksiksiz Seçenek Kontrolü
        required_keys = ["A", "B", "C", "D", "E"]
        has_all_options = all(k in options_dict for k in required_keys)
        extraction_status = "COMPLETE" if has_all_options else "EXTRACTION_INCOMPLETE"

        # QuestionOptionRecord Listesini Oluştur
        option_records: List[QuestionOptionRecord] = []
        for opt_key in sorted(options_dict.keys()):
            opt_id = f"opt_{question_id}_{opt_key}"
            option_records.append(
                QuestionOptionRecord(
                    option_id=opt_id,
                    question_id=question_id,
                    option_key=opt_key,
                    option_text=options_dict[opt_key],
                    is_correct_official=False,
                    created_at=now_str
                )
            )

        return QuestionRecord(
            question_id=question_id,
            exam_id=exam_id,
            document_id=document_id,
            page_number=page_number,
            question_number_in_exam=question_num,
            lesson=lesson if lesson != "UNKNOWN" else default_lesson,
            topic_id=topic,
            stem_text=stem_clean,
            passage_text=None,
            premises=premises,
            is_negative=is_negative,
            extraction_status=extraction_status,
            options=option_records,
            created_at=now_str
        )

    def parse_page_questions(
        self,
        page_text: str,
        exam_id: str,
        document_id: str,
        page_number: int,
        default_lesson: str = "TARIH"
    ) -> List[QuestionRecord]:
        """
        Bir sayfa içindeki tüm soruları tespit eder ve veritabanına yazar.
        """
        # Soru başlıklarının indekslerini bul
        matches = list(self.QUESTION_HEADER_PATTERN.finditer(page_text))
        if not matches:
            return []

        questions: List[QuestionRecord] = []

        for i, match in enumerate(matches):
            q_num = int(match.group(1))
            start_idx = match.start()
            end_idx = matches[i + 1].start() if (i + 1) < len(matches) else len(page_text)
            block_text = page_text[start_idx:end_idx].strip()

            q_record = self.parse_question_block(
                block_text=block_text,
                question_num=q_num,
                exam_id=exam_id,
                document_id=document_id,
                page_number=page_number,
                default_lesson=default_lesson
            )
            questions.append(q_record)

        # Veritabanına Soruları ve Seçenekleri Kaydet
        with db_session() as conn:
            cursor = conn.cursor()
            for q in questions:
                cursor.execute("""
                INSERT INTO v15_questions (
                    question_id, exam_id, document_id, page_number,
                    question_number_in_exam, lesson, topic_id, stem_text,
                    passage_text, premises_json, is_negative, extraction_status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_id, question_number_in_exam) DO UPDATE SET
                    stem_text = excluded.stem_text,
                    topic_id = excluded.topic_id,
                    premises_json = excluded.premises_json,
                    is_negative = excluded.is_negative,
                    extraction_status = excluded.extraction_status
                """, (
                    q.question_id,
                    q.exam_id,
                    q.document_id,
                    q.page_number,
                    q.question_number_in_exam,
                    q.lesson,
                    q.topic_id,
                    q.stem_text,
                    q.passage_text,
                    json.dumps(q.premises, ensure_ascii=False),
                    1 if q.is_negative else 0,
                    q.extraction_status,
                    q.created_at
                ))

                # Seçenekleri Kaydet
                for opt in q.options:
                    cursor.execute("""
                    INSERT INTO v15_question_options (
                        option_id, question_id, option_key, option_text,
                        is_correct_official, is_trap, trap_type, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(question_id, option_key) DO UPDATE SET
                        option_text = excluded.option_text
                    """, (
                        opt.option_id,
                        opt.question_id,
                        opt.option_key,
                        opt.option_text,
                        1 if opt.is_correct_official else 0,
                        1 if opt.is_trap else 0,
                        opt.trap_type,
                        opt.created_at
                    ))

            # Sınav soru sayısını güncelle
            cursor.execute("""
            UPDATE v15_exams
            SET total_questions = (SELECT COUNT(*) FROM v15_questions WHERE exam_id = ?)
            WHERE exam_id = ?
            """, (exam_id, exam_id))

        return questions

    def parse_exam_document(
        self,
        document_id: str,
        exam_id: Optional[str] = None,
        exam_name: Optional[str] = None,
        exam_code: Optional[str] = None,
        year: Optional[int] = None,
        default_lesson: str = "TARIH",
        auto_link_patterns: bool = True
    ) -> List[QuestionRecord]:
        """
        v15_document_pages tablosundaki tüm sayfaları sıralı okuyarak sınav sorularını ve seçeneklerini ayıklar.
        İsteğe bağlı olarak soru kalıplarını (pattern_classifier) otomatik bağlar.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM v15_documents WHERE document_id = ?", (document_id,))
            doc_row = cursor.fetchone()

        if not doc_row:
            raise ExamParsingError(f"Doküman bulunamadı: {document_id}")

        e_code = exam_code or doc_row["exam_code"] or "KPSS_LISANS"
        e_year = year or doc_row["year"] or datetime.now().year
        e_name = exam_name or doc_row["filename"]
        e_id = exam_id or f"exam_{document_id}"

        exam = self.create_or_get_exam(
            exam_id=e_id,
            exam_name=e_name,
            exam_code=e_code,
            year=e_year,
            document_id=document_id
        )

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT page_number, cleaned_text, raw_text
            FROM v15_document_pages
            WHERE document_id = ?
            ORDER BY page_number ASC
            """, (document_id,))
            pages = cursor.fetchall()

        all_questions: List[QuestionRecord] = []
        for page in pages:
            page_text = page["cleaned_text"] or page["raw_text"] or ""
            if not page_text.strip():
                continue

            page_questions = self.parse_page_questions(
                page_text=page_text,
                exam_id=exam.exam_id,
                document_id=document_id,
                page_number=page["page_number"],
                default_lesson=default_lesson
            )
            all_questions.extend(page_questions)

        if auto_link_patterns and all_questions:
            from cognition.pattern_classifier import pattern_classifier
            for q in all_questions:
                pattern_classifier.link_question_to_patterns(
                    question_id=q.question_id,
                    stem_text=q.stem_text,
                    premises=q.premises,
                    is_negative=q.is_negative
                )

        return all_questions


exam_parser = ExamParser()
