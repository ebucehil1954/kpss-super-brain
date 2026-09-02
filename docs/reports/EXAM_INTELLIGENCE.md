# KPSS Super-Brain V1.5 — Exam & Trap Intelligence Documentation

## 1. Overview & Objectives: How Knowledge is Tested

While Part 1 established the foundation for document processing and **"WHAT IS TAUGHT"**, Part 2 models **"HOW IT IS TESTED"**.

```text
┌─────────────────────────────────────────────────────────────┐
│                       EXAM PIPELINE                         │
│                                                             │
│   Official Exam PDF + Official Answer Key                   │
│         │                                                   │
│         ▼                                                   │
│   Question Boundary Detection & Stem Extraction             │
│         │                                                   │
│         ▼                                                   │
│   Option Extraction (A, B, C, D, E) + Primary Key Mapping   │
│         │                                                   │
│         ├──► LLM Analysis (Candidate)                       │
│         │         │                                         │
│         │         ▼                                         │
│         │   [Check Disagreement with Official Key]          │
│         │         │                                         │
│         │         ├──► Match    ──► VALIDATED QUESTION      │
│         │         └──► Conflict ──► LLM_DISAGREEMENT FLAG   │
│         │                                                   │
│         ▼                                                   │
│   Pedagogical Concept & Topic Linkage                       │
│         │                                                   │
│         ▼                                                   │
│   Question Pattern Extraction (Taxonomy Classification)     │
│         │                                                   │
│         ▼                                                   │
│   Trap & Distractor Analysis (Cognitive Misconceptions)     │
│         │                                                   │
│         ▼                                                   │
│   Rebuildable Assessment Statistics & Trend Aggregates      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Inviolable Safety Rules & Invariants

1. **Answer Keys are First-Class Evidence (Rule 7)**:
   - Official answer keys (`A`, `B`, `C`, `D`, `E`) are the **primary truth anchors**.
   - An LLM solver candidate must **never overwrite** or silently modify the official answer key.
2. **Mandatory Disagreement Recording**:
   - If an LLM suggests an answer conflicting with the official key, the system marks the question with `LLM_DISAGREEMENT` and logs both rationales. The official key remains canonical.
3. **No Hallucinated Question Provenance (Rule 3)**:
   - Every question links directly to its `exam_id`, `document_id`, and 1-indexed `page_number`.
4. **Verbatim Distractor & Option Preservation**:
   - Every option (`A` through `E`) is preserved verbatim without alteration or abbreviation.
5. **Patterns Are Abstract Models, Not Copies**:
   - A question pattern represents a reusable structural archetype (e.g., `NEGATIVE_SELECTION`, `STATEMENT_ANALYSIS`), never the raw text of an individual question.
6. **No Generalization from Weak Evidence**:
   - A distractor is never classified as a universal trap without concrete evidence linking it to at least one real question and a clear cognitive rationale.
7. **Exam Statistics Separation**:
   - High exam frequency measures ÖSYM testing habits; it never alters the scientific or historical truth of curriculum definitions.

---

## 3. Database Schema Architecture

The Part 2 architecture introduces 8 dedicated relational tables in `brain/database.py`:

```sql
-- 1. Exams Table
CREATE TABLE IF NOT EXISTS v15_exams (
    exam_id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES v15_documents(document_id) ON DELETE CASCADE,
    exam_name TEXT NOT NULL,
    exam_code TEXT NOT NULL, -- KPSS_LISANS, KPSS_ONLISANS, KPSS_ORTAOGRETIM, KPSS_ALAN
    year INTEGER NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 0,
    has_official_key INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- 2. Questions Table
CREATE TABLE IF NOT EXISTS v15_questions (
    question_id TEXT PRIMARY KEY,
    exam_id TEXT NOT NULL REFERENCES v15_exams(exam_id) ON DELETE CASCADE,
    document_id TEXT NOT NULL REFERENCES v15_documents(document_id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    question_number_in_exam INTEGER NOT NULL,
    lesson TEXT NOT NULL,
    topic_id TEXT DEFAULT 'UNKNOWN',
    stem_text TEXT NOT NULL,
    passage_text TEXT,
    premises_json TEXT NOT NULL DEFAULT '[]',
    is_negative INTEGER DEFAULT 0,
    extraction_status TEXT DEFAULT 'COMPLETE',
    created_at TEXT NOT NULL,
    CONSTRAINT uq_v15_exam_qnum UNIQUE (exam_id, question_number_in_exam)
);

-- 3. Question Options Table (A, B, C, D, E)
CREATE TABLE IF NOT EXISTS v15_question_options (
    option_id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES v15_questions(question_id) ON DELETE CASCADE,
    option_key TEXT NOT NULL, -- 'A', 'B', 'C', 'D', 'E'
    option_text TEXT NOT NULL,
    is_correct_official INTEGER DEFAULT 0,
    is_trap INTEGER DEFAULT 0,
    trap_type TEXT,
    created_at TEXT NOT NULL,
    CONSTRAINT uq_v15_q_opt UNIQUE (question_id, option_key)
);

-- 4. Official Answer Keys Table
CREATE TABLE IF NOT EXISTS v15_answer_keys (
    key_id TEXT PRIMARY KEY,
    exam_id TEXT NOT NULL REFERENCES v15_exams(exam_id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    correct_option TEXT NOT NULL,
    source_document_id TEXT,
    created_at TEXT NOT NULL,
    CONSTRAINT uq_v15_ak UNIQUE (exam_id, question_number)
);

-- 5. Question Patterns Taxonomy Table
CREATE TABLE IF NOT EXISTS v15_question_patterns (
    pattern_id TEXT PRIMARY KEY,
    pattern_code TEXT NOT NULL UNIQUE,
    pattern_name TEXT NOT NULL,
    description TEXT NOT NULL,
    cognitive_level TEXT,
    structural_indicators_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

-- 6. Question-to-Pattern Links Table
CREATE TABLE IF NOT EXISTS v15_question_pattern_links (
    link_id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES v15_questions(question_id) ON DELETE CASCADE,
    pattern_id TEXT NOT NULL REFERENCES v15_question_patterns(pattern_id) ON DELETE CASCADE,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    CONSTRAINT uq_v15_q_pat UNIQUE (question_id, pattern_id)
);

-- 7. Exam Traps & Cognitive Misconceptions Table
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

-- 8. Rebuildable Exam Statistics Table
CREATE TABLE IF NOT EXISTS v15_exam_statistics (
    stat_id TEXT PRIMARY KEY,
    metric_type TEXT NOT NULL, -- TOPIC_FREQ, CONCEPT_FREQ, PATTERN_FREQ, TRAP_FREQ, YEAR_DIST
    metric_key TEXT NOT NULL,
    exam_code TEXT,
    year INTEGER,
    count_value INTEGER NOT NULL DEFAULT 0,
    percentage_value REAL,
    meta_details_json TEXT NOT NULL DEFAULT '{}',
    last_computed_at TEXT NOT NULL
);
```

---

## 4. Question Pattern Taxonomy (11 Archetypes)

Managed by `PatternClassifier` (`cognition/pattern_classifier.py`):

| Pattern Code | Name | Cognitive Level | Syntactic / Structural Indicators |
| :--- | :--- | :--- | :--- |
| `NEGATIVE_SELECTION` | Olumsuz Seçim ve Kök Analizi | ANALYSIS | "değildir", "yoktur", "savunulamaz", "ulaşılamaz", "söylenemez" |
| `STATEMENT_ANALYSIS` | Öncüllü Yargı Analizi (I, II, III) | EVALUATION | "yalnız I", "I ve II", "I, II ve III", "yargılarından hangileri" |
| `CHRONOLOGY` | Kronolojik Sıralama | KNOWLEDGE | "kronolojik", "sırasıyla", "önce", "sonra", "tarihsel sıralama" |
| `CAUSE_RESULT` | Neden - Sonuç Bağıntısı | COMPREHENSION | "neden olmuştur", "sonucudur", "gerekçesiyle", "ortam hazırlamıştır" |
| `COMPARISON` | Karşılaştırma ve Mukayese | ANALYSIS | "farklı olarak", "benzer şekilde", "karşılaştırıldığında", "kıyasla" |
| `MATCHING` | Eşleştirme ve Tablo | KNOWLEDGE | "eşleştirmelerden hangisinde", "ilişkilendirilemez", "tabloda" |
| `INFERENCE` | Paragraftan Çıkarım | INFERENCE | "bilgiye dayanarak", "paragraftan hareketle", "çıkarılabilir" |
| `EXCEPTION` | Kural Dışı / İstisna Tespiti | ANALYSIS | "istisnadır", "hariçtir", "kapsamı dışındadır", "aykırıdır" |
| `COUNTING` | Sayısal Nicelik ve Adet Sayma | ANALYSIS | "kaç tanesi", "kaçında", "sayısı kaçtır" |
| `CLASSIFICATION` | Tasnif ve Gruplandırma | COMPREHENSION | "grubunda yer alır", "sınıflandırılır", "türündendir" |
| `DIRECT_FACT` | Doğrudan Olgusal Bilgi (Spot) | KNOWLEDGE | "kimdir", "hangisidir", "adlandırılır", "nerededir" |

---

## 5. Trap & Distractor Taxonomy (6 Misconceptions)

Managed by `TrapDetector` (`cognition/trap_detector.py`):

1. **`CHRONOLOGY_CONFUSION`**: Placing an event from an earlier or later era that sounds plausible (e.g. associating Tanzimat reform with Kanuni era).
2. **`SIMILAR_TERM_CONFUSION`**: Confusing phonetically or conceptually similar terms (e.g., Sened-i İttifak vs. Tanzimat Fermanı).
3. **`EXCEPTION_TRAP`**: Presenting a general constitutional rule where an explicit exception applies (or vice-versa).
4. **`CAUSE_RESULT_REVERSAL`**: Inverting the historical causality (presenting a treaty consequence as its cause).
5. **`CONCEPT_SWAP`**: Swapping specific attributes of two closely related bodies (e.g., decisions of Amasya Genelgesi vs. Erzurum Kongresi).
6. **`NUMBER_SWAP`**: Alterations in parliamentary quorums, member counts, or statutory deadlines (e.g., 360 vs 400).

---

## 6. Exam Statistics Engine

Managed by `ExamStatisticsEngine` (`cognition/exam_statistics_engine.py`):

- **Purely Rebuildable**: Running `recompute_all_statistics()` purges `v15_exam_statistics` and recalculates exact metrics from underlying tables.
- **Metric Categories**:
  - `TOPIC_FREQ`: Total question volume per curriculum topic across years.
  - `PATTERN_FREQ`: Distribution of question archetypes.
  - `TRAP_FREQ`: Frequency of cognitive distractor categories.
  - `CONCEPT_FREQ`: Recurrence of key targeted concepts.
  - `YEAR_DIST`: Examination volume trends by year and exam level.
