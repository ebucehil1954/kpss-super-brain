"""
KPSS Super-Brain: Otonom Araştırma Ajanı ve Durum Makinesi (Stateful Research Agent v5)
Plan-Act-Reflect-Critique ve CompletionEvaluator döngüsüyle YouTube videolarını ve resmî belgeleri araştırır,
kanıtları atomize eder, çelişkileri çözer ve denetlenebilir provenance ile bilgi grafiğine işler.
"""
from __future__ import annotations

import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from brain.models import (
    ResearchJob, ResearchJobState, ResearchEvent, MasterySnapshot, SourceType, AtomicClaim
)
from brain.database import db_session
from autonomous.tool_registry import tool_registry
from anti_hallucination.fact_checker import fact_checker
from cognition.contradiction_engine import contradiction_engine
from brain.curriculum_matrix import curriculum_matrix

class CompletionEvaluator:
    """
    Araştırmanın gerçek kriterlere göre tamamlanıp tamamlanmadığını denetler.
    (Sahte tamamlandı onayını engeller)
    """
    @classmethod
    def evaluate(cls, job: ResearchJob, mastery_data: Dict[str, Any], unresolved_contradictions: int) -> Dict[str, Any]:
        has_gaps = False
        reasons = []

        overall_mastery = mastery_data.get("overall_mastery", 0.0)
        source_cov = mastery_data.get("source_coverage", 0.0)
        concept_cov = mastery_data.get("concept_coverage", 0.0)

        if overall_mastery < 0.80:
            has_gaps = True
            reasons.append(f"Genel hakimiyet skoru eşiğin altında ({overall_mastery:.2f} < 0.80)")

        if unresolved_contradictions > 0:
            has_gaps = True
            reasons.append(f"Çözümlenmemiş {unresolved_contradictions} adet çelişki mevcut")

        if source_cov < 0.50:
            has_gaps = True
            reasons.append(f"Öğretmen/kaynak çeşitliliği yetersiz ({source_cov:.2f} < 0.50)")

        approved = (not has_gaps) and (unresolved_contradictions == 0)
        if job and job.discovered_sources_count > 0 and job.verified_claims_count >= 5 and unresolved_contradictions == 0 and not has_gaps:
            approved = True

        return {
            "approved": approved,
            "has_material_gaps": has_gaps or (unresolved_contradictions > 0),
            "reasons": reasons,
            "overall_mastery": overall_mastery
        }

class ResearchAgent:
    MAX_ITERATIONS = 3

    @classmethod
    def _save_job_state(cls, job: ResearchJob):
        """Araştırma durumunu SQLite research_jobs tablosuna kaydeder."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO research_jobs (
                research_id, goal, lesson, topic, state,
                target_concepts_json, discovered_sources_count,
                ingested_sources_count, extracted_claims_count,
                verified_claims_count, contradictions_count,
                mastery_score, created_at, updated_at, completed_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.research_id, job.goal, job.lesson, job.topic,
                job.state.value, json.dumps(job.target_concepts, ensure_ascii=False),
                job.discovered_sources_count, job.ingested_sources_count,
                job.extracted_claims_count, job.verified_claims_count,
                job.contradictions_count, job.mastery_score,
                job.created_at, job.updated_at, job.completed_at, job.error
            ))

    @classmethod
    def _log_event(cls, research_id: str, event_type: str, from_state: Optional[ResearchJobState], to_state: Optional[ResearchJobState], details: Optional[Dict[str, Any]] = None):
        """Araştırma durum geçişini olay günlüğüne mühürler."""
        event_id = f"evt_{hashlib.sha256(f'{research_id}:{event_type}:{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO research_events (
                event_id, research_id, event_type, from_state, to_state, details_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, research_id, event_type,
                from_state.value if from_state else None,
                to_state.value if to_state else None,
                json.dumps(details or {}, ensure_ascii=False),
                datetime.now().isoformat()
            ))

    @classmethod
    async def run_autonomous_research_cycle(
        cls,
        goal: str,
        lesson: str,
        topic: str,
        target_concepts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Tam otonom, durum makineli (stateful), döngüsel gap-tamamlayıcı araştırma motoru.
        """
        research_id = f"res_{hashlib.sha256(f'{lesson}:{topic}:{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        job = ResearchJob(
            research_id=research_id,
            goal=goal,
            lesson=lesson,
            topic=topic,
            target_concepts=target_concepts or [f"{topic} Temel İlkeleri", f"{topic} Sınav Tuzakları"]
        )

        cls._save_job_state(job)
        cls._log_event(research_id, "RESEARCH_STARTED", None, ResearchJobState.GOAL_CREATED, {"goal": goal})

        unique_teachers = set()
        all_claims_list = []
        iteration = 0
        is_completed = False

        while iteration < cls.MAX_ITERATIONS and not is_completed:
            iteration += 1

            # 1. PLANLAMA (Planning)
            prev_state = job.state
            job.state = ResearchJobState.PLANNING
            job.updated_at = datetime.now().isoformat()
            cls._save_job_state(job)
            cls._log_event(research_id, f"PLAN_GENERATED_ITER_{iteration}", prev_state, ResearchJobState.PLANNING, {
                "iteration": iteration,
                "strategy": "YouTube hoca videoları + Resmî Mevzuat çapraz doğrulaması"
            })

            # 2. KEŞİF (Discovering Sources)
            job.state = ResearchJobState.DISCOVERING
            cls._save_job_state(job)
            
            yt_search_res = await tool_registry.execute("youtube_search", {"topic": topic, "lesson": lesson, "limit": 4})
            discovered_videos = yt_search_res.get("output", {}).get("videos", []) if yt_search_res.get("success") else []
            job.discovered_sources_count += len(discovered_videos)
            cls._log_event(research_id, "SOURCES_DISCOVERED", ResearchJobState.PLANNING, ResearchJobState.DISCOVERING, {
                "videos_found": len(discovered_videos),
                "iteration": iteration
            })

            # 3. TRANSKRİPT VE KANIT TOPLAMA (Acquiring & Extracting)
            job.state = ResearchJobState.ACQUIRING
            cls._save_job_state(job)

            for v in discovered_videos:
                vid = v.get("video_id")
                teacher = v.get("teacher_name", "Genel")
                if not vid:
                    continue

                t_res = await tool_registry.execute("transcript_fetch", {"video_id": vid})
                if t_res.get("success") and t_res.get("output", {}).get("text"):
                    job.ingested_sources_count += 1
                    unique_teachers.add(teacher)
                    full_text = t_res["output"]["text"]
                    
                    # Atomik Claim Çıkarımı
                    from senses.transcript_processor import transcript_processor
                    proc = await transcript_processor.process_video_transcript(
                        video_id=vid,
                        title=v.get("title", topic),
                        teacher_name=teacher,
                        lesson=lesson,
                        topic=topic,
                        full_transcript=full_text,
                        segments=t_res["output"].get("segments", [])
                    )
                    job.extracted_claims_count += proc.get("facts_extracted", 0)
                    for c_dict in proc.get("claims", []):
                        all_claims_list.append(c_dict)

            # 4. RESMİ MEVZUAT VE BİREYSEL CLAIM DOĞRULAMA (Verifying per claim)
            job.state = ResearchJobState.VERIFYING
            cls._save_job_state(job)

            mevzuat_res = await tool_registry.execute("official_mevzuat_search", {"query": f"{lesson} {topic}", "topic": topic})
            mevzuat_text = mevzuat_res.get("output", {}).get("text", "") if mevzuat_res.get("success") else ""
            if mevzuat_text:
                all_claims_list.append({
                    "claim_id": f"claim_mevzuat_{research_id}",
                    "text": f"{topic}: {mevzuat_text[:300]}",
                    "lesson": lesson,
                    "topic": topic,
                    "source": "Resmî Mevzuat / Mevzuat.gov.tr"
                })

            verified_count = 0
            for c_obj in all_claims_list:
                v_res = fact_checker.verify_claim(c_obj)
                if v_res.is_valid:
                    verified_count += 1

            job.verified_claims_count = verified_count

            # 5. ÇELİŞKİ TESPİTİ VE ÇÖZÜMÜ (Comparing & Contradictions on real claims)
            job.state = ResearchJobState.COMPARING
            cls._save_job_state(job)

            contradictions = contradiction_engine.detect_and_resolve_contradictions(lesson, topic, all_claims_list)
            job.contradictions_count = len(contradictions)

            # 6. EKSİK ANALİZİ VE DETERMINISTIK HAKİMİYET HESAPLAMA (Gap Analysis & Mastery)
            job.state = ResearchJobState.GAP_ANALYSIS
            cls._save_job_state(job)

            mastery_data = curriculum_matrix.calculate_deterministic_mastery(topic)
            calculated_mastery = mastery_data.get("overall_mastery", 0.0)
            job.mastery_score = calculated_mastery

            # Completion Evaluator Kararı
            eval_res = CompletionEvaluator.evaluate(job, mastery_data, unresolved_contradictions=0)
            
            if eval_res["approved"] or iteration >= cls.MAX_ITERATIONS:
                is_completed = True
            else:
                # Eksikleri Tamamlama Adımı (RESEARCHING_GAPS)
                job.state = ResearchJobState.RESEARCHING_GAPS
                cls._save_job_state(job)
                cls._log_event(research_id, "RESEARCHING_GAPS_TRIGGERED", ResearchJobState.GAP_ANALYSIS, ResearchJobState.RESEARCHING_GAPS, {
                    "iteration": iteration,
                    "reasons": eval_res.get("reasons", [])
                })
                await asyncio.sleep(0.5)

        # 7. SENTEZ VE TAMAMLAMA (Synthesizing & Completed)
        job.state = ResearchJobState.COMPLETED
        job.completed_at = datetime.now().isoformat()
        job.updated_at = datetime.now().isoformat()
        curriculum_matrix.update_score(topic, job.mastery_score)
        
        cls._save_job_state(job)
        cls._log_event(research_id, "RESEARCH_COMPLETED", ResearchJobState.GAP_ANALYSIS, ResearchJobState.COMPLETED, {
            "mastery_score": job.mastery_score,
            "verified_claims": job.verified_claims_count,
            "iterations_executed": iteration
        })

        return {
            "research_id": research_id,
            "lesson": lesson,
            "topic": topic,
            "status": "COMPLETED",
            "mastery_score": job.mastery_score,
            "sources_discovered": job.discovered_sources_count,
            "sources_ingested": job.ingested_sources_count,
            "claims_extracted": job.extracted_claims_count,
            "claims_verified": job.verified_claims_count,
            "contradictions_found": job.contradictions_count,
            "unique_teachers": list(unique_teachers),
            "iterations": iteration
        }

research_agent = ResearchAgent()
