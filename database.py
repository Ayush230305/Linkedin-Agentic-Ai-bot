import sqlite3
from datetime import datetime, timezone

DB_PATH = "linkpilot.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS post_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT
            )
        """)
        conn.commit()

def save_post(content: str, status: str, details: str = ""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO post_history (created_at, content, status, details) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), content, status, details[:1500])
        )
        conn.commit()

def recent_posts(limit: int = 10):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT created_at, content, status, details FROM post_history ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
