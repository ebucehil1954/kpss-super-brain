"""
KPSS Super-Brain V1.5: Mission Control & REST API Yönlendiricisi (Phase 12)
Doküman yönetimi, sınav/soru zekası, kanıt gezgini ve bilgi grafiği uç noktalarını sağlar.
Dürüst arka plan durumu raporlama (Asenkron çalışanlar, PENDING/PARSING/COMPLETED/FAILED) prensibiyle çalışır.
"""
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Query
from fastapi.responses import HTMLResponse
from pathlib import Path
from pydantic import BaseModel

from brain.database import db_session
from ingestion.document_manager import document_manager, DocumentSecurityError
from ingestion.document_parser import DocumentParser, DocumentParsingError
from curriculum.document_classifier import document_classifier
from cognition.document_analyst import document_analyst
from cognition.v15_auditor_bridge import v15_auditor_bridge
from ingestion.exam_parser import exam_parser
from cognition.pattern_classifier import pattern_classifier
from cognition.trap_detector import trap_detector
from cognition.exam_statistics_engine import exam_statistics_engine
from brain.v15_graph_sync import v15_graph_sync

logger = logging.getLogger("v15_routes")
v15_router = APIRouter(prefix="/api/v15", tags=["V1.5 Document & Exam Intelligence"])
DASHBOARD_HTML_PATH = Path(__file__).parent / "dashboard.html"

@v15_router.get("/dashboard", response_class=HTMLResponse)
async def serve_v15_dashboard():
    """Mission Control görsel PDF yükleme ve analiz paneli."""
    if DASHBOARD_HTML_PATH.exists():
        return HTMLResponse(content=DASHBOARD_HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard bulunamadı</h1>", status_code=404)

# Bellek içi arka plan iş takip havuzu
_JOBS_STORE: Dict[str, Dict[str, Any]] = {}


def _async_process_document_pipeline(job_id: str, document_id: str, auto_analyze: bool = True):
    """Arka planda dokümanı parse eder, sınıflandırır ve iddia çıkarımı yapar."""
    try:
        _JOBS_STORE[job_id]["status"] = "PARSING"
        _JOBS_STORE[job_id]["updated_at"] = datetime.now().isoformat()

        parser = DocumentParser()
        pages = parser.parse_and_persist(document_id)

        # Otomatik sınıflandırma
        if pages:
            sample_text = " ".join([p.cleaned_text for p in pages[:3]])
            doc_class = document_classifier.classify_document_type(sample_text)
            lesson, topic, _ = document_classifier.map_curriculum_topic(sample_text)

            with db_session() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                UPDATE v15_documents
                SET classification = ?, lesson = CASE WHEN lesson IS NULL OR lesson = 'UNKNOWN' THEN ? ELSE lesson END,
                    topic_id = CASE WHEN topic_id IS NULL OR topic_id = 'UNKNOWN' THEN ? ELSE topic_id END
                WHERE document_id = ?
                """, (doc_class.value, lesson, topic, document_id))

        if auto_analyze and pages:
            _JOBS_STORE[job_id]["status"] = "EXTRACTING"
            _JOBS_STORE[job_id]["updated_at"] = datetime.now().isoformat()

            # İddiaları ayıkla
            total_claims = 0
            for p in pages:
                if p.cleaned_text and len(p.cleaned_text.strip()) > 30:
                    claims = document_analyst.extract_candidate_claims_from_page(
                        document_id=document_id,
                        page_number=p.page_number,
                        page_text=p.cleaned_text,
                        topic_id=p.document_id
                    )
                    total_claims += len(claims)

            _JOBS_STORE[job_id]["status"] = "AUDITING"
            _JOBS_STORE[job_id]["updated_at"] = datetime.now().isoformat()

            # Denetim kapısını çalıştır
            v15_auditor_bridge.audit_pending_candidate_claims(limit=50)

        # Graf senkronizasyonu
        v15_graph_sync.sync_all_v15_entities()

        _JOBS_STORE[job_id]["status"] = "COMPLETED"
        _JOBS_STORE[job_id]["updated_at"] = datetime.now().isoformat()

    except Exception as e:
        logger.error(f"Arka plan iş hatası: {str(e)}", exc_info=True)
        _JOBS_STORE[job_id]["status"] = "FAILED"
        _JOBS_STORE[job_id]["error"] = str(e)
        _JOBS_STORE[job_id]["updated_at"] = datetime.now().isoformat()


# ==============================================================
# 1. DOKÜMAN YÖNETİMİ UÇ NOKTALARI (Phase 12: Documents)
# ==============================================================

@v15_router.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    lesson: Optional[str] = Form(None),
    exam_code: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    auto_analyze: bool = Form(True)
):
    """
    Çok parçalı doküman (PDF, DOCX) yükleme uç noktası.
    SHA-256 idempotency garantisi ve dürüst arka plan iş kimliği (job_id) döner.
    """
    try:
        content_bytes = await file.read()
        doc = document_manager.ingest_document(
            content_bytes=content_bytes,
            filename=file.filename,
            lesson=lesson,
            exam_code=exam_code,
            year=year
        )

        job_id = f"job_doc_{uuid.uuid4().hex[:12]}"
        _JOBS_STORE[job_id] = {
            "job_id": job_id,
            "document_id": doc.document_id,
            "filename": doc.filename,
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "error": None
        }

        # Asenkron işlem görevini başlat
        background_tasks.add_task(_async_process_document_pipeline, job_id, doc.document_id, auto_analyze)

        return {
            "success": True,
            "job_id": job_id,
            "document_id": doc.document_id,
            "sha256": doc.sha256,
            "status": "PENDING",
            "message": "Doküman güvenle yüklendi ve işleme kuyruğuna alındı."
        }
    except DocumentSecurityError as e:
        raise HTTPException(status_code=400, detail=f"Güvenlik İhlali: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Yükleme Hatası: {str(e)}")


@v15_router.get("/documents")
async def list_documents(
    lesson: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200)
):
    """Sistemdeki tüm kayıtlı dokümanları filtrelerle listeler."""
    with db_session() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM v15_documents WHERE 1=1"
        params = []
        if lesson:
            query += " AND lesson = ?"
            params.append(lesson)
        if status:
            query += " AND parsing_status = ?"
            params.append(status)
        if year:
            query += " AND year = ?"
            params.append(year)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return {"total": len(rows), "documents": [dict(r) for r in rows]}


@v15_router.get("/documents/{doc_id}/status")
async def get_document_status(doc_id: str):
    """Dokümanın gerçek zamanlı ayrıştırma ve analiz durumunu döner."""
    # Önce job havuzunu kontrol et
    for job in _JOBS_STORE.values():
        if job.get("document_id") == doc_id:
            return job

    doc = document_manager.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doküman bulunamadı.")

    return {
        "document_id": doc_id,
        "filename": doc["filename"],
        "parsing_status": doc["parsing_status"],
        "parsing_error": doc["parsing_error"],
        "classification": doc["classification"],
        "created_at": doc["created_at"]
    }


@v15_router.post("/documents/{doc_id}/analyze")
async def analyze_document_pipeline(doc_id: str, background_tasks: BackgroundTasks):
    """Mevcut bir doküman için iddia çıkarımı ve denetim sürecini tetikler."""
    doc = document_manager.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doküman bulunamadı.")

    job_id = f"job_anlz_{uuid.uuid4().hex[:12]}"
    _JOBS_STORE[job_id] = {
        "job_id": job_id,
        "document_id": doc_id,
        "filename": doc["filename"],
        "status": "EXTRACTING",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error": None
    }
    background_tasks.add_task(_async_process_document_pipeline, job_id, doc_id, True)

    return {"success": True, "job_id": job_id, "status": "EXTRACTING"}


@v15_router.post("/documents/{doc_id}/reprocess")
async def reprocess_document(doc_id: str, background_tasks: BackgroundTasks):
    """Dokümanı sıfırdan yeniden ayrıştırır ve dizinler."""
    doc = document_manager.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doküman bulunamadı.")

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM v15_document_pages WHERE document_id = ?", (doc_id,))
        cursor.execute("UPDATE v15_documents SET parsing_status = 'PENDING', parsing_error = NULL WHERE document_id = ?", (doc_id,))

    job_id = f"job_reproc_{uuid.uuid4().hex[:12]}"
    _JOBS_STORE[job_id] = {
        "job_id": job_id,
        "document_id": doc_id,
        "filename": doc["filename"],
        "status": "PARSING",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error": None
    }
    background_tasks.add_task(_async_process_document_pipeline, job_id, doc_id, True)

    return {"success": True, "job_id": job_id, "status": "PARSING"}


# ==============================================================
# 2. SINAV & SORU ZEKASI UÇ NOKTALARI (Phase 12: Exams & Questions)
# ==============================================================

@v15_router.get("/exams")
async def list_exams(exam_code: Optional[str] = Query(None), year: Optional[int] = Query(None)):
    """Kayıtlı sınav kitapçıklarını listeler."""
    with db_session() as conn:
        cursor = conn.cursor()
        q = "SELECT * FROM v15_exams WHERE 1=1"
        params = []
        if exam_code:
            q += " AND exam_code = ?"
            params.append(exam_code)
        if year:
            q += " AND year = ?"
            params.append(year)
        q += " ORDER BY year DESC, exam_name ASC"
        cursor.execute(q, tuple(params))
        rows = cursor.fetchall()
        return {"total": len(rows), "exams": [dict(r) for r in rows]}


@v15_router.get("/exams/{exam_id}/questions")
async def get_exam_questions(exam_id: str):
    """Bir sınava ait tüm soruları, seçenekleri ve cevap anahtarını döner."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT q.*, ak.correct_option as official_correct_option
        FROM v15_questions q
        LEFT JOIN v15_answer_keys ak ON q.exam_id = ak.exam_id AND q.question_number_in_exam = ak.question_number
        WHERE q.exam_id = ?
        ORDER BY q.question_number_in_exam ASC
        """, (exam_id,))
        q_rows = cursor.fetchall()

        result = []
        for row in q_rows:
            q_dict = dict(row)
            cursor.execute("SELECT * FROM v15_question_options WHERE question_id = ? ORDER BY option_key ASC", (q_dict["question_id"],))
            q_dict["options"] = [dict(opt) for opt in cursor.fetchall()]
            result.append(q_dict)

        return {"exam_id": exam_id, "total": len(result), "questions": result}


@v15_router.get("/questions/{question_id}")
async def get_question_detail(question_id: str):
    """Tek bir sorunun tüm detaylarını (kök, öncüller, şıklar, resmi anahtar, kalıplar, tuzaklar) döner."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM v15_questions WHERE question_id = ?", (question_id,))
        q_row = cursor.fetchone()
        if not q_row:
            raise HTTPException(status_code=404, detail="Soru bulunamadı.")

        q_data = dict(q_row)

        # Seçenekler
        cursor.execute("SELECT * FROM v15_question_options WHERE question_id = ? ORDER BY option_key ASC", (question_id,))
        q_data["options"] = [dict(r) for r in cursor.fetchall()]

        # Resmi Cevap Anahtarı
        cursor.execute("SELECT * FROM v15_answer_keys WHERE exam_id = ? AND question_number = ?", (q_data["exam_id"], q_data["question_number_in_exam"]))
        ak_row = cursor.fetchone()
        q_data["official_key"] = dict(ak_row) if ak_row else None

        # Bağlı Kalıplar
        cursor.execute("""
        SELECT p.*, l.confidence
        FROM v15_question_pattern_links l
        JOIN v15_question_patterns p ON l.pattern_id = p.pattern_id
        WHERE l.question_id = ?
        """, (question_id,))
        q_data["patterns"] = [dict(r) for r in cursor.fetchall()]

        return q_data


@v15_router.get("/patterns")
async def list_question_patterns():
    """11 standart soru kalıbını ve kullanım frekanslarını döner."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT p.*, COUNT(l.link_id) as usage_count
        FROM v15_question_patterns p
        LEFT JOIN v15_question_pattern_links l ON p.pattern_id = l.pattern_id
        GROUP BY p.pattern_id
        ORDER BY usage_count DESC
        """)
        rows = cursor.fetchall()
        return {"total": len(rows), "patterns": [dict(r) for r in rows]}


@v15_router.get("/traps")
async def list_exam_traps(topic_id: Optional[str] = Query(None)):
    """Bilişsel çeldirici ve sınav tuzaklarını listeler."""
    if topic_id:
        return {"traps": trap_detector.get_traps_for_topic(topic_id)}
    return {"traps": trap_detector.list_all_traps()}


@v15_router.get("/statistics")
async def get_exam_statistics(recompute: bool = Query(False)):
    """Yeniden hesaplanabilir sınav trend ve soru istatistiklerini döner."""
    if recompute:
        exam_statistics_engine.recompute_all_statistics()

    return {
        "topic_frequency": exam_statistics_engine.get_topic_frequency_summary(),
        "pattern_frequency": exam_statistics_engine.get_pattern_frequency_summary(),
        "trap_frequency": exam_statistics_engine.get_trap_frequency_summary(),
        "year_distribution": exam_statistics_engine.get_year_distribution_summary()
    }


# ==============================================================
# 3. KANIT & BİLGİ GRAFİĞİ GEZGİNİ (Phase 12: Provenance & Graph)
# ==============================================================

@v15_router.get("/evidence/{evidence_id}")
async def get_evidence_detail(evidence_id: str):
    """Kanıt kaydını ve kaynak bağlamını (sayfa metni / video damgası) döner."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM v15_evidence WHERE evidence_id = ?", (evidence_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Kanıt kaydı bulunamadı.")
        return dict(row)


@v15_router.get("/graph/neighborhood/{node_id}")
async def get_graph_neighborhood(node_id: str, depth: int = Query(1, ge=1, le=3)):
    """Kavram, iddia veya soru düğümü etrafındaki komşuluk alt grafiğini döner."""
    subgraph = v15_graph_sync.get_subgraph_neighborhood(node_id=node_id, depth=depth)
    if not subgraph.get("center_node"):
        raise HTTPException(status_code=404, detail=f"Düğüm bulunamadı: '{node_id}'")
    return subgraph


@v15_router.post("/graph/sync")
async def trigger_graph_synchronization(rebuild: bool = Query(False)):
    """Grafiği kanonik tablolardan günceller veya sıfırdan yeniden oluşturur."""
    if rebuild:
        return v15_graph_sync.rebuild_graph_from_canonical()
    counts = v15_graph_sync.sync_all_v15_entities()
    return {"status": "SYNCED", "details": counts}
