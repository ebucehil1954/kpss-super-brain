"""
KPSS Super-Brain: Sadeleştirilmiş Veri Dışa Aktarım Modülü (JSON Exporter)
Yapay zekanın beynindeki tüm bilgi, mantık zincirleri ve öğretmen profillerini
en sade ve temiz formatta `data/exports/` dizinine otomatik olarak yazar.
"""
import os
import json
from typing import Dict, Any
from datetime import datetime
from config import super_brain_config
from brain.database import db_session
from brain.knowledge_store import knowledge_store
from brain.reasoning_store import reasoning_store

class DataExporter:
    EXPORTS_DIR = str(super_brain_config.EXPORTS_DIR)

    @classmethod
    def export_all(cls) -> Dict[str, str]:
        """Tüm zihin ambarını JSON formatında sade dosyalar halinde dışa aktarır."""
        os.makedirs(cls.EXPORTS_DIR, exist_ok=True)
        files_created = {}

        # 1. BİLGİ KAYITLARI (Knowledge Records)
        records = knowledge_store.get_all_records(limit=10000)
        kr_path = os.path.join(cls.EXPORTS_DIR, "knowledge_records.json")
        with open(kr_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        files_created["knowledge_records"] = kr_path

        # 2. MANTIK ZİNCİRLERİ (Reasoning Chains)
        chains = reasoning_store.get_all_chains(limit=2000)
        rc_path = os.path.join(cls.EXPORTS_DIR, "reasoning_chains.json")
        with open(rc_path, "w", encoding="utf-8") as f:
            json.dump(chains, f, ensure_ascii=False, indent=2)
        files_created["reasoning_chains"] = rc_path

        # 3. ÖĞRETMEN PROFİLLERİ (Teacher Profiles)
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM teacher_profiles")
            profiles = []
            for r in cursor.fetchall():
                profiles.append({
                    "teacher_id": r["teacher_id"],
                    "name": r["name"],
                    "channel": r["channel"],
                    "lesson": r["lesson"],
                    "videos_watched": r["videos_watched"],
                    "total_transcript_words": r["total_transcript_words"],
                    "teaching_patterns": json.loads(r["teaching_patterns_json"]),
                    "favorite_topics": json.loads(r["favorite_topics_json"]),
                    "mnemonics_used": json.loads(r["mnemonics_used_json"]),
                    "prediction_history": json.loads(r["prediction_history_json"]),
                    "reasoning_chains_count": r["reasoning_chains_count"],
                    "unique_facts_count": r["unique_facts_count"],
                    "trap_warnings_count": r["trap_warnings_count"],
                    "updated_at": r["updated_at"]
                })
        tp_path = os.path.join(cls.EXPORTS_DIR, "teacher_profiles.json")
        with open(tp_path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        files_created["teacher_profiles"] = tp_path

        # 4. VİDEO İZLEME VE LOG GEÇMİŞİ (Video Log)
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM video_queue ORDER BY watched_at DESC, created_at DESC LIMIT 1000")
            videos = []
            for r in cursor.fetchall():
                videos.append({
                    "video_id": r["video_id"],
                    "title": r["title"],
                    "channel": r["channel"],
                    "teacher_name": r["teacher_name"],
                    "lesson": r["lesson"],
                    "topic": r["topic"],
                    "status": r["status"],
                    "transcript_length": r["transcript_length"],
                    "chunks_extracted": r["chunks_extracted"],
                    "watched_at": r["watched_at"],
                    "created_at": r["created_at"]
                })
        vl_path = os.path.join(cls.EXPORTS_DIR, "video_log.json")
        with open(vl_path, "w", encoding="utf-8") as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)
        files_created["video_log"] = vl_path

        # 5. ÖĞRENME VE BEYİN İSTATİSTİKLERİ (Learning Stats)
        stats = knowledge_store.get_stats()
        stats["total_reasoning_chains"] = len(chains)
        stats["total_teacher_profiles"] = len(profiles)
        stats["exported_at"] = datetime.now().isoformat()
        
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as watched FROM video_queue WHERE status = 'WATCHED'")
            stats["total_videos_watched"] = cursor.fetchone()["watched"]
            cursor.execute("SELECT COUNT(*) as pending FROM video_queue WHERE status = 'PENDING'")
            stats["total_videos_pending"] = cursor.fetchone()["pending"]

        ls_path = os.path.join(cls.EXPORTS_DIR, "learning_stats.json")
        with open(ls_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        files_created["learning_stats"] = ls_path

        # 6. DOĞRULANMIŞ ŞİFRELER (Verified Mnemonics)
        from generators.mnemonic_engine import mnemonic_engine
        mn_path = os.path.join(cls.EXPORTS_DIR, "verified_mnemonics.json")
        with open(mn_path, "w", encoding="utf-8") as f:
            json.dump(mnemonic_engine.CURATED_MNEMONICS, f, ensure_ascii=False, indent=2)
        files_created["verified_mnemonics"] = mn_path

        return files_created

data_exporter = DataExporter()
