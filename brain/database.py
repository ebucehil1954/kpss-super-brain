"""
KPSS Super-Brain: Ana SQLite Veritabanı ve Şema Yönetimi
WAL modunda, eşzamanlı okuma-yazmaya dayanıklı, FTS5 destekli kalıcı zihin ambarı.
"""
import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime
from config import super_brain_config

DB_PATH = str(super_brain_config.BRAIN_DB_FILE)

def get_db_connection(max_retries: int = 3, retry_delay: float = 0.5):
    """SQLite bağlantısını oluşturur, kilitlenmelerde retry uygular ve WAL modunu aktif eder."""
    import time as _time
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    last_error = None
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            return conn
        except sqlite3.OperationalError as e:
            last_error = e
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                _time.sleep(retry_delay * (attempt + 1))
                continue
            raise
    if last_error:
        raise last_error

@contextmanager
def db_session():
    """
    SQLite bağlantı context manager'ı.
    WAL modunda kilitlenmelere karşı bağlantı ve commit seviyesinde retry uygular.
    """
    import time as _time
    conn = get_db_connection()
    try:
        yield conn
        # Commit aşamasında database is locked retry'ı
        committed = False
        for attempt in range(3):
            try:
                conn.commit()
                committed = True
                break
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < 2:
                    _time.sleep(0.3 * (attempt + 1))
                    continue
                raise
        if not committed:
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass

def initialize_database():
    """Tüm tabloları ve FTS indekslerini oluşturur."""
    with db_session() as conn:
        cursor = conn.cursor()
        
        # 1. BİLGİ KAYITLARI TABLOSU (Knowledge Records)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_records (
            record_id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            record_type TEXT NOT NULL, -- FACT, REASONING, PATTERN, TRAP, MNEMONIC, TEACHER_INSIGHT
            lesson TEXT NOT NULL,
            topic TEXT NOT NULL,
            subtopic TEXT DEFAULT '',
            confidence REAL DEFAULT 0.95,
            source_chain_json TEXT NOT NULL DEFAULT '[]',
            related_records_json TEXT NOT NULL DEFAULT '[]',
            times_reinforced INTEGER DEFAULT 1,
            first_learned TEXT NOT NULL,
            last_reinforced TEXT NOT NULL,
            tags_json TEXT NOT NULL DEFAULT '[]'
        );
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kr_lesson ON knowledge_records(lesson);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kr_topic ON knowledge_records(topic);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kr_type ON knowledge_records(record_type);")
        
        # FTS5 Full-Text Search
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
            record_id UNINDEXED,
            text,
            lesson,
            topic,
            subtopic,
            tokenize='unicode61 remove_diacritics 2'
        );
        """)

        # 2. MANTIK ZİNCİRLERİ (Reasoning Chains)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reasoning_chains (
            chain_id TEXT PRIMARY KEY,
            chain_type TEXT NOT NULL, -- QUESTION_SOLVING, ELIMINATION, CHRONOLOGICAL, ANOMALY_DETECTION
            lesson TEXT NOT NULL,
            topic TEXT NOT NULL,
            description TEXT NOT NULL,
            steps_json TEXT NOT NULL DEFAULT '[]',
            learned_from_json TEXT NOT NULL DEFAULT '[]',
            teacher_source TEXT NOT NULL DEFAULT 'GENEL',
            times_applied INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rc_lesson ON reasoning_chains(lesson);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rc_topic ON reasoning_chains(topic);")

        # 3. ÖĞRETMEN ZİHİN PROFİLLERİ (Videolardan Dinamik Öğrenilen)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_profiles (
            teacher_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            channel TEXT NOT NULL,
            lesson TEXT NOT NULL,
            videos_watched INTEGER DEFAULT 0,
            total_transcript_words INTEGER DEFAULT 0,
            teaching_patterns_json TEXT NOT NULL DEFAULT '{}',
            favorite_topics_json TEXT NOT NULL DEFAULT '[]',
            mnemonics_used_json TEXT NOT NULL DEFAULT '[]',
            prediction_history_json TEXT NOT NULL DEFAULT '[]',
            reasoning_chains_count INTEGER DEFAULT 0,
            unique_facts_count INTEGER DEFAULT 0,
            trap_warnings_count INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        """)

        # 4. VİDEO İZLEME VE TÜKETİM KUYRUĞU
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_queue (
            video_id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            channel TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            lesson TEXT NOT NULL,
            topic TEXT NOT NULL,
            duration_seconds INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSING, WATCHED, NO_TRANSCRIPT, FAILED
            priority INTEGER DEFAULT 10,           -- 1 (düşük) - 100 (en yüksek)
            retry_count INTEGER DEFAULT 0,
            transcript_length INTEGER DEFAULT 0,
            chunks_extracted INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            watched_at TEXT,
            error_message TEXT
        );
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vq_status ON video_queue(status, priority DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vq_teacher ON video_queue(teacher_name);")

        # 4B. TRANSCRIPT SAĞLAYICI DENEME TEŞHİS GÜNLÜĞÜ (Transcript Provider Attempts)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcript_provider_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            attempt_number INTEGER DEFAULT 1,
            status TEXT NOT NULL,
            error_code TEXT,
            error_message TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            duration_ms INTEGER DEFAULT 0
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tpa_vid ON transcript_provider_attempts(video_id);")

        # 5. EPİZODİK ÖĞRENME GÜNLÜĞÜ (Activity & Episode Journal)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL, -- VIDEO_DIGEST, WEB_RESEARCH, REASONING_SYNTHESIS, SELF_EVAL, CONSOLIDATION
            lesson TEXT NOT NULL,
            topic TEXT NOT NULL,
            teacher TEXT DEFAULT 'Sistem',
            summary TEXT NOT NULL,
            confidence_gain REAL DEFAULT 0.05,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_le_created ON learning_events(created_at DESC);")

        # 6. SINAV KALIPLARI VE TUZAKLAR (Exam Patterns & Traps)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_patterns (
            pattern_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lesson TEXT NOT NULL,
            topic TEXT NOT NULL,
            frequency_analysis TEXT NOT NULL,
            solving_strategy TEXT NOT NULL,
            common_traps_json TEXT NOT NULL DEFAULT '[]',
            teacher_tips_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        # 7. RESMİ MÜFREDAT VE KONU HAKİMİYET MATRİSİ (Topic Mastery Matrix)
        # Her konu için en az 3-4 video kuralını deterministik olarak takip eder.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS topic_mastery (
            topic_id TEXT PRIMARY KEY,
            lesson TEXT NOT NULL,
            topic_name TEXT NOT NULL,
            target_videos_count INTEGER DEFAULT 4,
            consumed_videos_count INTEGER DEFAULT 0,
            distinct_teachers_json TEXT NOT NULL DEFAULT '[]',
            distinct_channels_json TEXT NOT NULL DEFAULT '[]',
            consumed_video_ids_json TEXT NOT NULL DEFAULT '[]',
            facts_count INTEGER DEFAULT 0,
            traps_count INTEGER DEFAULT 0,
            reasoning_count INTEGER DEFAULT 0,
            mnemonics_count INTEGER DEFAULT 0,
            mastery_stage TEXT NOT NULL DEFAULT 'UNSTARTED', -- UNSTARTED (0/4), STARTED (1/4), DEVELOPING (2/4), SYNTHESIZING (3/4), MASTERED (4+/4)
            is_mastered INTEGER DEFAULT 0,
            last_digested_at TEXT,
            updated_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tm_lesson ON topic_mastery(lesson);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tm_stage ON topic_mastery(mastery_stage);")

        # 8. ÇOKLU HOCA KARŞILAŞTIRMALI UZMAN SENTEZLERİ (Expert Syntheses)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS expert_syntheses (
            synthesis_id TEXT PRIMARY KEY,
            lesson TEXT NOT NULL,
            topic TEXT NOT NULL,
            teachers_involved_json TEXT NOT NULL DEFAULT '[]',
            video_ids_json TEXT NOT NULL DEFAULT '[]',
            consensus_facts_json TEXT NOT NULL DEFAULT '[]',
            teacher_insights_json TEXT NOT NULL DEFAULT '[]',
            unified_traps_json TEXT NOT NULL DEFAULT '[]',
            consolidated_mnemonics_json TEXT NOT NULL DEFAULT '[]',
            master_summary TEXT NOT NULL,
            synthesis_score REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_es_topic ON expert_syntheses(lesson, topic);")

        # 9. MANUS YOUTUBE KEŞİF RADARI VE KANAL LİSTESİ (Discovered Channels & Playlists)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS discovered_channels_playlists (
            item_id TEXT PRIMARY KEY,
            item_type TEXT NOT NULL, -- CHANNEL, PLAYLIST, COURSE_SERIES, GENERAL_REVIEW
            channel_name TEXT NOT NULL,
            channel_handle TEXT DEFAULT '',
            title TEXT NOT NULL,
            playlist_id TEXT DEFAULT '',
            video_count INTEGER DEFAULT 0,
            lesson TEXT NOT NULL,
            target_topics_json TEXT NOT NULL DEFAULT '[]',
            url TEXT NOT NULL,
            discovered_at TEXT NOT NULL,
            last_scanned_at TEXT
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dcp_lesson ON discovered_channels_playlists(lesson);")

        # 10. KANONİK KAYNAKLAR (Canonical Sources)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL, -- YOUTUBE_TRANSCRIPT, YOUTUBE_AUDIO_WHISPER, WEB_PAGE, OFFICIAL_LEGISLATION, TUIK_MTA_STATISTICS, PDF_DOCUMENT
            title TEXT NOT NULL,
            url TEXT,
            author_or_teacher TEXT DEFAULT 'Bilinmiyor',
            institution_or_channel TEXT,
            published_at TEXT,
            reliability_score REAL DEFAULT 0.85,
            provenance_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_src_type ON sources(source_type);")

        # 11. TRANSKRİPT SEGMENTLERİ (Transcript Segments with Timestamps)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcript_segments (
            segment_id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL,
            start_seconds REAL NOT NULL,
            end_seconds REAL NOT NULL,
            text TEXT NOT NULL,
            segment_hash TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ts_video ON transcript_segments(video_id);")

        # 12. ATOMİK İDDİALAR VE KANITLAR (Atomic Claims & Provenance)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS atomic_claims (
            claim_id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            lesson TEXT NOT NULL,
            topic TEXT NOT NULL,
            subtopic TEXT DEFAULT '',
            claim_type TEXT NOT NULL, -- FACT, DEFINITION, LEGAL_RULE, DATE, NUMBER, MNEMONIC, TRAP, etc.
            subject TEXT,
            predicate TEXT,
            object_val TEXT,
            evidence_refs_json TEXT NOT NULL DEFAULT '[]',
            confidence REAL DEFAULT 0.90,
            temporal_status TEXT NOT NULL DEFAULT 'ACTIVE',
            verification_status TEXT NOT NULL DEFAULT 'PENDING',
            tags_json TEXT NOT NULL DEFAULT '[]',
            provenance_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ac_topic ON atomic_claims(lesson, topic);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ac_type ON atomic_claims(claim_type);")

        # 13. ÇELİŞKİ KAYITLARI (Contradiction Records)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contradictions (
            contradiction_id TEXT PRIMARY KEY,
            lesson TEXT NOT NULL,
            topic TEXT NOT NULL,
            claim_a_id TEXT NOT NULL,
            claim_a_text TEXT NOT NULL,
            claim_a_source TEXT NOT NULL,
            claim_b_id TEXT NOT NULL,
            claim_b_text TEXT NOT NULL,
            claim_b_source TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'HIGH', -- HIGH, MEDIUM, LOW
            resolution TEXT NOT NULL DEFAULT 'UNRESOLVED', -- OFFICIAL_SOURCE_WINS, RECENT_SOURCE_WINS, MULTI_SOURCE_CONSENSUS, UNRESOLVED
            winning_claim_id TEXT,
            resolution_rationale TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contra_topic ON contradictions(lesson, topic);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contra_status ON contradictions(resolution);")

        # 14. ARAŞTIRMA GÖREVLERİ VE DURUM MAKİNESİ (Research Jobs & State Machine)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_jobs (
            research_id TEXT PRIMARY KEY,
            goal TEXT NOT NULL,
            lesson TEXT NOT NULL,
            topic TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'GOAL_CREATED',
            target_concepts_json TEXT NOT NULL DEFAULT '[]',
            discovered_sources_count INTEGER DEFAULT 0,
            ingested_sources_count INTEGER DEFAULT 0,
            extracted_claims_count INTEGER DEFAULT 0,
            verified_claims_count INTEGER DEFAULT 0,
            contradictions_count INTEGER DEFAULT 0,
            mastery_score REAL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            error TEXT
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rj_state ON research_jobs(state);")

        # 15. ARAŞTIRMA OLAY GÜNLÜĞÜ (Research Events Log)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_events (
            event_id TEXT PRIMARY KEY,
            research_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            from_state TEXT,
            to_state TEXT,
            details_json TEXT NOT NULL DEFAULT '{}',
            timestamp TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_re_job ON research_events(research_id, timestamp DESC);")

        # 16. KONSEPT DOLULUK MATRİSİ (Concept Coverage Matrix)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_coverage (
            concept_key TEXT PRIMARY KEY, -- topic_id:concept_name
            topic_id TEXT NOT NULL,
            concept_name TEXT NOT NULL,
            lesson TEXT NOT NULL,
            topic_name TEXT NOT NULL,
            is_covered INTEGER DEFAULT 0,
            evidence_claims_count INTEGER DEFAULT 0,
            distinct_teachers_count INTEGER DEFAULT 0,
            confidence_score REAL DEFAULT 0.0,
            last_verified_at TEXT
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cc_topic ON concept_coverage(topic_id);")

        # 17. HAKİMİYET ANLIK GÖRÜNTÜLERİ (Mastery Snapshots)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mastery_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            topic_id TEXT NOT NULL,
            lesson TEXT NOT NULL,
            topic_name TEXT NOT NULL,
            source_coverage REAL NOT NULL,
            evidence_density REAL NOT NULL,
            verification_score REAL NOT NULL,
            cross_teacher_agreement REAL NOT NULL,
            concept_coverage REAL NOT NULL,
            freshness_score REAL NOT NULL,
            overall_mastery REAL NOT NULL,
            consumed_videos_count INTEGER DEFAULT 0,
            distinct_teachers_json TEXT NOT NULL DEFAULT '[]',
            distinct_channels_json TEXT NOT NULL DEFAULT '[]',
            calculated_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ms_topic ON mastery_snapshots(topic_id, calculated_at DESC);")

        # ==========================================
        # 18. V1.5 DOKÜMAN & KANIT TABLOLARI (Document & Exam Intelligence)
        # ==========================================

        # 18.1. DOKÜMANLAR TABLOSU (Documents)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_documents (
            document_id TEXT PRIMARY KEY,
            sha256 TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'UPLOAD_MANUAL',
            authority_level INTEGER NOT NULL DEFAULT 1,
            exam_code TEXT,
            year INTEGER,
            lesson TEXT DEFAULT 'UNKNOWN',
            topic_id TEXT DEFAULT 'UNKNOWN',
            classification TEXT DEFAULT 'UNKNOWN',
            parsing_status TEXT DEFAULT 'PENDING', -- PENDING, PARSED, PARTIAL, FAILED
            parsing_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_doc_sha ON v15_documents(sha256);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_doc_lesson ON v15_documents(lesson, topic_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_doc_status ON v15_documents(parsing_status);")

        # 18.2. DOKÜMAN SAYFALARI (Document Pages)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_document_pages (
            page_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            raw_text TEXT NOT NULL,
            cleaned_text TEXT,
            is_ocr INTEGER DEFAULT 0,
            ocr_confidence REAL,
            char_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES v15_documents(document_id) ON DELETE CASCADE,
            CONSTRAINT uq_v15_doc_page UNIQUE (document_id, page_number)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_dp_doc ON v15_document_pages(document_id);")

        # 18.3. ORTAK KANIT TABLOSU (Unified Evidence: Document & YouTube)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_evidence (
            evidence_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL DEFAULT 'DOCUMENT', -- DOCUMENT, YOUTUBE
            document_id TEXT,
            page_number INTEGER,
            section_id TEXT,
            video_id TEXT,
            transcript_start_seconds REAL,
            transcript_end_seconds REAL,
            evidence_text TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES v15_documents(document_id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_ev_doc ON v15_evidence(document_id, page_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_ev_yt ON v15_evidence(video_id);")

        # 18.4. ADAY İDDİALAR TABLOSU (Candidate Claims Staging)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_candidate_claims (
            claim_id TEXT PRIMARY KEY,
            evidence_id TEXT NOT NULL,
            claim_type TEXT NOT NULL, -- FACT, DEFINITION, DATE, NUMBER, CLASSIFICATION, RELATION, CAUSE_EFFECT, COMPARISON, EXCEPTION, PROCESS, RULE, TEACHING_INSIGHT
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object_val TEXT NOT NULL,
            raw_statement TEXT NOT NULL,
            topic_id TEXT DEFAULT 'UNKNOWN',
            confidence_score REAL DEFAULT 0.5,
            audit_status TEXT DEFAULT 'CANDIDATE', -- CANDIDATE, SUPPORTED, VERIFIED, REJECTED, DISPUTED, OUTDATED, UNKNOWN
            audit_reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (evidence_id) REFERENCES v15_evidence(evidence_id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_cc_status ON v15_candidate_claims(audit_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_cc_evidence ON v15_candidate_claims(evidence_id);")

        # ==========================================
        # 19. PART 2: SINAV, SORU, KALIP VE TUZAK TABLOLARI
        # ==========================================

        # 19.1. SINAVLAR TABLOSU (Exams)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_exams (
            exam_id TEXT PRIMARY KEY,
            document_id TEXT,
            exam_name TEXT NOT NULL,
            exam_code TEXT NOT NULL, -- KPSS_LISANS, KPSS_ONLISANS, KPSS_ORTAOGRETIM, KPSS_ALAN
            year INTEGER NOT NULL,
            total_questions INTEGER NOT NULL DEFAULT 0,
            has_official_key INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES v15_documents(document_id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_exam_year ON v15_exams(year, exam_code);")

        # 19.2. SORULAR TABLOSU (Questions)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_questions (
            question_id TEXT PRIMARY KEY,
            exam_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            question_number_in_exam INTEGER NOT NULL,
            lesson TEXT NOT NULL,
            topic_id TEXT DEFAULT 'UNKNOWN',
            stem_text TEXT NOT NULL,
            passage_text TEXT,
            premises_json TEXT NOT NULL DEFAULT '[]',
            is_negative INTEGER DEFAULT 0,
            extraction_status TEXT DEFAULT 'COMPLETE', -- COMPLETE, EXTRACTION_INCOMPLETE
            created_at TEXT NOT NULL,
            FOREIGN KEY (exam_id) REFERENCES v15_exams(exam_id) ON DELETE CASCADE,
            FOREIGN KEY (document_id) REFERENCES v15_documents(document_id) ON DELETE CASCADE,
            CONSTRAINT uq_v15_exam_qnum UNIQUE (exam_id, question_number_in_exam)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_q_exam ON v15_questions(exam_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_q_topic ON v15_questions(lesson, topic_id);")

        # 19.3. SEÇENEKLER TABLOSU (Question Options: A, B, C, D, E)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_question_options (
            option_id TEXT PRIMARY KEY,
            question_id TEXT NOT NULL,
            option_key TEXT NOT NULL, -- 'A', 'B', 'C', 'D', 'E'
            option_text TEXT NOT NULL,
            is_correct_official INTEGER DEFAULT 0,
            is_trap INTEGER DEFAULT 0,
            trap_type TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (question_id) REFERENCES v15_questions(question_id) ON DELETE CASCADE,
            CONSTRAINT uq_v15_q_opt UNIQUE (question_id, option_key)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_opt_q ON v15_question_options(question_id);")

        # 19.4. RESMİ CEVAP ANAHTARLARI TABLOSU (Official Answer Keys)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_answer_keys (
            key_id TEXT PRIMARY KEY,
            exam_id TEXT NOT NULL,
            question_number INTEGER NOT NULL,
            correct_option TEXT NOT NULL, -- 'A', 'B', 'C', 'D', 'E'
            source_document_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (exam_id) REFERENCES v15_exams(exam_id) ON DELETE CASCADE,
            CONSTRAINT uq_v15_ak UNIQUE (exam_id, question_number)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_ak_exam ON v15_answer_keys(exam_id);")

        # 19.5. SORU KALIPLARI TAKSONOMİSİ (Question Patterns)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_question_patterns (
            pattern_id TEXT PRIMARY KEY,
            pattern_code TEXT NOT NULL UNIQUE,
            pattern_name TEXT NOT NULL,
            description TEXT NOT NULL,
            cognitive_level TEXT,
            structural_indicators_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_pat_code ON v15_question_patterns(pattern_code);")

        # 19.6. SORU - KALIP BAĞLANTILARI
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_question_pattern_links (
            link_id TEXT PRIMARY KEY,
            question_id TEXT NOT NULL,
            pattern_id TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (question_id) REFERENCES v15_questions(question_id) ON DELETE CASCADE,
            FOREIGN KEY (pattern_id) REFERENCES v15_question_patterns(pattern_id) ON DELETE CASCADE,
            CONSTRAINT uq_v15_q_pat UNIQUE (question_id, pattern_id)
        );
        """)

        # 19.7. SINAV TUZAKLARI VE ÇELDİRİCİ ZEKASI (Traps)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_traps (
            trap_id TEXT PRIMARY KEY,
            topic_id TEXT NOT NULL,
            target_concept TEXT NOT NULL,
            distractor_concept TEXT NOT NULL,
            trap_type TEXT NOT NULL,
            why_attractive TEXT NOT NULL,
            supporting_questions_json TEXT NOT NULL DEFAULT '[]',
            confidence REAL DEFAULT 0.5,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_trap_topic ON v15_traps(topic_id);")

        # 19.8. YENİDEN HESAPLANABİLİR SINAV İSTATİSTİKLERİ (Exam Statistics)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v15_exam_statistics (
            stat_id TEXT PRIMARY KEY,
            metric_type TEXT NOT NULL, -- TOPIC_FREQ, CONCEPT_FREQ, PATTERN_FREQ, TRAP_FREQ, YEAR_DIST, DIFFICULTY_DIST
            metric_key TEXT NOT NULL,
            exam_code TEXT,
            year INTEGER,
            count_value INTEGER NOT NULL DEFAULT 0,
            percentage_value REAL,
            meta_details_json TEXT NOT NULL DEFAULT '{}',
            last_computed_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_v15_stat_type ON v15_exam_statistics(metric_type, metric_key);")

# Veritabanını otomatik ilklendir
initialize_database()



