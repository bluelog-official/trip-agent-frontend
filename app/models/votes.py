"""votes SQLite 테이블. 글과 IP 조합은 한 행만 둔다."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


_SCHEMA = """
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (article_id, ip_address)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def insert_vote(conn: sqlite3.Connection, article_id: str, ip_address: str, created_at: str) -> bool:
    """새 표면 True. 같은 글·IP가 이미 있으면 False."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO votes (article_id, ip_address, created_at)
            VALUES (?, ?, ?)
            """,
            (article_id, ip_address, created_at),
        )
        created = conn.execute("SELECT changes()").fetchone()[0] == 1
        conn.execute("COMMIT")
        return created
    except Exception:
        conn.execute("ROLLBACK")
        raise


def count_for_article(conn: sqlite3.Connection, article_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS votes FROM votes WHERE article_id = ?",
        (article_id,),
    ).fetchone()
    return int(row["votes"]) if row else 0


def ip_has_vote(conn: sqlite3.Connection, article_id: str, ip_address: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM votes WHERE article_id = ? AND ip_address = ?",
        (article_id, ip_address),
    ).fetchone()
    return row is not None


def status_for_articles(
    conn: sqlite3.Connection,
    article_ids: Sequence[str],
    ip_address: str,
) -> List[Dict[str, object]]:
    """요청한 글 순서대로 추천 수와 이 IP의 투표 여부를 돌려준다."""
    if not article_ids:
        return []
    placeholders = ", ".join("?" for _ in article_ids)
    rows = conn.execute(
        """
        SELECT article_id,
               COUNT(*) AS votes,
               SUM(CASE WHEN ip_address = ? THEN 1 ELSE 0 END) AS mine
        FROM votes
        WHERE article_id IN ({0})
        GROUP BY article_id
        """.format(placeholders),
        (ip_address, *article_ids),
    ).fetchall()
    found = {row["article_id"]: row for row in rows}
    payload: List[Dict[str, object]] = []
    for article_id in article_ids:
        row = found.get(article_id)
        payload.append(
            {
                "article_id": article_id,
                "vote_count": int(row["votes"]) if row else 0,
                "voted": bool(row and int(row["mine"] or 0) > 0),
            }
        )
    return payload


def counts_between(
    conn: sqlite3.Connection,
    start: Optional[str],
    end: Optional[str],
) -> Dict[str, int]:
    """start < created_at <= end. 둘 다 없으면 전체 기간이다."""
    if start and end:
        rows = conn.execute(
            """
            SELECT article_id, COUNT(*) AS votes
            FROM votes
            WHERE created_at > ? AND created_at <= ?
            GROUP BY article_id
            """,
            (start, end),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT article_id, COUNT(*) AS votes FROM votes GROUP BY article_id"
        ).fetchall()
    return {str(row["article_id"]): int(row["votes"]) for row in rows}


def fetch_votes(conn: sqlite3.Connection) -> List[Tuple[int, str, str, str]]:
    rows = conn.execute(
        "SELECT id, article_id, ip_address, created_at FROM votes ORDER BY id"
    ).fetchall()
    return [(int(row["id"]), row["article_id"], row["ip_address"], row["created_at"]) for row in rows]
