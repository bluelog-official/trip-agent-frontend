"""guides QA 칼럼과 guide_similarities 테이블. API 응답에는 연결하지 않는다."""

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple


_ROOT_DIR = Path(__file__).resolve().parents[2]

# 이미 있는 guides 행은 그대로 두고, 없는 칼럼만 ALTER로 붙인다.
_QA_COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("qa_score", "INTEGER NOT NULL DEFAULT 75"),
    ("rating_grade", "VARCHAR(10) NOT NULL DEFAULT 'B-'"),
    ("star_rating", "NUMERIC(3, 2) NOT NULL DEFAULT 3.00"),
    ("qa_reason", "TEXT"),
)

_CREATE_GUIDES = """
CREATE TABLE IF NOT EXISTS guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT
)
"""

_CREATE_SIMILARITIES = """
CREATE TABLE IF NOT EXISTS guide_similarities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_guide_id INTEGER NOT NULL,
    target_guide_id INTEGER NOT NULL,
    similarity_score FLOAT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_guide_id) REFERENCES guides(id),
    FOREIGN KEY (target_guide_id) REFERENCES guides(id)
)
"""


def db_path() -> Path:
    override = os.getenv("GUIDES_DB_PATH", "").strip()
    if override:
        return Path(override)
    return _ROOT_DIR / "output" / "guides.db"


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _row_count(conn: sqlite3.Connection, name: str) -> int:
    if not _table_exists(conn, name):
        return 0
    row = conn.execute("SELECT COUNT(*) AS rows FROM {0}".format(name)).fetchone()
    return int(row["rows"]) if row else 0


def _column_names(conn: sqlite3.Connection, table: str) -> List[str]:
    return [str(row[1]) for row in conn.execute("PRAGMA table_info({0})".format(table))]


def apply_migration(conn: sqlite3.Connection) -> Dict[str, Any]:
    """guides에 QA 칼럼을 더하고 guide_similarities를 만든다. 기존 행 수는 바꾸지 않는다."""
    conn.execute("PRAGMA foreign_keys = ON")
    guides_existed = _table_exists(conn, "guides")
    if guides_existed and "id" not in _column_names(conn, "guides"):
        raise RuntimeError("guides table has no id column; refusing to rewrite it")

    rows_before = _row_count(conn, "guides")
    similarities_existed = _table_exists(conn, "guide_similarities")
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(_CREATE_GUIDES)
        existing = set(_column_names(conn, "guides"))
        added: List[str] = []
        for name, column_type in _QA_COLUMNS:
            if name in existing:
                continue
            conn.execute("ALTER TABLE guides ADD COLUMN {0} {1}".format(name, column_type))
            added.append(name)
        if not _table_exists(conn, "guide_similarities"):
            conn.execute(_CREATE_SIMILARITIES)
        rows_after = _row_count(conn, "guides")
        if rows_after != rows_before:
            raise RuntimeError(
                "guides row count changed from {0} to {1}".format(rows_before, rows_after)
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return {
        "guides_created": not guides_existed,
        "columns_added": added,
        "similarities_created": not similarities_existed,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "columns": _column_names(conn, "guides"),
    }


def migrate_file(path: Path) -> Dict[str, Any]:
    conn = connect(path)
    try:
        return apply_migration(conn)
    finally:
        conn.close()
