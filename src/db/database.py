import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database connections and queries."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self) -> None:
        """Initializes the database schema."""
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                
                c.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        start_time TEXT,
                        end_time TEXT,
                        recording_path TEXT,
                        summary TEXT
                    )
                ''')
                
                c.execute('''
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        timestamp TEXT,
                        event_type TEXT,
                        x INTEGER,
                        y INTEGER,
                        window_name TEXT,
                        FOREIGN KEY(session_id) REFERENCES sessions(id)
                    )
                ''')
                
                c.execute('''
                    CREATE TABLE IF NOT EXISTS screenshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        timestamp TEXT,
                        filepath TEXT,
                        trigger_type TEXT,
                        annotated_path TEXT,
                        ocr_text TEXT,
                        ai_description TEXT,
                        ui_elements TEXT,
                        FOREIGN KEY(session_id) REFERENCES sessions(id)
                    )
                ''')
                
                conn.commit()
                
                # Patch existing database to handle the column rename/addition
                try:
                    c.execute("ALTER TABLE screenshots ADD COLUMN ui_elements TEXT")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass # Column already exists
                    

            logger.info("Database initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def create_session(self) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute("INSERT INTO sessions (start_time) VALUES (?)", (now,))
            conn.commit()
            return c.lastrowid

    def end_session(self, session_id: int, recording_path: Optional[str] = None) -> None:
        with self._get_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute(
                "UPDATE sessions SET end_time = ?, recording_path = ? WHERE id = ?", 
                (now, recording_path, session_id)
            )
            conn.commit()

    def insert_event(self, session_id: int, event_type: str, x: int, y: int, window_name: str) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute(
                "INSERT INTO events (session_id, timestamp, event_type, x, y, window_name) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, now, event_type, x, y, window_name)
            )
            conn.commit()
            return c.lastrowid

    def insert_screenshot(self, session_id: int, filepath: str, trigger_type: str) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute(
                "INSERT INTO screenshots (session_id, timestamp, filepath, trigger_type) VALUES (?, ?, ?, ?)",
                (session_id, now, filepath, trigger_type)
            )
            conn.commit()
            return c.lastrowid

    def update_screenshot_analysis(self, screenshot_id: int, ocr_text: Optional[str] = None, 
                                   ai_description: Optional[str] = None, annotated_path: Optional[str] = None,
                                   ui_elements: Optional[str] = None) -> None:
        updates = []
        params = []
        
        if ocr_text is not None:
            updates.append("ocr_text = ?")
            params.append(ocr_text)
        if ai_description is not None:
            updates.append("ai_description = ?")
            params.append(ai_description)
        if annotated_path is not None:
            updates.append("annotated_path = ?")
            params.append(annotated_path)
        if ui_elements is not None:
            updates.append("ui_elements = ?")
            params.append(ui_elements)
            
        if not updates:
            return
            
        query = f"UPDATE screenshots SET {', '.join(updates)} WHERE id = ?"
        params.append(screenshot_id)
        
        with self._get_connection() as conn:
            conn.execute(query, tuple(params))
            conn.commit()

    def get_session(self, session_id: int) -> Dict[str, Any]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = c.fetchone()
            return dict(row) if row else {}

    def get_events(self, session_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM events WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
            return [dict(r) for r in c.fetchall()]

    def get_screenshots(self, session_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM screenshots WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
            return [dict(r) for r in c.fetchall()]

    def update_session_summary(self, session_id: int, summary: Any) -> None:
        if isinstance(summary, (list, dict)):
            summary = json.dumps(summary)
            
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE sessions SET summary = ? WHERE id = ?", (summary, session_id))
            conn.commit()
