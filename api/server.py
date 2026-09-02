"""
KPSS Super-Brain: FastAPI API Sunucusu (Genişletilmiş REST & WebSocket Arayüzü)
"""
import os
import json
import httpx
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from config import super_brain_config
from brain.knowledge_store import knowledge_store
from brain.reasoning_store import reasoning_store
from brain.exporter import data_exporter
from senses.video_queue import video_queue
from senses.video_crawler import video_crawler
from cognition.teacher_learner import teacher_learner
from cognition.self_tester import self_tester
from cognition.pattern_learner import pattern_learner
from autonomous.cycle_manager import cycle_manager
from autonomous.stats_tracker import stats_tracker
from generators.smart_question_gen import smart_question_generator
from generators.explainer import kpss_professor_explainer

app = FastAPI(
    title="Promius KPSS Super-Brain API",
    description="7/24 Öğrenen Yapay Zeka KPSS Profesörü API Katmanı",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.v15_routes import v15_router
app.include_router(v15_router)

from api.logs_routes import logs_router
app.include_router(logs_router)

from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
try:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
except Exception:
    templates = None

@app.get("/", response_class=HTMLResponse)
async def serve_root_panel(request: Request):
    """Ana Kontrol Panelini render eder."""
    context = {
        "request": request,
        "title": "Promius KPSS Super-Brain",
        "app_name": "PROMIUS KPSS SUPER-BRAIN",
        "default_confidence": "95.0",
        "min_sources": "8-10"
    }
    if templates:
        try:
            return templates.TemplateResponse(request=request, name="index.html", context=context)
        except TypeError:
            return templates.TemplateResponse("index.html", context)
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Ana Panel bulunamadı</h1>", status_code=404)

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_root_dashboard():
    p = Path(__file__).parent / "dashboard.html"
    if p.exists():
        return HTMLResponse(content=p.read_text(encoding="utf-8"))
    return RedirectResponse(url="/api/v15/dashboard")

@app.get("/logs", response_class=HTMLResponse)
async def serve_logs_page(request: Request):
    """Otonom Saha, Çıkarım, Denetim ve Hata Günlüğü görsel paneli."""
    context = {
        "request": request,
        "title": "OpenManus & Qwen LLM — Saha, Çıkarım, Denetim ve Hata Günlüğü",
        "app_name": "PROMIUS KPSS SUPER-BRAIN"
    }
    if templates:
        try:
            return templates.TemplateResponse(request=request, name="logs.html", context=context)
        except TypeError:
            return templates.TemplateResponse("logs.html", context)
    template_path = TEMPLATES_DIR / "logs.html"
    if template_path.exists():
        return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Logs şablonu hazırlanıyor...</h1>", status_code=200)

class KnowledgeQueryRequest(BaseModel):
    query: str
    lesson: Optional[str] = None
    record_type: Optional[str] = None
    limit: int = 20

class AutonomousStepRequest(BaseModel):
    force_discovery: bool = False

class ExplainRequest(BaseModel):
    lesson: str
    topic: str
    question: Optional[str] = None

class GenerateQuestionRequest(BaseModel):
    lesson: str
    topic: str
    teacher_style: Optional[str] = None
    difficulty: str = "ORTA"

@app.get("/api/status")
async def get_system_status():
    """Canlı sistem durumunu ve ambar metriklerini döner."""
    metrics = stats_tracker.get_live_metrics()
    
    ollama_active = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{super_brain_config.OLLAMA_BASE_URL}/api/tags")
            ollama_active = (res.status_code == 200)
    except Exception:
        ollama_active = False

    return {
        "status": "online",
        "ollama_active": ollama_active,
        "main_model": super_brain_config.MAIN_MODEL,
        "reasoning_model": super_brain_config.REASONING_MODEL,
        "metrics": metrics
    }

@app.get("/api/knowledge/records")
async def get_knowledge_records(
    query: str = Query("", description="Arama metni"),
    lesson: Optional[str] = Query(None),
    record_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    """FTS5 ve filtrelere göre bilgi kayıtlarını arar."""
    results = knowledge_store.search(
        query=query,
        lesson=lesson,
        record_type=record_type,
        limit=limit
    )
    return {"total": len(results), "records": results}

@app.get("/api/reasoning/chains")
async def get_reasoning_chains(lesson: Optional[str] = None, topic: Optional[str] = None):
    """Mantık zincirlerini döner."""
    if lesson and topic:
        chains = reasoning_store.get_chains_for_topic(lesson, topic)
    else:
        chains = reasoning_store.get_all_chains()
    return {"total": len(chains), "chains": chains}

@app.get("/api/teachers/profiles")
async def get_teacher_profiles():
    """Tüm eğitmen profillerini döner."""
    profiles = teacher_learner.get_all_profiles()
    return {"total": len(profiles), "profiles": profiles}

@app.get("/api/video-queue")
async def get_video_queue_status():
    """Video izleme kuyruk durumunu döner."""
    summary = video_queue.get_queue_summary()
    return summary

@app.get("/api/patterns")
async def get_exam_patterns():
    """Öğrenilmiş soru kalıplarını döner."""
    patterns = pattern_learner.get_all_patterns()
    return {"total": len(patterns), "patterns": patterns}

@app.get("/api/health/gaps")
async def get_knowledge_health_and_gaps():
    """Bilişsel sağlık ve müfredat konu eksikliği analizini döner."""
    health = self_tester.evaluate_knowledge_health()
    return health

@app.get("/api/curriculum/mastery")
async def get_curriculum_mastery():
    """Resmi ÖSYM müfredat konu hakimiyet matrisini ve video tüketim oranlarını döner."""
    from brain.curriculum_matrix import curriculum_matrix
    return curriculum_matrix.get_curriculum_mastery_report()

@app.get("/api/curriculum/synthesis/{lesson}/{topic}")
async def get_topic_synthesis(lesson: str, topic: str):
    """Belirli bir konu için çoklu hoca karşılaştırmalı uzman sentezini döner."""
    from cognition.cross_teacher_analyzer import cross_teacher_analyzer
    return cross_teacher_analyzer.get_synthesis_for_topic(lesson, topic)

@app.get("/api/curriculum/syntheses")
async def get_all_topic_syntheses():
    """Tüm tamamlanmış konu sentezlerini döner."""
    from cognition.cross_teacher_analyzer import cross_teacher_analyzer
    syntheses = cross_teacher_analyzer.get_all_syntheses()
    return {"total": len(syntheses), "syntheses": syntheses}

@app.get("/api/discovery/status")
async def get_manus_discovery_status():
    """Manus YouTube keşif ajanının canlı durumunu döner."""
    from senses.youtube_crawler_agent import youtube_crawler_agent
    return youtube_crawler_agent.get_status()

@app.post("/api/discovery/trigger")
async def trigger_manus_discovery():
    """Manus YouTube keşif ajanını manuel tetikler."""
    from senses.youtube_crawler_agent import youtube_crawler_agent
    res = await youtube_crawler_agent.run_manus_style_deep_discovery(force_all_topics=True)
    return res

@app.post("/api/exports/refresh")
async def trigger_exports_refresh():
    """Tüm ambarı 'data/exports/' klasörüne dışa aktarır."""
    files = data_exporter.export_all()
    return {"status": "success", "files": files, "timestamp": datetime.now().isoformat()}

@app.post("/api/autonomous/step")
async def trigger_autonomous_step(req: AutonomousStepRequest = Body(default=AutonomousStepRequest())):
    """Otonom öğrenme döngüsünün 1 video sindirme adımını tetikler."""
    if req.force_discovery:
        await cycle_manager.run_discovery_if_needed(force=True)
    
    result = await cycle_manager.process_single_video_step()
    await cycle_manager.run_consolidation_and_exports(force=True)
    return {
        "status": "success" if result else "idle",
        "result": result,
        "metrics": stats_tracker.get_live_metrics()
    }

@app.post("/api/professor/explain")
async def professor_explain_topic(req: ExplainRequest):
    """KPSS Profesörü ders anlatımı ve rehberlik üretir."""
    explanation = await kpss_professor_explainer.explain_topic_as_professor(
        lesson=req.lesson,
        topic=req.topic,
        student_question=req.question
    )
    return explanation

@app.post("/api/professor/generate-question")
async def professor_generate_question(req: GenerateQuestionRequest):
    """Öğrenilmiş zihniyete dayalı hakemli sınav sorusu üretir."""
    q = await smart_question_generator.generate_master_question(
        lesson=req.lesson,
        topic=req.topic,
        teacher_style=req.teacher_style,
        difficulty=req.difficulty
    )
    if not q:
        raise HTTPException(status_code=500, detail="Soru üretilemedi.")
    return q

@app.get("/api/consciousness")
async def get_consciousness_state():
    """Ajanın anlık düşünce günlüğü (CoT), aktif odak ve kararlarını döner."""
    from autonomous.consciousness import consciousness
    return consciousness.get_current_consciousness_state()

@app.get("/api/checkpoint")
async def get_checkpoint_state():
    """Kalıcı hafızadaki son durum checkpoint verilerini döner."""
    from autonomous.state_persistence import state_persistence
    return state_persistence.load_checkpoint()

@app.get("/api/ontology/stats")
async def get_ontology_statistics():
    """Derin müfredat ve bilgi grafiği istatistiklerini döner."""
    from brain.deep_ontology import deep_ontology
    return deep_ontology.get_curriculum_statistics()

from fastapi import UploadFile, File, Form
import shutil

@app.post("/api/documents/upload")
async def upload_and_ingest_document(
    file: UploadFile = File(...),
    lesson: str = Form("GENEL"),
    topic: str = Form("Genel Müfredat"),
    source_title: Optional[str] = Form(None)
):
    """
    Kullanıcının yüklediği MEB kitabı veya PDF fasikülünü doğrudan okur ve hafıza ambarına sindirir.
    """
    from senses.turbo_pdf_reader import turbo_pdf_reader
    
    os.makedirs(super_brain_config.PDF_UPLOADS_DIR, exist_ok=True)
    file_path = os.path.join(super_brain_config.PDF_UPLOADS_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    result = await turbo_pdf_reader.ingest_book_or_document(
        pdf_path=file_path,
        lesson=lesson,
        topic=topic,
        source_title=source_title or file.filename
    )
    
    return result

@app.get("/api/documents/history")
async def get_uploaded_documents_history():
    """Daha önce yüklenmiş ve sindirilmiş belgelerin geçmişini döner."""
    from senses.turbo_pdf_reader import turbo_pdf_reader
    history = turbo_pdf_reader.get_ingested_history()
    return {"total": len(history), "history": history}

# ==============================================================
# FAZ 1: MÜFREDAT & AKILLI ARAŞTIRMA KUYRUĞU ENDPOINT'LERİ
# ==============================================================

@app.get("/api/curriculum/coverage")
async def get_curriculum_coverage_report(
    exam_level: str = Query("ALL", description="LISANS, ONLISANS, ORTAOGRETIM veya ALL")
):
    """3 KPSS sınavı ve ders bazlı canlı müfredat hakimiyet raporunu döner."""
    from curriculum import curriculum_engine, ExamLevel
    lvl = ExamLevel.from_str(exam_level)
    return curriculum_engine.get_gap_analysis(exam_level=lvl)

@app.get("/api/curriculum/next-tasks")
async def get_curriculum_next_tasks(
    count: int = Query(5, ge=1, le=20),
    exam_level: str = Query("ALL")
):
    """OpenManus veya otonom crawler için sıradaki yüksek öncelikli görev paketlerini döner."""
    from curriculum import curriculum_engine, ExamLevel
    lvl = ExamLevel.from_str(exam_level)
    tasks = curriculum_engine.generate_next_research_tasks(count=count, exam_level=lvl)
    return {"total": len(tasks), "tasks": [t.model_dump() for t in tasks]}

@app.get("/api/curriculum/queue-stats")
async def get_curriculum_queue_statistics():
    """Canlı video kuyruğu metriklerini döner."""
    from curriculum import curriculum_queue
    return curriculum_queue.get_queue_stats()

# ==============================================================
# FAZ 2: OTONOM YOUTUBE KARADELİĞİ (HARVESTER) ENDPOINT'LERİ
# ==============================================================

@app.get("/api/harvester/status")
async def get_harvester_status():
    """Otonom YouTube karadeliğinin canlı çalışma durumunu döner."""
    from autonomous.harvester import youtube_harvester
    return youtube_harvester.get_status()

@app.post("/api/harvester/harvest-once")
async def trigger_harvest_single_task(
    exam_level: str = Query("ALL", description="LISANS, ONLISANS, ORTAOGRETIM veya ALL")
):
    """Müfredattan sıradaki bir görevi otonom olarak araştırıp YouTube'dan çeker."""
    from autonomous.harvester import youtube_harvester
    from curriculum import ExamLevel
    lvl = ExamLevel.from_str(exam_level)
    return await youtube_harvester.harvest_single_task(exam_level=lvl)

# ==============================================================
# FAZ 3: BİLİŞSEL ANALİST & HOCA ZİHNİYETİ ENDPOINT'LERİ
# ==============================================================

@app.get("/api/cognition/teachers")
async def list_all_teacher_profiles():
    """Modellenen tüm öğretmen profillerini döner."""
    from brain.database import db_session
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teacher_profiles ORDER BY videos_watched DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@app.get("/api/cognition/teacher/{name}")
async def get_teacher_profile(name: str):
    """Belirli bir öğretmenin zihin modelini ve kullandığı şifreleri döner."""
    from cognition.teacher_learner import teacher_learner
    return teacher_learner.get_or_create_profile(name)

@app.get("/api/cognition/mnemonics")
async def list_all_mnemonics():
    """Hafıza ambarında tespit edilmiş tüm KPSS kodlama ve şifrelerini döner."""
    from brain.database import db_session
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_records WHERE record_type = 'MNEMONIC' ORDER BY first_learned DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@app.get("/api/cognition/traps")
async def list_all_exam_traps():
    """Hafıza ambarında tespit edilmiş tüm ÖSYM çeldirici sınav tuzaklarını döner."""
    from brain.database import db_session
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_records WHERE record_type = 'TRAP' ORDER BY first_learned DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

# ==============================================================
# FAZ 4: KORELASYON GRAFI, ÇAPRAZ SENTEZ & AUDITOR ENDPOINT'LERİ
# ==============================================================

@app.get("/api/cognition/correlations")
async def get_correlations_graph(lesson: Optional[str] = Query(None)):
    """Kavramlar arası korelasyon grafiğini ve karıştırılan kavram çiftlerini döner."""
    from cognition.correlation_engine import correlation_engine
    correlation_engine.discover_correlations_from_db()
    stats = correlation_engine.get_graph_stats()
    pairs = correlation_engine.get_confused_pairs(lesson_filter=lesson)
    return {
        "stats": stats,
        "confused_pairs": pairs
    }

@app.post("/api/cognition/synthesize")
async def trigger_cross_teacher_synthesis(
    lesson: str = Query("COGRAFYA"),
    topic: str = Query("Türkiye'nin Fiziki Özellikleri, Jeolojik Yapısı ve Yer Şekilleri")
):
    """Belirli bir konuda çoklu hoca sentezi üretir."""
    from cognition.cross_teacher_analyzer import cross_teacher_analyzer
    return cross_teacher_analyzer.synthesize_master_topic_profile(lesson=lesson, topic=topic)

@app.get("/api/cognition/audit-report")
async def get_z3_audit_report():
    """Z3 SMT ve kanonik gerçeklik denetim raporunu döner."""
    from cognition.auditor import auditor_engine
    return auditor_engine.run_full_knowledge_audit()

# ==============================================================
# DEEPSEEK-R1 SAVCILIK VE DERİN ADVERSARIAL DENETİM ENDPOINT'LERİ
# ==============================================================

@app.post("/api/prosecutor/audit-claim")
async def deepseek_audit_single_claim(
    claim_text: str = Query(..., description="Denetlenecek hoca iddiası"),
    lesson: str = Query("GENEL", description="Ders adı"),
    topic: str = Query("Genel", description="Konu adı"),
    teacher: str = Query("Bilinmeyen", description="Eğitmen adı")
):
    """
    DeepSeek-R1'in Chain-of-Thought (<think>) muhakemesi ve Kanonik Gerçeklik
    ile iddiayı acımasızca denetler. Yanlışsa anında ÖSYM tuzağına dönüştürür.
    """
    from cognition.prosecutor_auditor import prosecutor_auditor
    return await prosecutor_auditor.audit_claim_deepseek(
        claim_text=claim_text,
        lesson=lesson,
        topic=topic,
        teacher=teacher
    )

@app.post("/api/prosecutor/adjudicate")
async def deepseek_adjudicate_teachers(
    lesson: str = Query("COGRAFYA"),
    topic: str = Query("Genel"),
    teacher_a: str = Query(..., description="1. Hoca Adı"),
    claim_a: str = Query(..., description="1. Hocanın İddiası"),
    teacher_b: str = Query(..., description="2. Hoca Adı"),
    claim_b: str = Query(..., description="2. Hocanın İddiası")
):
    """İki öğretmenin zıt düştüğü konularda DeepSeek-R1'i hakem yapar."""
    from cognition.prosecutor_auditor import prosecutor_auditor
    return await prosecutor_auditor.adjudicate_teacher_dispute(
        lesson=lesson,
        topic=topic,
        teacher_a=teacher_a,
        claim_a=claim_a,
        teacher_b=teacher_b,
        claim_b=claim_b
    )

@app.get("/api/prosecutor/recent-verdicts")
async def get_recent_prosecutor_verdicts(limit: int = Query(15, ge=1, le=50)):
    """DeepSeek-R1 savcılık motorunun verdiği son gerekçeli hükümleri döner."""
    from cognition.prosecutor_auditor import prosecutor_auditor
    return prosecutor_auditor.get_recent_audits(limit=limit)





