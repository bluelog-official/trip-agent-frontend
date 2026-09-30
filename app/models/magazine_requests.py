"""magazine_requests SQLite 테이블. 신규 행의 상태는 PENDING_REVIEW다."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


PENDING_REVIEW = "PENDING_REVIEW"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS magazine_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_type TEXT NOT NULL,
    nickname TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    place TEXT NOT NULL,
    review TEXT NOT NULL,
    photo_url TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at TEXT NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def insert_request(
    conn: sqlite3.Connection,
    author_type: str,
    nickname: str,
    email: str,
    country: str,
    city: str,
    place: str,
    review: str,
    photo_url: str,
    created_at: str,
) -> int:
    conn.execute("BEGIN IMMEDIATE")
    try:
        cursor = conn.execute(
            """
            INSERT INTO magazine_requests (
                author_type, nickname, email, country, city, place, review, photo_url, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                author_type,
                nickname,
                email,
                country,
                city,
                place,
                review,
                photo_url,
                PENDING_REVIEW,
                created_at,
            ),
        )
        request_id = int(cursor.lastrowid)
        conn.execute("COMMIT")
        return request_id
    except Exception:
        conn.execute("ROLLBACK")
        raise


def fetch_request(conn: sqlite3.Connection, request_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT id, author_type, nickname, email, country, city, place, review, photo_url, status, created_at
        FROM magazine_requests
        WHERE id = ?
        """,
        (int(request_id),),
    ).fetchone()
    return dict(row) if row else None


def fetch_requests(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, author_type, nickname, email, country, city, place, review, photo_url, status, created_at
        FROM magazine_requests
        ORDER BY id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]
