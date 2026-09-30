"""magazine_requests SQLite 테이블. 신규 행은 PENDING_REVIEW, 팩트체크는 PENDING이다."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


PENDING_REVIEW = "PENDING_REVIEW"
PUBLISHED = "PUBLISHED"
FACT_PENDING = "PENDING"
FACT_VERIFIED = "VERIFIED"
FACT_REJECTED = "REJECTED"

_COLUMNS = (
    "id",
    "author_type",
    "nickname",
    "email",
    "country",
    "city",
    "place",
    "review",
    "photo_url",
    "transport_info",
    "discovery_story",
    "reference_urls",
    "status",
    "fact_check_status",
    "verification_note",
    "published_guide_id",
    "submit_language",
    "english_sha256",
    "korean_guide_id",
    "created_at",
)

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
    transport_info TEXT NOT NULL DEFAULT '',
    discovery_story TEXT NOT NULL DEFAULT '',
    reference_urls TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    fact_check_status TEXT NOT NULL DEFAULT 'PENDING',
    verification_note TEXT NOT NULL DEFAULT '',
    published_guide_id TEXT NOT NULL DEFAULT '',
    submit_language TEXT NOT NULL DEFAULT 'en',
    english_sha256 TEXT NOT NULL DEFAULT '',
    korean_guide_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

_ADDED_COLUMNS = {
    "transport_info": "TEXT NOT NULL DEFAULT ''",
    "discovery_story": "TEXT NOT NULL DEFAULT ''",
    "reference_urls": "TEXT NOT NULL DEFAULT ''",
    "fact_check_status": "TEXT NOT NULL DEFAULT 'PENDING'",
    "verification_note": "TEXT NOT NULL DEFAULT ''",
    "published_guide_id": "TEXT NOT NULL DEFAULT ''",
    "submit_language": "TEXT NOT NULL DEFAULT 'en'",
    "english_sha256": "TEXT NOT NULL DEFAULT ''",
    "korean_guide_id": "TEXT NOT NULL DEFAULT ''",
    "user_id": "INTEGER NOT NULL DEFAULT 0",
    "xrpl_tx_hash": "TEXT NOT NULL DEFAULT ''",
}

_WALLET_COLUMNS = _COLUMNS + ("user_id", "xrpl_tx_hash")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _ensure_columns(conn)
    return conn


def _ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(magazine_requests)")}
    for name, column_type in _ADDED_COLUMNS.items():
        if name not in existing:
            conn.execute(
                "ALTER TABLE magazine_requests ADD COLUMN {0} {1}".format(name, column_type)
            )


def _select_list() -> str:
    return ", ".join(_COLUMNS)


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
    transport_info: str,
    discovery_story: str,
    reference_urls: str,
    created_at: str,
    submit_language: str = "en",
) -> int:
    conn.execute("BEGIN IMMEDIATE")
    try:
        cursor = conn.execute(
            """
            INSERT INTO magazine_requests (
                author_type, nickname, email, country, city, place, review, photo_url,
                transport_info, discovery_story, reference_urls,
                status, fact_check_status, submit_language, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                transport_info,
                discovery_story,
                reference_urls,
                PENDING_REVIEW,
                FACT_PENDING,
                submit_language or "en",
                created_at,
            ),
        )
        request_id = int(cursor.lastrowid)
        conn.execute("COMMIT")
        return request_id
    except Exception:
        conn.execute("ROLLBACK")
        raise


def update_fact_check(
    conn: sqlite3.Connection,
    request_id: int,
    fact_check_status: str,
    verification_note: str,
) -> None:
    conn.execute(
        """
        UPDATE magazine_requests
        SET fact_check_status = ?, verification_note = ?
        WHERE id = ?
        """,
        (fact_check_status, verification_note, int(request_id)),
    )


def mark_published_editions(
    conn: sqlite3.Connection,
    request_id: int,
    guide_id: str,
    korean_guide_id: str,
    english_sha256: str,
) -> None:
    conn.execute(
        """
        UPDATE magazine_requests
        SET status = ?, published_guide_id = ?, korean_guide_id = ?, english_sha256 = ?
        WHERE id = ?
        """,
        (PUBLISHED, guide_id, korean_guide_id, english_sha256, int(request_id)),
    )


def mark_published(conn: sqlite3.Connection, request_id: int, guide_id: str) -> None:
    conn.execute(
        """
        UPDATE magazine_requests
        SET status = ?, published_guide_id = ?
        WHERE id = ?
        """,
        (PUBLISHED, guide_id, int(request_id)),
    )


def fetch_request(conn: sqlite3.Connection, request_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT {0} FROM magazine_requests WHERE id = ?".format(_select_list()),
        (int(request_id),),
    ).fetchone()
    return dict(row) if row else None


def fetch_by_guide_id(conn: sqlite3.Connection, guide_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT {0} FROM magazine_requests WHERE published_guide_id = ?".format(_select_list()),
        (guide_id,),
    ).fetchone()
    return dict(row) if row else None


def assign_owner(conn: sqlite3.Connection, email: str, user_id: int) -> int:
    """게스트 이메일과 같은 제보의 소유자를 가입 사용자로 바꾼다."""
    address = (email or "").strip().lower()
    if not address:
        return 0
    count = conn.execute(
        """
        SELECT COUNT(*) AS n FROM magazine_requests
        WHERE lower(email) = ? AND user_id != ?
        """,
        (address, int(user_id)),
    ).fetchone()["n"]
    conn.execute(
        """
        UPDATE magazine_requests
        SET user_id = ?
        WHERE lower(email) = ? AND user_id != ?
        """,
        (int(user_id), address, int(user_id)),
    )
    return int(count)


def fetch_owned_requests(
    conn: sqlite3.Connection,
    user_id: int,
    email: str,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT {0} FROM magazine_requests
        WHERE user_id = ? OR lower(email) = ?
        ORDER BY id DESC
        """.format(", ".join(_WALLET_COLUMNS)),
        (int(user_id), (email or "").strip().lower()),
    ).fetchall()
    return [dict(row) for row in rows]


def set_xrpl_tx_hash(conn: sqlite3.Connection, request_id: int, tx_hash: str) -> None:
    conn.execute(
        "UPDATE magazine_requests SET xrpl_tx_hash = ? WHERE id = ?",
        ((tx_hash or "").strip(), int(request_id)),
    )


def fetch_requests(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT {0} FROM magazine_requests ORDER BY id DESC".format(_select_list())
    ).fetchall()
    return [dict(row) for row in rows]
