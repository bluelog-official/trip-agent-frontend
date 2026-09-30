"""users, point_logs, partner_merchants SQLite 테이블."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    auth_provider TEXT NOT NULL DEFAULT 'email',
    points_balance INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS point_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    reporter_email TEXT NOT NULL DEFAULT '',
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    article_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (user_id, reason, article_id)
);

CREATE TABLE IF NOT EXISTS partner_merchants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    discount_rate REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'PLANNED'
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def fetch_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT id, email, auth_provider, points_balance, created_at FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    return dict(row) if row else None


def insert_user(
    conn: sqlite3.Connection,
    email: str,
    auth_provider: str,
    created_at: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO users (email, auth_provider, points_balance, created_at)
        VALUES (?, ?, 0, ?)
        """,
        (email, auth_provider or "email", created_at),
    )
    return int(cursor.lastrowid)


def add_points(conn: sqlite3.Connection, user_id: int, amount: int) -> int:
    conn.execute(
        "UPDATE users SET points_balance = points_balance + ? WHERE id = ?",
        (int(amount), int(user_id)),
    )
    row = conn.execute(
        "SELECT points_balance FROM users WHERE id = ?",
        (int(user_id),),
    ).fetchone()
    return int(row["points_balance"]) if row else 0


def insert_point_log(
    conn: sqlite3.Connection,
    user_id: int,
    reporter_email: str,
    amount: int,
    reason: str,
    article_id: str,
    created_at: str,
) -> Optional[int]:
    """같은 사용자·사유·글은 한 번만 적립한다. 이미 있으면 None."""
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO point_logs (
            user_id, reporter_email, amount, reason, article_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (int(user_id), reporter_email, int(amount), reason, article_id, created_at),
    )
    created = conn.execute("SELECT changes()").fetchone()[0] == 1
    if not created:
        return None
    return int(cursor.lastrowid)


def fetch_point_log(conn: sqlite3.Connection, log_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT id, user_id, reporter_email, amount, reason, article_id, created_at
        FROM point_logs WHERE id = ?
        """,
        (int(log_id),),
    ).fetchone()
    return dict(row) if row else None


def fetch_partners(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, name, city, discount_rate, status
        FROM partner_merchants
        ORDER BY id
        """
    ).fetchall()
    return [dict(row) for row in rows]
