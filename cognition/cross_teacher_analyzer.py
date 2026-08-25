"""
KPSS Super-Brain: Çapraz Öğretmen Karşılaştırma ve Uzman Sentez Motoru (Cross-Teacher Synthesizer)
"Farklı KPSS hocalarının aynı konuyu anlatış biçimlerini, ortak vurgularını, hafıza şifrelerini
ve sınav tuzaklarını tek bir uzman öğretmen zihninde birleştirir."
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from brain.knowledge_store import knowledge_store
from brain.reasoning_store import reasoning_store
from brain.database import db_session

class CrossTeacherAnalyzer:
    @classmethod
    def synthesize_master_topic_profile(cls, lesson: str, topic: str) -> Dict[str, Any]:
        """
        Belirli bir konu için tüm farklı öğretmenlerin ders kayıtlarını toplayıp
        kapsamlı bir 'KPSS Uzman Öğretmen Sentezi' oluşturur ve SQLite'a kaydeder.
        """
        records = knowledge_store.get_records_by_topic(lesson, topic, limit=250)
        chains = reasoning_store.get_chains_for_topic(lesson, topic)
        
        teachers_involved: Set[str] = set()
        video_ids_involved: Set[str] = set()
        
        consensus_facts: List[str] = []
        teacher_specific_insights: Dict[str, List[str]] = {}
        unified_traps: List[str] = []
        consolidated_mnemonics: List[Dict[str, Any]] = []

        # 1. topic_mastery tablosundan kayıtlı hoca ve video listesini çek
        try:
            from brain.curriculum_matrix import curriculum_matrix
            matched_id = curriculum_matrix._find_matching_topic_id(lesson, topic)
            with db_session() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT distinct_teachers_json, consumed_video_ids_json FROM topic_mastery WHERE topic_id = ?", (matched_id,))
                row = cursor.fetchone()
                if row:
                    for t in json.loads(row["distinct_teachers_json"]):
                        teachers_involved.add(t)
                    for v in json.loads(row["consumed_video_ids_json"]):
                        video_ids_involved.add(v)
        except Exception:
            pass

        # 2. Kayıtlı olguları, tuzakları ve şifreleri ayrıştır
        for r in records:
            rtype = r.get("record_type")
            text = r.get("text", "")
            sources = r.get("source_chain", [])
            
            for s in sources:
                t = s.get("teacher")
                v_id = s.get("video_id")
                if t:
                    teachers_involved.add(t)
                    if t not in teacher_specific_insights:
                        teacher_specific_insights[t] = []
                if v_id:
                    video_ids_involved.add(v_id)

            if rtype == "FACT":
                if text not in consensus_facts:
                    consensus_facts.append(text)
            elif rtype == "TEACHER_INSIGHT":
                teacher_tag = "Genel"
                for t in teachers_involved:
                    if t in text:
                        teacher_tag = t
                        break
                if teacher_tag not in teacher_specific_insights:
                    teacher_specific_insights[teacher_tag] = []
                teacher_specific_insights[teacher_tag].append(text)
            elif rtype == "TRAP":
                if text not in unified_traps:
                    unified_traps.append(text)
            elif rtype == "MNEMONIC":
                consolidated_mnemonics.append({
                    "mnemonic_text": text,
                    "lesson": lesson,
                    "topic": topic
                })

        # 3. Sentez Metni Oluştur
        now_str = datetime.now().isoformat()
        t_list = list(teachers_involved)
        t_count = len(t_list)

        master_summary = f"[{lesson} - {topic}] Konusunda {t_count} Farklı KPSS Eğitmeninin ({', '.join(t_list) if t_list else 'Müfredat Uzmanları'}) Karşılaştırmalı Sentezi:\n"
        master_summary += f"- Toplam {len(consensus_facts)} Doğrulanmış Olgu ve Kanun Maddesi\n"
        master_summary += f"- Toplam {len(unified_traps)} ÖSYM Sınav Çeldiricisi ve Tuzak Uyarısı\n"
        master_summary += f"- Toplam {len(consolidated_mnemonics)} Hafıza Şifresi ve Kodlama\n"
        master_summary += f"- Toplam {len(chains)} Farklı Soru Çözüm Mantık Stratejisi"

        synthesis_id = f"synth_{hashlib.md5((lesson + '_' + topic).encode('utf-8')).hexdigest()[:12]}"

        # 4. SQLite'a kaydet
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO expert_syntheses (
                synthesis_id, lesson, topic, teachers_involved_json, video_ids_json,
                consensus_facts_json, teacher_insights_json, unified_traps_json,
                consolidated_mnemonics_json, master_summary, synthesis_score,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(synthesis_id) DO UPDATE SET
                teachers_involved_json = excluded.teachers_involved_json,
                video_ids_json = excluded.video_ids_json,
                consensus_facts_json = excluded.consensus_facts_json,
                teacher_insights_json = excluded.teacher_insights_json,
                unified_traps_json = excluded.unified_traps_json,
                consolidated_mnemonics_json = excluded.consolidated_mnemonics_json,
                master_summary = excluded.master_summary,
                synthesis_score = excluded.synthesis_score,
                updated_at = excluded.updated_at
            """, (
                synthesis_id,
                lesson,
                topic,
                json.dumps(t_list, ensure_ascii=False),
                json.dumps(list(video_ids_involved), ensure_ascii=False),
                json.dumps(consensus_facts, ensure_ascii=False),
                json.dumps(teacher_specific_insights, ensure_ascii=False),
                json.dumps(unified_traps, ensure_ascii=False),
                json.dumps(consolidated_mnemonics, ensure_ascii=False),
                master_summary,
                min(1.0, 0.4 + (t_count * 0.15) + (len(consensus_facts) * 0.01)),
                now_str,
                now_str
            ))

        return {
            "synthesis_id": synthesis_id,
            "lesson": lesson,
            "topic": topic,
            "teachers_count": t_count,
            "teachers": t_list,
            "videos_count": len(video_ids_involved),
            "consensus_facts": consensus_facts,
            "teacher_insights": teacher_specific_insights,
            "unified_traps": unified_traps,
            "consolidated_mnemonics": consolidated_mnemonics,
            "reasoning_strategies": chains,
            "master_summary": master_summary
        }

    @classmethod
    def get_synthesis_for_topic(cls, lesson: str, topic: str) -> Optional[Dict[str, Any]]:
        """Kayıtlı sentezi veritabanından çeker, yoksa anlık üretir."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM expert_syntheses WHERE lesson = ? AND topic = ?", (lesson, topic))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d["teachers_involved"] = json.loads(d["teachers_involved_json"])
                d["video_ids"] = json.loads(d["video_ids_json"])
                d["consensus_facts"] = json.loads(d["consensus_facts_json"])
                d["teacher_insights"] = json.loads(d["teacher_insights_json"])
                d["unified_traps"] = json.loads(d["unified_traps_json"])
                d["consolidated_mnemonics"] = json.loads(d["consolidated_mnemonics_json"])
                return d

        return cls.synthesize_master_topic_profile(lesson, topic)

    @classmethod
    def get_all_syntheses(cls) -> List[Dict[str, Any]]:
        """Tüm kayıtlı hoca sentezlerini listeler."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM expert_syntheses ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["teachers_involved"] = json.loads(d["teachers_involved_json"])
                d["video_ids"] = json.loads(d["video_ids_json"])
                d["consensus_facts"] = json.loads(d["consensus_facts_json"])
                d["teacher_insights"] = json.loads(d["teacher_insights_json"])
                d["unified_traps"] = json.loads(d["unified_traps_json"])
                d["consolidated_mnemonics"] = json.loads(d["consolidated_mnemonics_json"])
                results.append(d)
            return results

cross_teacher_analyzer = CrossTeacherAnalyzer()
