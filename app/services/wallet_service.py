"""포인트 지갑. 잔액, 적립 내역, 제보 상태, 저장한 매거진. LLM 의존성 없음."""

import re
from typing import Dict, List

from app.services.magazine_request_service import owned_requests
from app.services.rewards_service import forget_guide, point_history, remember_guide, saved_guide_ids


_GUIDE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,180}$")
_XRPL_EXPLORER = "https://livenet.xrpl.org/transactions/{0}"


def publish_state(status: str, fact_check_status: str) -> str:
    if str(status or "") == "PUBLISHED":
        return "PUBLISHED"
    if str(fact_check_status or "") == "VERIFIED":
        return "VERIFIED"
    if str(fact_check_status or "") == "REJECTED":
        return "REJECTED"
    return "PENDING"


def xrpl_explorer_url(tx_hash: str) -> str:
    clean = str(tx_hash or "").strip()
    if not clean:
        return ""
    return _XRPL_EXPLORER.format(clean)


def _report(row: Dict[str, object]) -> Dict[str, object]:
    tx_hash = str(row.get("xrpl_tx_hash") or "")
    status = str(row.get("status") or "")
    fact = str(row.get("fact_check_status") or "")
    return {
        "id": int(row["id"]),
        "place": str(row.get("place") or ""),
        "city": str(row.get("city") or ""),
        "guest_email": str(row.get("email") or ""),
        "publish_state": publish_state(status, fact),
        "fact_check_status": fact or "PENDING",
        "status": status or "PENDING_REVIEW",
        "published_guide_id": str(row.get("published_guide_id") or ""),
        "xrpl_tx_hash": tx_hash,
        "xrpl_url": xrpl_explorer_url(tx_hash),
    }


def wallet_for_user(user: Dict[str, object]) -> Dict[str, object]:
    user_id = int(user["id"])
    email = str(user.get("email") or "")
    logs = [
        {
            "id": int(row["id"]),
            "amount": int(row["amount"]),
            "reason": str(row["reason"]),
            "article_id": str(row.get("article_id") or ""),
            "created_at": str(row.get("created_at") or ""),
        }
        for row in point_history(user_id)
    ]
    reports = [_report(row) for row in owned_requests(email, user_id)]
    return {
        "user_id": user_id,
        "email": email,
        "name": str(user.get("display_name") or ""),
        "auth_provider": str(user.get("auth_provider") or ""),
        "points_balance": int(user.get("points_balance") or 0),
        "logs": logs,
        "reports": reports,
        "saved_guides": saved_guide_ids(user_id),
    }


def save_guide(user_id: int, guide_id: str) -> List[str]:
    guide = str(guide_id or "").strip()
    if not _GUIDE_ID.match(guide):
        raise ValueError("guide_id is invalid")
    return remember_guide(int(user_id), guide)


def remove_saved_guide(user_id: int, guide_id: str) -> List[str]:
    return forget_guide(int(user_id), str(guide_id or "").strip())
