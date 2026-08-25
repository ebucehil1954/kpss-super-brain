"""
KPSS Super-Brain: Otonom Araştırma Ajanı ve Durum Makinesi (Stateful Research Agent v6)
Plan-Act-Reflect-Critique, CompletionEvaluator, hedefe yönelik gap tamamlayıcı arama,
mükerrer video/claim önleme ve strict FAILED/COMPLETED durum kontratları ile çalışır.
"""
from __future__ import annotations

import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from brain.models import (
    ResearchJob, ResearchJobState, ResearchEvent, MasterySnapshot, SourceType, AtomicClaim, VerificationStatus
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
    REQUIRED_MASTERY_THRESHOLD = 0.80
    REQUIRED_CONCEPT_COVERAGE = 0.80
    REQUIRED_SOURCE_COVERAGE = 0.50

    @classmethod
    def evaluate(cls, job: Optional[ResearchJob], mastery_data: Dict[str, Any], unresolved_contradictions: int = 0) -> Dict[str, Any]:
        has_gaps = False
        reasons = []

        overall_mastery = mastery_data.get("overall_mastery", 0.0)
        source_cov = mastery_data.get("source_coverage", 0.0)
        concept_cov = mastery_data.get("concept_coverage", 0.0)

        if overall_mastery < cls.REQUIRED_MASTERY_THRESHOLD:
            has_gaps = True
            reasons.append(f"Genel hakimiyet skoru eşiğin altında ({overall_mastery:.2f} < {cls.REQUIRED_MASTERY_THRESHOLD})")

        if unresolved_contradictions > 0:
            has_gaps = True
            reasons.append(f"Çözümlenmemiş {unresolved_contradictions} adet yüksek öncelikli çelişki mevcut")

        if source_cov < cls.REQUIRED_SOURCE_COVERAGE:
            has_gaps = True
            reasons.append(f"Öğretmen/kaynak çeşitliliği yetersiz ({source_cov:.2f} < {cls.REQUIRED_SOURCE_COVERAGE})")

        if concept_cov < cls.REQUIRED_CONCEPT_COVERAGE:
            has_gaps = True
            reasons.append(f"Kavram doluluk oranı yetersiz ({concept_cov:.2f} < {cls.REQUIRED_CONCEPT_COVERAGE})")

        approved = (not has_gaps) and (unresolved_contradictions == 0)

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
        Hard Invariant: COMPLETED yalnızca ve yalnızca CompletionEvaluator.approved == True olduğunda atanabilir.
        """
        research_id = f"res_{hashlib.sha256(f'{lesson}:{topic}:{datetime.now().isoformat()}'.encode()).hexdigest()[:12]}"
        concepts = target_concepts or [f"{topic} Temel İlkeleri", f"{topic} Sınav Tuzakları", f"{topic} Yargı Kararları"]
        
        job = ResearchJob(
            research_id=research_id,
            goal=goal,
            lesson=lesson,
            topic=topic,
            target_concepts=concepts
        )

        cls._save_job_state(job)
        cls._log_event(research_id, "RESEARCH_STARTED", None, ResearchJobState.GOAL_CREATED, {"goal": goal})

        seen_video_ids: set[str] = set()
        claims_by_id: Dict[str, Dict[str, Any]] = {}
        unique_teachers = set()
        iteration = 0
        is_completed = False
        final_status = "FAILED"

        try:
            while iteration < cls.MAX_ITERATIONS and not is_completed:
                iteration += 1

                # 1. PLANLAMA (Planning via TargetedResearchPlanner)
                prev_state = job.state
                job.state = ResearchJobState.PLANNING
                job.updated_at = datetime.now().isoformat()
                cls._save_job_state(job)

                from autonomous.gap_analyzer import gap_analyzer
                from autonomous.research_planner import research_planner
                
                cur_gap_report = gap_analyzer.analyze_gaps(
                    lesson=lesson,
                    topic=topic,
                    target_concepts=concepts,
                    claims=list(claims_by_id.values()),
                    teachers=list(unique_teachers)
                )
                plan = research_planner.create_research_plan(
                    lesson=lesson,
                    topic=topic,
                    gap_report=cur_gap_report,
                    iteration=iteration
                )

                cls._log_event(research_id, f"PLAN_GENERATED_ITER_{iteration}", prev_state, ResearchJobState.PLANNING, {
                    "iteration": iteration,
                    "priority": plan.get("priority", "MEDIUM"),
                    "queries": plan.get("queries", []),
                    "strategy": plan.get("strategy", "")
                })

                # 2. KEŞİF (Discovering Sources based on Targeted Plan)
                job.state = ResearchJobState.DISCOVERING
                cls._save_job_state(job)
                
                # Arama sorgusu: Hedefli araştırma planından alınan öncelikli sorgu
                search_query = plan["queries"][0] if plan.get("queries") else topic
                yt_search_res = await tool_registry.execute("youtube_search", {"topic": search_query, "lesson": lesson, "limit": 4})
                discovered_raw = yt_search_res.get("output", {}).get("videos", []) if yt_search_res.get("success") else []
                
                # Mükerrer Video Filtreleme (P0-05)
                new_videos = [v for v in discovered_raw if v.get("video_id") and v.get("video_id") not in seen_video_ids]
                for v in new_videos:
                    seen_video_ids.add(v["video_id"])

                job.discovered_sources_count += len(new_videos)
                cls._log_event(research_id, "SOURCES_DISCOVERED", ResearchJobState.PLANNING, ResearchJobState.DISCOVERING, {
                    "search_query": search_query,
                    "plan_priority": plan.get("priority", "MEDIUM"),
                    "videos_found": len(new_videos),
                    "iteration": iteration
                })

                # 3. TRANSKRİPT VE KANIT TOPLAMA (Acquiring & Extracting)
                job.state = ResearchJobState.ACQUIRING
                cls._save_job_state(job)

                for v in new_videos:
                    vid = v.get("video_id")
                    teacher = v.get("teacher_name", "Genel")
                    if not vid:
                        continue

                    t_res = await tool_registry.execute("transcript_fetch", {"video_id": vid})
                    if t_res.get("success") and t_res.get("output", {}).get("text"):
                        job.ingested_sources_count += 1
                        unique_teachers.add(teacher)
                        full_text = t_res["output"]["text"]

                        # Müfredat matrisine video tüketimini işle
                        curriculum_matrix.record_video_consumption(
                            lesson=lesson,
                            topic=topic,
                            video_id=vid,
                            teacher_name=teacher,
                            channel_name=v.get("channel", "YouTube")
                        )
                        
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
                        
                        # Claim Deduplication (P0-06)
                        for c_dict in proc.get("claims", []):
                            c_id = c_dict.get("claim_id")
                            if c_id and c_id not in claims_by_id:
                                claims_by_id[c_id] = c_dict
                                job.extracted_claims_count += 1

                # 4. RESMİ MEVZUAT VE BİREYSEL CLAIM DOĞRULAMA (Verifying per claim)
                job.state = ResearchJobState.VERIFYING
                cls._save_job_state(job)

                mevzuat_res = await tool_registry.execute("official_mevzuat_search", {"query": f"{lesson} {topic}", "topic": topic})
                mevzuat_text = mevzuat_res.get("output", {}).get("text", "") if mevzuat_res.get("success") else ""
                if mevzuat_text:
                    m_cid = f"claim_mevzuat_{hashlib.sha256(mevzuat_text[:100].encode()).hexdigest()[:10]}"
                    if m_cid not in claims_by_id:
                        claims_by_id[m_cid] = {
                            "claim_id": m_cid,
                            "text": f"{topic}: {mevzuat_text[:300]}",
                            "lesson": lesson,
                            "topic": topic,
                            "source": "Resmî Mevzuat / Mevzuat.gov.tr",
                            "evidence_refs": [{
                                "source_id": "src_official_mevzuat",
                                "source_type": "OFFICIAL_LEGISLATION",
                                "snippet": mevzuat_text[:300],
                                "url": "https://www.mevzuat.gov.tr"
                            }]
                        }
                        job.extracted_claims_count += 1

                all_claims_list = list(claims_by_id.values())
                verified_count = 0
                for c_obj in all_claims_list:
                    # Verified iddialar gereksiz tekrar doğrulanmaz
                    if c_obj.get("verification_status") in [VerificationStatus.VERIFIED, "VERIFIED"]:
                        verified_count += 1
                        continue

                    v_res = fact_checker.verify_claim(c_obj)
                    c_obj["verification_status"] = v_res.status
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

                from autonomous.gap_analyzer import gap_analyzer
                gap_analysis_data = gap_analyzer.analyze_gaps(
                    lesson=lesson,
                    topic=topic,
                    target_concepts=concepts,
                    claims=all_claims_list,
                    teachers=list(unique_teachers)
                )

                mastery_data = curriculum_matrix.calculate_deterministic_mastery(topic)
                calculated_mastery = mastery_data.get("overall_mastery", 0.0)
                job.mastery_score = calculated_mastery

                # Gerçek Çözümlenmemiş Çelişki Sayısı (P0-02)
                unresolved = contradiction_engine.count_unresolved_high_severity(lesson, topic)

                # Completion Evaluator Kararı (Hard Invariant)
                eval_res = CompletionEvaluator.evaluate(job, mastery_data, unresolved_contradictions=unresolved)
                
                if eval_res["approved"] and not gap_analysis_data["has_material_gaps"]:
                    # YALNIZCA approved == True olduğunda COMPLETED state'ine geçilebilir!
                    job.state = ResearchJobState.COMPLETED
                    job.completed_at = datetime.now().isoformat()
                    final_status = "COMPLETED"
                    is_completed = True
                elif iteration < cls.MAX_ITERATIONS:
                    # Eksikleri Gerçek Arama ile Tamamlama Adımı (P0-04: RESEARCHING_GAPS)
                    job.state = ResearchJobState.RESEARCHING_GAPS
                    cls._save_job_state(job)
                    gap_query = gap_analysis_data["recommended_queries"][0] if gap_analysis_data.get("recommended_queries") else concepts[iteration % len(concepts)]
                    cls._log_event(research_id, "RESEARCHING_GAPS_TRIGGERED", ResearchJobState.GAP_ANALYSIS, ResearchJobState.RESEARCHING_GAPS, {
                        "iteration": iteration,
                        "target_gap_concept": gap_query,
                        "gap_status": gap_analysis_data["gap_status"],
                        "reasons": eval_res.get("reasons", [])
                    })
                else:
                    # P0-01: MAX_ITERATIONS aşıldı ve onay alınamadıysa kesinlikle FAILED üretilir!
                    job.state = ResearchJobState.FAILED
                    job.error = f"MAX_ITERATIONS_REACHED: Araştırma onay kriterlerini karşılayamadı ({'; '.join(eval_res.get('reasons', []))})"
                    final_status = "FAILED"
                    is_completed = True

            # 7. SON DURUMU KAYDET
            job.updated_at = datetime.now().isoformat()
            if final_status == "COMPLETED":
                curriculum_matrix.update_score(topic, job.mastery_score)
                cls._log_event(research_id, "RESEARCH_COMPLETED", ResearchJobState.GAP_ANALYSIS, ResearchJobState.COMPLETED, {
                    "mastery_score": job.mastery_score,
                    "verified_claims": job.verified_claims_count,
                    "iterations_executed": iteration
                })
            else:
                cls._log_event(research_id, "RESEARCH_FAILED", ResearchJobState.GAP_ANALYSIS, ResearchJobState.FAILED, {
                    "error": job.error,
                    "mastery_score": job.mastery_score,
                    "iterations_executed": iteration
                })

            cls._save_job_state(job)

        except Exception as e:
            # Beklenmeyen istisnalarda (timeout, tool error vb.) ASLA COMPLETED üretilmez!
            job.state = ResearchJobState.FAILED
            job.error = f"RESEARCH_EXCEPTION: {str(e)}"
            final_status = "FAILED"
            job.updated_at = datetime.now().isoformat()
            cls._save_job_state(job)
            cls._log_event(research_id, "RESEARCH_EXCEPTION", job.state, ResearchJobState.FAILED, {"error": str(e)})

        return {
            "research_id": research_id,
            "lesson": lesson,
            "topic": topic,
            "status": final_status,
            "mastery_score": job.mastery_score,
            "sources_discovered": job.discovered_sources_count,
            "sources_ingested": job.ingested_sources_count,
            "claims_extracted": job.extracted_claims_count,
            "claims_verified": job.verified_claims_count,
            "contradictions_found": job.contradictions_count,
            "unique_teachers": list(unique_teachers),
            "iterations": iteration,
            "error": job.error
        }

research_agent = ResearchAgent()
