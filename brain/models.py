"""
KPSS Super-Brain: Kanonik Veri Modelleri ve Şemaları (Canonical Data Models)
Tüm sistem genelinde tür güvenliği (Type Safety), Provenance ve Pydantic v2 doğrulaması sağlar.
"""
import hashlib
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

# ==========================================
# 1. KAYNAK & MEDYA MODELLERİ (Source & Media)
# ==========================================

class SourceType(str, Enum):
    YOUTUBE_TRANSCRIPT = "YOUTUBE_TRANSCRIPT"
    YOUTUBE_AUDIO_WHISPER = "YOUTUBE_AUDIO_WHISPER"
    WEB_PAGE = "WEB_PAGE"
    OFFICIAL_LEGISLATION = "OFFICIAL_LEGISLATION"
    TUIK_MTA_STATISTICS = "TUIK_MTA_STATISTICS"
    PDF_DOCUMENT = "PDF_DOCUMENT"
    MANUAL_CURATED = "MANUAL_CURATED"

class VideoState(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    TRANSCRIPT_FOUND = "TRANSCRIPT_FOUND"
    TRANSCRIBED = "TRANSCRIBED"
    EXTRACTED = "EXTRACTED"
    VERIFIED = "VERIFIED"
    FAILED_TRANSCRIPT = "FAILED_TRANSCRIPT"
    FAILED_EXTRACTION = "FAILED_EXTRACTION"
    FAILED_VERIFICATION = "FAILED_VERIFICATION"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"

class Source(BaseModel):
    source_id: str
    source_type: SourceType
    title: str
    url: Optional[str] = None
    author_or_teacher: Optional[str] = "Bilinmiyor"
    institution_or_channel: Optional[str] = None
    published_at: Optional[str] = None
    reliability_score: float = Field(default=0.85, ge=0.0, le=1.0)
    provenance_hash: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @model_validator(mode="after")
    def compute_provenance_hash(self):
        if not self.provenance_hash:
            raw = f"{self.source_id}:{self.source_type.value}:{self.url or ''}:{self.author_or_teacher or ''}"
            self.provenance_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return self

class VideoMetadata(BaseModel):
    video_id: str
    url: str
    title: str
    channel_id: Optional[str] = ""
    channel_name: str = "Bilinmeyen Kanal"
    teacher_name: str = "Genel"
    lesson: str = "GENEL"
    topic: str = "Genel"
    subtopics: List[str] = Field(default_factory=list)
    duration_seconds: int = 0
    language: str = "tr"
    state: VideoState = VideoState.DISCOVERED
    relevance_score: float = 1.0
    source_rank: float = 1.0
    discovered_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    processed_at: Optional[str] = None
    error_message: Optional[str] = None

class TranscriptSegment(BaseModel):
    segment_id: str
    video_id: str
    start_seconds: float
    end_seconds: float
    text: str
    segment_hash: Optional[str] = None

    @model_validator(mode="after")
    def compute_hash(self):
        if not self.segment_hash:
            raw = f"{self.video_id}:{self.start_seconds}:{self.end_seconds}:{self.text}"
            self.segment_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return self

class TranscriptDocument(BaseModel):
    video_id: str
    source_type: SourceType
    full_text: str
    segments: List[TranscriptSegment] = Field(default_factory=list)
    word_count: int = 0
    language: str = "tr"
    is_whisper_transcribed: bool = False
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())

# ==========================================
# 2. ATOMİK İDDİA & KANIT MODELLERİ (Claims & Evidence)
# ==========================================

class ClaimType(str, Enum):
    FACT = "FACT"
    DEFINITION = "DEFINITION"
    RELATION = "RELATION"
    CAUSE_EFFECT = "CAUSE_EFFECT"
    COMPARISON = "COMPARISON"
    DATE = "DATE"
    NUMBER = "NUMBER"
    LEGAL_RULE = "LEGAL_RULE"
    EXCEPTION = "EXCEPTION"
    MNEMONIC = "MNEMONIC"
    TRAP = "TRAP"
    QUESTION_STRATEGY = "QUESTION_STRATEGY"
    TEACHER_INSIGHT = "TEACHER_INSIGHT"
    UNCERTAIN_CLAIM = "UNCERTAIN_CLAIM"

class TemporalValidityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REPEALED = "REPEALED"
    HISTORICAL = "HISTORICAL"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"

class EvidenceRef(BaseModel):
    source_id: str
    source_type: SourceType
    video_id: Optional[str] = None
    segment_id: Optional[str] = None
    url: Optional[str] = None
    snippet: str
    speaker_or_author: Optional[str] = None
    timestamp_str: Optional[str] = None

class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    CONTRADICTORY = "CONTRADICTORY"
    REJECTED = "REJECTED"

class AtomicClaim(BaseModel):
    claim_id: str
    text: str
    lesson: str
    topic: str
    subtopic: str = ""
    claim_type: ClaimType = ClaimType.FACT
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object_val: Optional[str] = None
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    temporal_status: TemporalValidityStatus = TemporalValidityStatus.ACTIVE
    verification_status: VerificationStatus = VerificationStatus.PENDING
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    provenance_hash: Optional[str] = None

    @model_validator(mode="after")
    def compute_claim_hash(self):
        if not self.provenance_hash:
            raw = f"{self.lesson}:{self.topic}:{self.text}"
            self.provenance_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return self

# ==========================================
# 3. DOĞRULAMA & ÇELİŞKİ MODELLERİ (Verification & Contradiction)
# ==========================================

class VerificationResult(BaseModel):
    is_valid: bool
    status: VerificationStatus
    stage: str
    reason: str
    confidence_score: float = 0.90
    refchecker_triplets: List[Dict[str, Any]] = Field(default_factory=list)
    z3_sat: Optional[bool] = None
    temporal_valid: bool = True
    numerical_valid: bool = True
    semantic_consistency_score: float = 0.95
    checked_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class ContradictionSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ContradictionResolution(str, Enum):
    OFFICIAL_SOURCE_WINS = "OFFICIAL_SOURCE_WINS"
    RECENT_SOURCE_WINS = "RECENT_SOURCE_WINS"
    MULTI_SOURCE_CONSENSUS = "MULTI_SOURCE_CONSENSUS"
    UNRESOLVED = "UNRESOLVED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

class ContradictionRecord(BaseModel):
    contradiction_id: str
    lesson: str
    topic: str
    claim_a_id: str
    claim_a_text: str
    claim_a_source: str
    claim_b_id: str
    claim_b_text: str
    claim_b_source: str
    severity: ContradictionSeverity = ContradictionSeverity.HIGH
    resolution: ContradictionResolution = ContradictionResolution.UNRESOLVED
    winning_claim_id: Optional[str] = None
    resolution_rationale: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None

# ==========================================
# 4. ARAŞTIRMA AJANI & GÖREV MODELLERİ (Agentic State)
# ==========================================

class ResearchJobState(str, Enum):
    GOAL_CREATED = "GOAL_CREATED"
    PLANNING = "PLANNING"
    DISCOVERING = "DISCOVERING"
    ACQUIRING = "ACQUIRING"
    EXTRACTING = "EXTRACTING"
    MINING = "MINING"
    VERIFYING = "VERIFYING"
    COMPARING = "COMPARING"
    GAP_ANALYSIS = "GAP_ANALYSIS"
    RESEARCHING_GAPS = "RESEARCHING_GAPS"
    SYNTHESIZING = "SYNTHESIZING"
    FINAL_REVIEW = "FINAL_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"

class ResearchEvent(BaseModel):
    event_id: str
    research_id: str
    event_type: str
    from_state: Optional[ResearchJobState] = None
    to_state: Optional[ResearchJobState] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ResearchJob(BaseModel):
    research_id: str
    goal: str
    lesson: str
    topic: str
    state: ResearchJobState = ResearchJobState.GOAL_CREATED
    target_concepts: List[str] = Field(default_factory=list)
    discovered_sources_count: int = 0
    ingested_sources_count: int = 0
    extracted_claims_count: int = 0
    verified_claims_count: int = 0
    contradictions_count: int = 0
    mastery_score: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None

# ==========================================
# 5. KAVRAM KAPSAMI & HAKİMİYET MODELLERİ (Coverage & Mastery)
# ==========================================

class ConceptCoverageRecord(BaseModel):
    topic_id: str
    concept_name: str
    lesson: str
    topic_name: str
    is_covered: bool = False
    evidence_claims_count: int = 0
    distinct_teachers_count: int = 0
    confidence_score: float = 0.0
    last_verified_at: Optional[str] = None

class MasterySnapshot(BaseModel):
    topic_id: str
    lesson: str
    topic_name: str
    source_coverage: float = Field(ge=0.0, le=1.0)
    evidence_density: float = Field(ge=0.0, le=1.0)
    verification_score: float = Field(ge=0.0, le=1.0)
    cross_teacher_agreement: float = Field(ge=0.0, le=1.0)
    concept_coverage: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    overall_mastery: float = Field(ge=0.0, le=1.0)
    consumed_videos_count: int = 0
    distinct_teachers: List[str] = Field(default_factory=list)
    distinct_channels: List[str] = Field(default_factory=list)
    calculated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

# ==========================================
# 6. DOKÜMAN & SINAV ZEKA MODELLERİ (V1.5 Document & Exam Intelligence)
# ==========================================

class DocumentClassification(str, Enum):
    COURSE_MATERIAL = "COURSE_MATERIAL"
    REFERENCE = "REFERENCE"
    OFFICIAL = "OFFICIAL"
    EXAM = "EXAM"
    ANSWER_KEY = "ANSWER_KEY"
    QUESTION_BANK = "QUESTION_BANK"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"

class DocumentSourceType(str, Enum):
    UPLOAD_MANUAL = "UPLOAD_MANUAL"
    OFFICIAL_OSYM = "OFFICIAL_OSYM"
    MEB_CURRICULUM = "MEB_CURRICULUM"
    PUBLISHER = "PUBLISHER"
    UNKNOWN = "UNKNOWN"

class V15AuditStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    SUPPORTED = "SUPPORTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"
    OUTDATED = "OUTDATED"
    UNKNOWN = "UNKNOWN"

class DocumentRecord(BaseModel):
    document_id: str
    sha256: str
    filename: str
    storage_path: str
    mime_type: str
    file_size: int
    source_type: DocumentSourceType = DocumentSourceType.UPLOAD_MANUAL
    authority_level: int = Field(default=1, ge=1, le=10)
    exam_code: Optional[str] = None
    year: Optional[int] = None
    lesson: str = "UNKNOWN"
    topic_id: str = "UNKNOWN"
    classification: DocumentClassification = DocumentClassification.UNKNOWN
    parsing_status: str = "PENDING"  # PENDING, PARSED, PARTIAL, FAILED
    parsing_error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class DocumentPageRecord(BaseModel):
    page_id: str
    document_id: str
    page_number: int = Field(ge=1)  # 1-indexed
    raw_text: str
    cleaned_text: Optional[str] = None
    is_ocr: bool = False
    ocr_confidence: Optional[float] = None
    char_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @model_validator(mode="after")
    def compute_char_count(self):
        if not self.char_count and self.raw_text:
            self.char_count = len(self.raw_text)
        return self

class V15EvidenceRecord(BaseModel):
    evidence_id: str
    source_type: str = "DOCUMENT"  # DOCUMENT or YOUTUBE
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    section_id: Optional[str] = None
    video_id: Optional[str] = None
    transcript_start_seconds: Optional[float] = None
    transcript_end_seconds: Optional[float] = None
    evidence_text: str
    content_hash: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @model_validator(mode="after")
    def compute_content_hash(self):
        if not self.content_hash and self.evidence_text:
            raw = f"{self.source_type}:{self.document_id or ''}:{self.page_number or ''}:{self.video_id or ''}:{self.evidence_text.strip()}"
            self.content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self

class V15CandidateClaimRecord(BaseModel):
    claim_id: str
    evidence_id: str
    claim_type: str  # FACT, DEFINITION, DATE, NUMBER, CLASSIFICATION, RELATION, CAUSE_EFFECT, COMPARISON, EXCEPTION, PROCESS, RULE, TEACHING_INSIGHT
    subject: str
    predicate: str
    object_val: str
    raw_statement: str
    topic_id: str = "UNKNOWN"
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    audit_status: V15AuditStatus = V15AuditStatus.CANDIDATE
    audit_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

# ==========================================
# 7. SINAV & SORU ZEKA MODELLERİ (Part 2: Exam & Trap Intelligence)
# ==========================================

class ExamRecord(BaseModel):
    exam_id: str
    document_id: Optional[str] = None
    exam_name: str
    exam_code: str  # KPSS_LISANS, KPSS_ONLISANS, KPSS_ORTAOGRETIM, KPSS_ALAN
    year: int
    total_questions: int = 0
    has_official_key: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class QuestionOptionRecord(BaseModel):
    option_id: str
    question_id: str
    option_key: str  # 'A', 'B', 'C', 'D', 'E'
    option_text: str
    is_correct_official: bool = False
    is_trap: bool = False
    trap_type: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class QuestionRecord(BaseModel):
    question_id: str
    exam_id: str
    document_id: str
    page_number: int = Field(ge=1)  # 1-indexed
    question_number_in_exam: int = Field(ge=1)
    lesson: str
    topic_id: str = "UNKNOWN"
    stem_text: str
    passage_text: Optional[str] = None
    premises: List[str] = Field(default_factory=list)  # I., II., III. öncülleri
    is_negative: bool = False
    extraction_status: str = "COMPLETE"  # COMPLETE, EXTRACTION_INCOMPLETE
    options: List[QuestionOptionRecord] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class AnswerKeyRecord(BaseModel):
    key_id: str
    exam_id: str
    question_number: int
    correct_option: str  # 'A', 'B', 'C', 'D', 'E'
    source_document_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class QuestionResolution(BaseModel):
    final_answer: str
    disagreement_flag: bool = False
    disagreement_details: Optional[Dict[str, Any]] = None
    note: Optional[str] = None

class QuestionPatternRecord(BaseModel):
    pattern_id: str
    pattern_code: str  # e.g., PAT_NEG_SELECTION, PAT_STATEMENT_ANALYSIS
    pattern_name: str
    description: str
    cognitive_level: Optional[str] = None
    structural_indicators: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class TrapRecord(BaseModel):
    trap_id: str
    topic_id: str
    target_concept: str
    distractor_concept: str
    trap_type: str  # CHRONOLOGY_CONFUSION, SIMILAR_TERM_CONFUSION, EXCEPTION_TRAP, CAUSE_RESULT_REVERSAL, CONCEPT_SWAP, NUMBER_SWAP
    why_attractive: str
    supporting_questions: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class ExamStatisticRecord(BaseModel):
    stat_id: str
    metric_type: str  # TOPIC_FREQ, CONCEPT_FREQ, PATTERN_FREQ, TRAP_FREQ, YEAR_DIST, DIFFICULTY_DIST
    metric_key: str
    exam_code: Optional[str] = None
    year: Optional[int] = None
    count_value: int = 0
    percentage_value: Optional[float] = None
    meta_details: Dict[str, Any] = Field(default_factory=dict)
    last_computed_at: str = Field(default_factory=lambda: datetime.now().isoformat())


