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
