# KPSS Super-Brain V1.5 — Current State & Architectural Forensic Audit

## 1. Executive Summary
This document provides the mandatory forensic baseline audit of the `kpss-super-brain` repository prior to implementing Document / Exam Intelligence V1.5 (Part 1).

- **Current Repository Status**: 163 pytest unit/integration tests passing (100% pass rate).
- **Core Database**: SQLite in WAL mode (`brain/database.py`) with FTS5 search index (`knowledge_fts`), supplemented by PostgreSQL / pgvector schemas (`brain/pg_database.py`).
- **Existing Cognitive Ingestion**: YouTube video crawler, Whisper transcriber, DeepSeek-R1 Prosecutor Auditor (`cognition/prosecutor_auditor.py`), Z3 logic validator (`anti_hallucination/z3_logic_validator.py`), Cross-Teacher Analyzer, and Curriculum Matrix Engine.
- **V1.5 Goal**: Extend the engine to seamlessly ingest, parse, classify, audit, and extract knowledge from PDFs and Exam documents with strict provenance and zero regression.

---

## 2. Active Database Schemas & Persistence Analysis

The current database (`data/brain.db`) maintains 17 core tables:
1. `knowledge_records`: Canonical verified knowledge with FTS5 virtual table `knowledge_fts`.
2. `reasoning_chains`: Multi-step reasoning and question-solving strategies.
3. `teacher_profiles`: Cognitive profiles learned from teacher transcripts.
4. `video_queue`: Video ingestion queue and processing status.
5. `learning_events`: Episodic activity log and mastery tracking.
6. `exam_patterns`: Pattern archetypes identified from lessons.
7. `topic_mastery`: Topic mastery matrix across 3 KPSS levels.
8. `expert_syntheses`: Multi-teacher comparative consensus models.
9. `discovered_channels_playlists`: Discovered YouTube channels.
10. `sources`: Canonical source references and reliability scores.
11. `transcript_segments`: Chunked transcript segments with timestamps.
12. `atomic_claims`: Staged and verified atomic claims from videos.
13. `contradictions`: Detected factual/chronological contradictions.
14. `research_jobs`: State machine for OpenManus / Agentic research jobs.
15. `research_events`: Event log for research tasks.
16. `concept_coverage`: Topic-concept coverage matrix.
17. `mastery_snapshots`: Historical mastery snapshots.

### V1.5 Additive Tables:
To prevent schema contention or breaking existing queries, V1.5 introduces additive, namespaced tables:
**Part 1 (Foundation & Document Ingestion):**
- `v15_documents`: Metadata, SHA-256 hash, storage path, authority level, exam metadata.
- `v15_document_pages`: Multi-page segmentation, raw & cleaned text, 1-indexed `page_number`, OCR flags.
- `v15_evidence`: Unified multimodal evidence model (supporting both `DOCUMENT` and `YOUTUBE`).
- `v15_candidate_claims`: Staging table for extracted claims awaiting Auditor verification.

**Part 2 (Exam, Question, Pattern & Trap Intelligence):**
- `v15_exams`: Exam entities with `exam_code`, `year`, `total_questions`, `has_official_key`.
- `v15_questions`: Structured question items with 1-indexed `page_number`, `stem_text`, `premises_json`, `is_negative`, `extraction_status`.
- `v15_question_options`: Verbatim multiple-choice options (`A`-`E`), `is_correct_official`, `is_trap`, `trap_type`.
- `v15_answer_keys`: First-class official answer keys serving as primary truth anchor.
- `v15_question_patterns`: Abstract taxonomical archetypes (11 ÖSYM patterns).
- `v15_question_pattern_links`: Multi-label question pattern links with confidence scores.
- `v15_traps`: Evidence-backed distractor misconceptions linked to real questions.
- `v15_exam_statistics`: Rebuildable derived statistical aggregates.

---

## 3. Ingestion Routes & Attachment Points

```text
CURRENT INGESTION PATH (Videos):
YouTube -> Video Crawler -> Whisper / Transcript API -> Transcript Segments -> Cognitive Analyst -> Prosecutor Auditor -> Knowledge Store

V1.5 EXTENSION PATH (Documents - Part 1):
PDF / DOCX -> DocumentManager (SHA-256 Idempotency) -> DocumentParser (pypdf + OCR flag) 
           -> DocumentClassifier (Taxonomy + Safe Curriculum Cascade)
           -> DocumentAnalyst (Evidence Creation + 12 Claim Types)
           -> V15AuditorBridge (Prosecutor Auditor Gate)
           -> Guarded Canonical Commit (knowledge_records)

V1.5 EXTENSION PATH (Exams & Traps - Part 2):
Exam PDF + Official Key -> ExamParser (Multi-column boundary detector, 5 options, premises)
                        -> QuestionSolver (Rule 7 Answer Key Supremacy, LLM_DISAGREEMENT protocol)
                        -> PatternClassifier (11 abstract ÖSYM pattern taxonomies)
                        -> TrapDetector (Evidence-based distractor & misconception modeling)
                        -> ExamStatisticsEngine (Deterministic, rebuildable topic/pattern/trap/year metrics)
```

---

## 4. Invariant & Provenance Integrity Guarantees

1. **Source is not Truth**: Raw PDF text does not enter `knowledge_records` until verified by `ProsecutorAuditor`.
2. **Evidence-First**: Candidate claims must maintain a foreign key reference to `v15_evidence`.
3. **No Fallback Guessing**: `lesson = 'UNKNOWN'` and `topic_id = 'UNKNOWN'` are strictly assigned when confidence is below threshold; fallback to default topics (e.g., `TARIH`) is prohibited.
4. **Idempotency**: Duplicate SHA-256 uploads return the existing `document_id` without creating redundant records.
5. **Preserve Originals**: Raw uploaded files are stored safely in `data/documents/` with sanitized paths.
6. **Answer Key Supremacy (Rule 7)**: Extracted official keys are primary truth anchors. Candidate LLM answers never overwrite official keys; conflicts trigger `LLM_DISAGREEMENT`.
7. **Abstract Patterns Only**: Question patterns model structural archetypes; question body text is never copied into pattern entities.
8. **Evidence-Required Traps**: Distractors cannot be registered as cognitive traps without linking to at least one real question and an explicit attractiveness explanation.
9. **Derived Statistics Separation**: Exam metrics describe testing habits and are strictly rebuildable without modifying canonical curriculum definitions.
