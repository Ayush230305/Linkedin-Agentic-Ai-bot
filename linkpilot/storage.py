import json
import os
import sqlite3
import hashlib
import uuid
from dotenv import load_dotenv

load_dotenv()


def connect():
    db = os.getenv("LINKPILOT_DB", "linkpilot.db")
    conn = sqlite3.connect(db, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _row(row):
    if not row:
        return None
    d = dict(row)
    d["media"] = json.loads(d.get("media") or "[]")
    return d


def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                instruction TEXT NOT NULL,
                text TEXT NOT NULL,
                status TEXT NOT NULL,
                content_hash TEXT,
                post_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrate databases created before media support.
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(drafts)")]
        if "media" not in cols:
            conn.execute("ALTER TABLE drafts ADD COLUMN media TEXT DEFAULT '[]'")


def create_draft(owner, instruction, text, media=None):
    draft_id = uuid.uuid4().hex[:8]
    with connect() as conn:
        conn.execute(
            """INSERT INTO drafts (id, owner, instruction, text, status, media)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (draft_id, owner, instruction, text, json.dumps(media or [])),
        )
    return draft_id


def get_draft(draft_id, owner):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM drafts WHERE id=? AND owner=?", (draft_id, owner)
        ).fetchone()
    return _row(row)


def edit_draft(draft_id, owner, new_text):
    with connect() as conn:
        r = conn.execute(
            """UPDATE drafts SET text=?
               WHERE id=? AND owner=? AND status='pending'""",
            (new_text, draft_id, owner),
        )
        return r.rowcount == 1


def set_media(draft_id, owner, media):
    with connect() as conn:
        r = conn.execute(
            """UPDATE drafts SET media=?
               WHERE id=? AND owner=? AND status='pending'""",
            (json.dumps(media), draft_id, owner),
        )
        return r.rowcount == 1


def reject_draft(draft_id, owner):
    with connect() as conn:
        r = conn.execute(
            """UPDATE drafts SET status='rejected'
               WHERE id=? AND owner=? AND status='pending'""",
            (draft_id, owner),
        )
        return r.rowcount == 1


def reserve_for_publication(draft_id, owner):
    """Atomically claim a pending draft so it cannot be published twice."""
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM drafts WHERE id=? AND owner=? AND status='pending'",
            (draft_id, owner),
        ).fetchone()
        if not row:
            conn.rollback()
            return None
        digest = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        conn.execute(
            "UPDATE drafts SET status='publishing', content_hash=? WHERE id=?",
            (digest, draft_id),
        )
        conn.commit()
        return _row(row)
    finally:
        conn.close()


def finish_publication(draft_id, owner, post_id):
    with connect() as conn:
        r = conn.execute(
            """UPDATE drafts SET status='published', post_id=?
               WHERE id=? AND owner=? AND status='publishing'""",
            (post_id, draft_id, owner),
        )
        return r.rowcount == 1


def mark_publication_unknown(draft_id, owner):
    with connect() as conn:
        conn.execute(
            """UPDATE drafts SET status='unknown'
               WHERE id=? AND owner=? AND status='publishing'""",
            (draft_id, owner),
        )


def release_after_definite_failure(draft_id, owner):
    with connect() as conn:
        conn.execute(
            """UPDATE drafts SET status='pending'
               WHERE id=? AND owner=? AND status='publishing'""",
            (draft_id, owner),
        )