"""
KPSS Super-Brain: Öğretmen Zihniyeti Dinamik Modelleme Motoru (Teacher Learner)
İzlenen her videodan sonra öğretmenin pedagojik tarzını, sık kullandığı kalıpları,
vurguladığı konuları ve soru tahmin geçmişini SQLite `teacher_profiles` tablosunda günceller.
"""
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from brain.database import db_session
from config import super_brain_config

class TeacherLearner:
    @classmethod
    def get_or_create_profile(cls, teacher_name: str, channel: str = "", lesson: str = "GENEL") -> Dict[str, Any]:
        """Öğretmenin mevcut profilini getirir veya yenisini başlatır."""
        teacher_id = re.sub(r'[^a-zA-Z0-9_]', '', teacher_name.lower().replace(' ', '_'))
        now_str = datetime.now().isoformat()
        
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM teacher_profiles WHERE teacher_id = ?", (teacher_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "teacher_id": row["teacher_id"],
                    "name": row["name"],
                    "channel": row["channel"],
                    "lesson": row["lesson"],
                    "videos_watched": row["videos_watched"],
                    "total_transcript_words": row["total_transcript_words"],
                    "teaching_patterns": json.loads(row["teaching_patterns_json"]),
                    "favorite_topics": json.loads(row["favorite_topics_json"]),
                    "mnemonics_used": json.loads(row["mnemonics_used_json"]),
                    "prediction_history": json.loads(row["prediction_history_json"]),
                    "reasoning_chains_count": row["reasoning_chains_count"],
                    "unique_facts_count": row["unique_facts_count"],
                    "trap_warnings_count": row["trap_warnings_count"],
                    "updated_at": row["updated_at"]
                }
            
            # Yeni profil
            init_profile = {
                "teacher_id": teacher_id,
                "name": teacher_name,
                "channel": channel or "YouTube",
                "lesson": lesson,
                "videos_watched": 0,
                "total_transcript_words": 0,
                "teaching_patterns": {
                    "anlatim_tarzi": "Ders anlatımı ve soru kalıbı vurgusu",
                    "anahtar_kaliplar": []
                },
                "favorite_topics": [],
                "mnemonics_used": [],
                "prediction_history": [],
                "reasoning_chains_count": 0,
                "unique_facts_count": 0,
                "trap_warnings_count": 0,
                "updated_at": now_str
            }
            
            cursor.execute("""
            INSERT INTO teacher_profiles (
                teacher_id, name, channel, lesson, videos_watched,
                total_transcript_words, teaching_patterns_json, favorite_topics_json,
                mnemonics_used_json, prediction_history_json, reasoning_chains_count,
                unique_facts_count, trap_warnings_count, updated_at
            ) VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?, ?, 0, 0, 0, ?)
            """, (
                teacher_id,
                teacher_name,
                channel or "YouTube",
                lesson,
                json.dumps(init_profile["teaching_patterns"], ensure_ascii=False),
                json.dumps(init_profile["favorite_topics"], ensure_ascii=False),
                json.dumps(init_profile["mnemonics_used"], ensure_ascii=False),
                json.dumps(init_profile["prediction_history"], ensure_ascii=False),
                now_str
            ))
            return init_profile

    @classmethod
    def update_profile_from_lecture(
        cls,
        teacher_name: str,
        lesson: str,
        topic: str,
        transcript_words_count: int,
        facts_count: int,
        mnemonics_count: int,
        reasoning_count: int,
        traps_count: int,
        channel: str = ""
    ) -> Dict[str, Any]:
        """Video işlendikten sonra profil metriklerini günceller."""
        prof = cls.get_or_create_profile(teacher_name, channel, lesson)
        now_str = datetime.now().isoformat()
        
        # Favori konuları güncelle
        favs = prof["favorite_topics"]
        found = False
        for item in favs:
            if item.get("topic") == topic:
                item["mention_count"] = item.get("mention_count", 0) + 1
                found = True
                break
        if not found:
            favs.append({"topic": topic, "mention_count": 1})
            
        favs.sort(key=lambda x: x.get("mention_count", 0), reverse=True)

        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE teacher_profiles
            SET videos_watched = videos_watched + 1,
                total_transcript_words = total_transcript_words + ?,
                favorite_topics_json = ?,
                reasoning_chains_count = reasoning_chains_count + ?,
                unique_facts_count = unique_facts_count + ?,
                trap_warnings_count = trap_warnings_count + ?,
                updated_at = ?
            WHERE teacher_id = ?
            """, (
                transcript_words_count,
                json.dumps(favs, ensure_ascii=False),
                reasoning_count,
                facts_count,
                traps_count,
                now_str,
                prof["teacher_id"]
            ))

        return cls.get_or_create_profile(teacher_name)

    @classmethod
    def get_all_profiles(cls) -> List[Dict[str, Any]]:
        """Tüm hoca profillerini listeler."""
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM teacher_profiles ORDER BY videos_watched DESC")
            rows = cursor.fetchall()
            return [cls.get_or_create_profile(r["name"]) for r in rows]

teacher_learner = TeacherLearner()
