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
    status TEXT NOT NULL DEFAULT 'PLANNED',
    category TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    contact_email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    store_description TEXT NOT NULL DEFAULT '',
    catalog_images TEXT NOT NULL DEFAULT '',
    offered_benefit TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 0,
    voucher_points INTEGER NOT NULL DEFAULT 50,
    guide_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS vouchers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    merchant_id INTEGER NOT NULL,
    voucher_code TEXT NOT NULL UNIQUE,
    qr_token TEXT NOT NULL,
    points_cost INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'ISSUED',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guide_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (user_id, guide_id)
);
"""

_USER_COLUMNS = {
    "display_name": "TEXT NOT NULL DEFAULT ''",
    "provider_subject": "TEXT NOT NULL DEFAULT ''",
}

_PARTNER_COLUMNS = {
    "category": "TEXT NOT NULL DEFAULT ''",
    "address": "TEXT NOT NULL DEFAULT ''",
    "contact_email": "TEXT NOT NULL DEFAULT ''",
    "phone": "TEXT NOT NULL DEFAULT ''",
    "store_description": "TEXT NOT NULL DEFAULT ''",
    "catalog_images": "TEXT NOT NULL DEFAULT ''",
    "offered_benefit": "TEXT NOT NULL DEFAULT ''",
    "is_active": "INTEGER NOT NULL DEFAULT 0",
    "voucher_points": "INTEGER NOT NULL DEFAULT 50",
    "guide_id": "TEXT NOT NULL DEFAULT ''",
    "created_at": "TEXT NOT NULL DEFAULT ''",
}

_PARTNER_SELECT = """
id, name, city, discount_rate, status, category, address, contact_email, phone,
store_description, catalog_images, offered_benefit, is_active, voucher_points,
guide_id, created_at
"""

_USER_SELECT = (
    "id, email, auth_provider, points_balance, created_at, display_name, provider_subject"
)


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _ensure_user_columns(conn)
    _ensure_partner_columns(conn)
    return conn


def _ensure_partner_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(partner_merchants)")}
    for name, column_type in _PARTNER_COLUMNS.items():
        if name not in existing:
            conn.execute(
                "ALTER TABLE partner_merchants ADD COLUMN {0} {1}".format(name, column_type)
            )


def _ensure_user_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    for name, column_type in _USER_COLUMNS.items():
        if name not in existing:
            conn.execute("ALTER TABLE users ADD COLUMN {0} {1}".format(name, column_type))


def fetch_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT {0} FROM users WHERE email = ?".format(_USER_SELECT),
        (email,),
    ).fetchone()
    return dict(row) if row else None


def fetch_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT {0} FROM users WHERE id = ?".format(_USER_SELECT),
        (int(user_id),),
    ).fetchone()
    return dict(row) if row else None


def fetch_user_by_subject(
    conn: sqlite3.Connection,
    auth_provider: str,
    provider_subject: str,
) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT {0} FROM users WHERE auth_provider = ? AND provider_subject = ?".format(_USER_SELECT),
        (auth_provider, provider_subject),
    ).fetchone()
    return dict(row) if row else None


def insert_user(
    conn: sqlite3.Connection,
    email: str,
    auth_provider: str,
    created_at: str,
    display_name: str = "",
    provider_subject: str = "",
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO users (
            email, auth_provider, points_balance, created_at, display_name, provider_subject
        ) VALUES (?, ?, 0, ?, ?, ?)
        """,
        (email, auth_provider or "email", created_at, display_name or "", provider_subject or ""),
    )
    return int(cursor.lastrowid)


def update_user_identity(
    conn: sqlite3.Connection,
    user_id: int,
    auth_provider: str,
    display_name: str,
    provider_subject: str,
) -> None:
    conn.execute(
        """
        UPDATE users
        SET auth_provider = ?, display_name = ?, provider_subject = ?
        WHERE id = ?
        """,
        (auth_provider, display_name or "", provider_subject or "", int(user_id)),
    )


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


def claim_point_logs(conn: sqlite3.Connection, user_id: int, email: str) -> int:
    """게스트 이메일의 적립 행을 가입 사용자에게 옮긴다. 같은 사유가 이미 있으면 중복 행은 버린다."""
    moved = 0
    rows = conn.execute(
        """
        SELECT id, user_id FROM point_logs
        WHERE lower(reporter_email) = ?
        """,
        (email,),
    ).fetchall()
    for row in rows:
        if int(row["user_id"]) == int(user_id):
            continue
        try:
            conn.execute(
                "UPDATE point_logs SET user_id = ? WHERE id = ?",
                (int(user_id), int(row["id"])),
            )
            moved += 1
        except sqlite3.IntegrityError:
            conn.execute("DELETE FROM point_logs WHERE id = ?", (int(row["id"]),))
    return moved


def sync_balance(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM point_logs WHERE user_id = ?",
        (int(user_id),),
    ).fetchone()
    total = int(row["total"] or 0)
    conn.execute(
        "UPDATE users SET points_balance = ? WHERE id = ?",
        (total, int(user_id)),
    )
    return total


def fetch_logs_for_user(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, user_id, reporter_email, amount, reason, article_id, created_at
        FROM point_logs
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (int(user_id),),
    ).fetchall()
    return [dict(row) for row in rows]


def insert_saved_guide(
    conn: sqlite3.Connection,
    user_id: int,
    guide_id: str,
    created_at: str,
) -> bool:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO saved_guides (user_id, guide_id, created_at)
        VALUES (?, ?, ?)
        """,
        (int(user_id), guide_id, created_at),
    )
    return cursor.rowcount == 1


def delete_saved_guide(conn: sqlite3.Connection, user_id: int, guide_id: str) -> None:
    conn.execute(
        "DELETE FROM saved_guides WHERE user_id = ? AND guide_id = ?",
        (int(user_id), guide_id),
    )


def fetch_saved_guides(conn: sqlite3.Connection, user_id: int) -> List[str]:
    rows = conn.execute(
        """
        SELECT guide_id FROM saved_guides
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (int(user_id),),
    ).fetchall()
    return [str(row["guide_id"]) for row in rows]


def fetch_partners(conn: sqlite3.Connection, active_only: bool = False) -> List[Dict[str, Any]]:
    sql = "SELECT {0} FROM partner_merchants".format(_PARTNER_SELECT)
    if active_only:
        sql += " WHERE is_active = 1 AND status = 'APPROVED'"
    sql += " ORDER BY id"
    rows = conn.execute(sql).fetchall()
    return [dict(row) for row in rows]


def fetch_partner(conn: sqlite3.Connection, partner_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT {0} FROM partner_merchants WHERE id = ?".format(_PARTNER_SELECT),
        (int(partner_id),),
    ).fetchone()
    return dict(row) if row else None


def insert_partner(conn: sqlite3.Connection, fields: Dict[str, Any]) -> int:
    cursor = conn.execute(
        """
        INSERT INTO partner_merchants (
            name, city, discount_rate, status, category, address, contact_email, phone,
            store_description, catalog_images, offered_benefit, is_active, voucher_points,
            guide_id, created_at
        ) VALUES (?, ?, ?, 'PENDING_APPROVAL', ?, ?, ?, ?, ?, ?, ?, 0, ?, '', ?)
        """,
        (
            fields["name"],
            fields["city"],
            float(fields.get("discount_rate") or 0),
            fields.get("category") or "",
            fields.get("address") or "",
            fields.get("contact_email") or "",
            fields.get("phone") or "",
            fields.get("store_description") or "",
            fields.get("catalog_images") or "",
            fields.get("offered_benefit") or "",
            int(fields.get("voucher_points") or 50),
            fields.get("created_at") or "",
        ),
    )
    return int(cursor.lastrowid)


def activate_partner(conn: sqlite3.Connection, partner_id: int, guide_id: str) -> None:
    conn.execute(
        """
        UPDATE partner_merchants
        SET status = 'APPROVED', is_active = 1, guide_id = ?
        WHERE id = ?
        """,
        (guide_id, int(partner_id)),
    )


def insert_voucher(
    conn: sqlite3.Connection,
    user_id: int,
    merchant_id: int,
    voucher_code: str,
    qr_token: str,
    points_cost: int,
    created_at: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO vouchers (
            user_id, merchant_id, voucher_code, qr_token, points_cost, status, created_at
        ) VALUES (?, ?, ?, ?, ?, 'ISSUED', ?)
        """,
        (int(user_id), int(merchant_id), voucher_code, qr_token, int(points_cost), created_at),
    )
    return int(cursor.lastrowid)


def fetch_voucher_by_code(conn: sqlite3.Connection, voucher_code: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT id, user_id, merchant_id, voucher_code, qr_token, points_cost, status, created_at
        FROM vouchers WHERE voucher_code = ?
        """,
        (voucher_code,),
    ).fetchone()
    return dict(row) if row else None


def fetch_vouchers_for_user(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, user_id, merchant_id, voucher_code, qr_token, points_cost, status, created_at
        FROM vouchers
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (int(user_id),),
    ).fetchall()
    return [dict(row) for row in rows]


def mark_voucher_redeemed(conn: sqlite3.Connection, voucher_id: int) -> None:
    conn.execute(
        "UPDATE vouchers SET status = 'REDEEMED' WHERE id = ? AND status = 'ISSUED'",
        (int(voucher_id),),
    )
