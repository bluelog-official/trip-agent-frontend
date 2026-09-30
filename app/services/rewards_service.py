"""포인트 적립. LLM 의존성 없음. 같은 글·같은 사유는 한 번만 쌓인다."""

import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from app.models import rewards as reward_store
from app.services.magazine_request_service import find_request_by_guide


_ROOT_DIR = Path(__file__).resolve().parents[2]
_LOCK = threading.Lock()

PUBLISH_POINTS = 100
TOP_RANK_POINTS = 50
TOP_RANK_LIMIT = 5
REASON_PUBLISHED = "MAGAZINE_PUBLISHED"
REASON_TOP_RANK = "UGC_TOP_RANK_BONUS"

_AMOUNTS = {
    REASON_PUBLISHED: PUBLISH_POINTS,
    REASON_TOP_RANK: TOP_RANK_POINTS,
}


def db_path() -> Path:
    override = os.getenv("REWARDS_DB_PATH", "").strip()
    if override:
        return Path(override)
    return _ROOT_DIR / "output" / "rewards.db"


def _stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def overview() -> Dict[str, object]:
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            partners = reward_store.fetch_partners(conn)
        finally:
            conn.close()
    return {
        "publish_points": PUBLISH_POINTS,
        "top_rank_points": TOP_RANK_POINTS,
        "top_rank_limit": TOP_RANK_LIMIT,
        "auth_providers": ["google", "apple"],
        "partners": partners,
    }


def accrue_points(
    email: str,
    reason: str,
    article_id: str = "",
    auth_provider: str = "email",
) -> Optional[Dict[str, object]]:
    """이메일이 있는 제보자에게 포인트를 적립한다. 이미 같은 사유면 created는 False."""
    address = str(email or "").strip().lower()
    if not address or reason not in _AMOUNTS:
        return None
    amount = _AMOUNTS[reason]
    article = str(article_id or "").strip()
    provider = str(auth_provider or "email").strip() or "email"
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            conn.execute("BEGIN IMMEDIATE")
            user = reward_store.fetch_user_by_email(conn, address)
            if user is None:
                user_id = reward_store.insert_user(conn, address, provider, _stamp())
            else:
                user_id = int(user["id"])
            log_id = reward_store.insert_point_log(
                conn,
                user_id,
                address,
                amount,
                reason,
                article,
                _stamp(),
            )
            created = log_id is not None
            if created:
                balance = reward_store.add_points(conn, user_id, amount)
                stored = reward_store.fetch_point_log(conn, int(log_id))
            else:
                stored = None
                current = reward_store.fetch_user_by_email(conn, address)
                balance = int(current["points_balance"]) if current else 0
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()
    if not created or not stored:
        return {
            "id": 0,
            "user_id": user_id,
            "email": address,
            "amount": 0,
            "reason": reason,
            "article_id": article,
            "created_at": "",
            "created": False,
            "points_balance": balance,
        }
    return {
        "id": int(stored["id"]),
        "user_id": int(stored["user_id"]),
        "email": str(stored["reporter_email"]),
        "amount": int(stored["amount"]),
        "reason": str(stored["reason"]),
        "article_id": str(stored["article_id"]),
        "created_at": str(stored["created_at"]),
        "created": True,
        "points_balance": balance,
    }


def award_published_guide(guide_id: str) -> Optional[Dict[str, object]]:
    """정식 발행된 제보 매거진이면 제보자 이메일에 발행 포인트를 넣는다."""
    record = find_request_by_guide(guide_id)
    if not record:
        return None
    return accrue_points(
        str(record.get("email") or ""),
        REASON_PUBLISHED,
        article_id=guide_id,
    )


def award_top_rank(article_id: str) -> Optional[Dict[str, object]]:
    """Top ranks에 들어간 제보 매거진이면 보너스 포인트를 한 번 넣는다."""
    record = find_request_by_guide(article_id)
    if not record:
        return None
    return accrue_points(
        str(record.get("email") or ""),
        REASON_TOP_RANK,
        article_id=article_id,
    )
