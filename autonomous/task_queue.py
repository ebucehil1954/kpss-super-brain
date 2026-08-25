"""
KPSS Super-Brain: Otonom Görev Kuyruğu (Task Queue)
SQLite tabanlı, öncelik sıralamalı asenkron iş kuyruğu.
"""
import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import super_brain_config

class TaskQueue:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(super_brain_config.TASK_DB_FILE)
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS autonomous_tasks (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    priority INTEGER NOT NULL DEFAULT 5,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT
                )
            """)
            conn.commit()

    def enqueue_task(self, task_type: str, payload: Dict[str, Any], priority: int = 5) -> str:
        task_id = f"task_{int(datetime.now().timestamp()*1000)}"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO autonomous_tasks (id, task_type, payload, status, priority, created_at)
                VALUES (?, ?, ?, 'PENDING', ?, ?)
            """, (task_id, task_type, json.dumps(payload), priority, datetime.now().isoformat()))
            conn.commit()
        return task_id

    def fetch_next_pending_task(self) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, task_type, payload, priority, created_at
                FROM autonomous_tasks
                WHERE status = 'PENDING'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                task_id, task_type, payload_str, priority, created_at = row
                cursor.execute("""
                    UPDATE autonomous_tasks
                    SET status = 'IN_PROGRESS', started_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), task_id))
                conn.commit()
                return {
                    "id": task_id,
                    "task_type": task_type,
                    "payload": json.loads(payload_str),
                    "priority": priority,
                    "created_at": created_at
                }
        return None

    def mark_completed(self, task_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE autonomous_tasks
                SET status = 'COMPLETED', completed_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), task_id))
            conn.commit()

    def mark_failed(self, task_id: str, error_msg: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE autonomous_tasks
                SET status = 'FAILED', completed_at = ?, error_message = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), error_msg, task_id))
            conn.commit()

    def recover_zombies(self) -> int:
        """Yarım kalan IN_PROGRESS görevleri PENDING durumuna geri çeker."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE autonomous_tasks
                SET status = 'PENDING', started_at = NULL
                WHERE status = 'IN_PROGRESS'
            """)
            count = cursor.rowcount
            conn.commit()
            return count

task_queue = TaskQueue()
