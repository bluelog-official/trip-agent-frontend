"""포인트 적립. LLM 의존성 없음. 같은 글·같은 사유는 한 번만 쌓인다."""

import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

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


def _public_image(raw: str) -> str:
    for line in str(raw or "").splitlines():
        url = line.strip()
        if url.startswith("https://") or url.startswith("http://"):
            return url
    return ""


def _public_partner(row: Dict[str, object]) -> Dict[str, object]:
    return {
        "id": int(row["id"]),
        "name": str(row.get("name") or ""),
        "city": str(row.get("city") or ""),
        "discount_rate": float(row.get("discount_rate") or 0),
        "status": str(row.get("status") or ""),
        "category": str(row.get("category") or ""),
        "address": str(row.get("address") or ""),
        "offered_benefit": str(row.get("offered_benefit") or ""),
        "store_description": str(row.get("store_description") or ""),
        "image_url": _public_image(str(row.get("catalog_images") or "")),
        "voucher_points": int(row.get("voucher_points") or 50),
    }


def overview() -> Dict[str, object]:
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            partners = [
                _public_partner(row) for row in reward_store.fetch_partners(conn, active_only=True)
            ]
        finally:
            conn.close()
    return {
        "publish_points": PUBLISH_POINTS,
        "top_rank_points": TOP_RANK_POINTS,
        "top_rank_limit": TOP_RANK_LIMIT,
        "auth_providers": ["google", "apple", "kakao"],
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


def link_social_account(
    email: str,
    provider: str,
    subject: str,
    name: str = "",
) -> Dict[str, object]:
    """같은 이메일의 게스트 적립을 소셜 계정으로 합치고 잔액을 로그 합계로 맞춘다."""
    address = str(email or "").strip().lower()
    provider_name = str(provider or "").strip().lower()
    subject_id = str(subject or "").strip()
    display = str(name or "").strip()
    if provider_name not in ("google", "apple", "kakao"):
        raise ValueError("unsupported provider")
    if not subject_id and not address:
        raise ValueError("email or subject is required")
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            conn.execute("BEGIN IMMEDIATE")
            user = reward_store.fetch_user_by_email(conn, address) if address else None
            if user is None and subject_id:
                user = reward_store.fetch_user_by_subject(conn, provider_name, subject_id)
            if user is None:
                if not address:
                    raise ValueError("email is required for a new account")
                user_id = reward_store.insert_user(
                    conn,
                    address,
                    provider_name,
                    _stamp(),
                    display,
                    subject_id,
                )
            else:
                user_id = int(user["id"])
                if not address:
                    address = str(user["email"]).strip().lower()
                reward_store.update_user_identity(
                    conn,
                    user_id,
                    provider_name,
                    display or str(user.get("display_name") or ""),
                    subject_id or str(user.get("provider_subject") or ""),
                )
            moved = reward_store.claim_point_logs(conn, user_id, address)
            balance = reward_store.sync_balance(conn, user_id)
            conn.execute("COMMIT")
            stored = reward_store.fetch_user_by_id(conn, user_id)
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()
    if not stored:
        raise ValueError("account was not stored")
    return {
        "id": int(stored["id"]),
        "email": str(stored["email"]),
        "auth_provider": str(stored["auth_provider"]),
        "display_name": str(stored.get("display_name") or ""),
        "provider_subject": str(stored.get("provider_subject") or ""),
        "points_balance": balance,
        "created_at": str(stored["created_at"]),
        "migrated_point_logs": int(moved),
    }


def load_user(user_id: int) -> Optional[Dict[str, object]]:
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            return reward_store.fetch_user_by_id(conn, int(user_id))
        finally:
            conn.close()


def point_history(user_id: int) -> List[Dict[str, object]]:
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            return reward_store.fetch_logs_for_user(conn, int(user_id))
        finally:
            conn.close()


def saved_guide_ids(user_id: int) -> List[str]:
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            return reward_store.fetch_saved_guides(conn, int(user_id))
        finally:
            conn.close()


def remember_guide(user_id: int, guide_id: str) -> List[str]:
    guide = str(guide_id or "").strip()
    if not guide:
        raise ValueError("guide_id is required")
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            reward_store.insert_saved_guide(conn, int(user_id), guide, _stamp())
            return reward_store.fetch_saved_guides(conn, int(user_id))
        finally:
            conn.close()


def forget_guide(user_id: int, guide_id: str) -> List[str]:
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            reward_store.delete_saved_guide(conn, int(user_id), str(guide_id or "").strip())
            return reward_store.fetch_saved_guides(conn, int(user_id))
        finally:
            conn.close()


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
