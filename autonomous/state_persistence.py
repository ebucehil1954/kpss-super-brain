"""
KPSS Super-Brain: Kalıcı Durum ve Checkpoint Yöneticisi (State Persistence Engine v3)
"Kapandığı yeri bilecek, tekrar açıldığında kaldığı yerden devam edecek."
SQLite tabanlı transaksiyonel oturum günlüğü, zombi görev kurtarma ve anlık hafıza checkpoint mekanizması.
"""
import os
import sqlite3
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from config import super_brain_config

class StatePersistenceEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(super_brain_config.ENGINE_STATE_DB_FILE)
        self.current_session_id = f"sess_{int(time.time()*1000)}"
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Oturum Tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS engine_sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    stopped_at TEXT,
                    stop_reason TEXT,
                    total_cycles INTEGER DEFAULT 0,
                    items_consumed INTEGER DEFAULT 0,
                    facts_stored INTEGER DEFAULT 0,
                    questions_minted INTEGER DEFAULT 0,
                    mnemonics_minted INTEGER DEFAULT 0
                )
            """)

            # Anlık Checkpoint Tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS engine_checkpoints (
                    checkpoint_key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Worker Nabız (Heartbeat) Tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS worker_heartbeats (
                    worker_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    current_task_info TEXT,
                    last_heartbeat TEXT NOT NULL
                )
            """)
            conn.commit()

    def record_session_start(self) -> str:
        """Yeni veya devam eden oturumu kaydeder."""
        now_str = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO engine_sessions (session_id, started_at)
                VALUES (?, ?)
            """, (self.current_session_id, now_str))
            conn.commit()
        return self.current_session_id

    def record_session_stop(self, reason: str = "GRACEFUL_SHUTDOWN", stats: Optional[Dict[str, Any]] = None):
        """Oturum kapanışını ve nihai metriklerini mühürler."""
        now_str = datetime.now().isoformat()
        stats = stats or {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE engine_sessions
                SET stopped_at = ?,
                    stop_reason = ?,
                    total_cycles = ?,
                    items_consumed = ?,
                    facts_stored = ?,
                    questions_minted = ?,
                    mnemonics_minted = ?
                WHERE session_id = ?
            """, (
                now_str,
                reason,
                stats.get("total_cycles", 0),
                stats.get("items_consumed", 0),
                stats.get("facts_stored", 0),
                stats.get("questions_minted", 0),
                stats.get("mnemonics_minted", 0),
                self.current_session_id
            ))
            conn.commit()

    def save_checkpoint(self, state_dict: Dict[str, Any]):
        """Motorun canlı durumunu ve kuyruk durumunu atomik olarak kaydeder."""
        now_str = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for key, val in state_dict.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO engine_checkpoints (checkpoint_key, value_json, updated_at)
                    VALUES (?, ?, ?)
                """, (key, json.dumps(val, ensure_ascii=False), now_str))
            conn.commit()

    def load_checkpoint(self) -> Dict[str, Any]:
        """Kapanan sistemin en son kaydedilmiş checkpoint verilerini geri yükler."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT checkpoint_key, value_json FROM engine_checkpoints")
            rows = cursor.fetchall()
            output = {}
            for k, v in rows:
                try:
                    output[k] = json.loads(v)
                except Exception:
                    output[k] = v
            return output

    def update_worker_heartbeat(self, worker_id: str, status: str, current_task: Optional[Dict[str, Any]] = None):
        """Worker'ın hayatta olduğunu ve ne üzerinde çalıştığını kaydeder."""
        now_str = datetime.now().isoformat()
        task_str = json.dumps(current_task, ensure_ascii=False) if current_task else ""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO worker_heartbeats (worker_id, status, current_task_info, last_heartbeat)
                VALUES (?, ?, ?, ?)
            """, (worker_id, status, task_str, now_str))
            conn.commit()

    def recover_zombie_tasks(self) -> int:
        """
        Elektrik kesintisi veya ani kapanma nedeniyle 'IN_PROGRESS' kalan
        tüm görevleri 'PENDING' durumuna geri döndürür. Hiçbir ders/video yarıda kaybolmaz.
        """
        recovered_count = 0
        task_db = str(super_brain_config.TASK_DB_FILE)
        
        if os.path.exists(task_db):
            with sqlite3.connect(task_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE autonomous_tasks
                    SET status = 'PENDING', started_at = NULL
                    WHERE status = 'IN_PROGRESS'
                """)
                recovered_count += cursor.rowcount
                conn.commit()

        # Video kuyruğu kontrolü
        brain_db = str(super_brain_config.BRAIN_DB_FILE)
        if os.path.exists(brain_db):
            with sqlite3.connect(brain_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE video_queue
                    SET status = 'QUEUED'
                    WHERE status = 'PROCESSING'
                """)
                recovered_count += cursor.rowcount
                conn.commit()

        return recovered_count

state_persistence = StatePersistenceEngine()
