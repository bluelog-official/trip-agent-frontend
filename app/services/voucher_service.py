"""포인트로 제휴 바우처를 발행하고, 매장 코드로 검증한다. LLM 의존성 없음."""

import hashlib
import hmac
import os
import secrets
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import rewards as reward_store
from app.services.qr_svg import qr_svg
from app.services.rewards_service import db_path


_LOCK = threading.Lock()
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 8


def _stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _secret() -> bytes:
    raw = os.getenv("VOUCHER_SECRET", "").strip() or os.getenv("OAUTH_TOKEN_SECRET", "").strip()
    return (raw or "bluelog-voucher").encode("utf-8")


def sign_voucher(code: str, merchant_id: int, user_id: int) -> str:
    message = "{0}.{1}.{2}".format(code, int(merchant_id), int(user_id))
    digest = hmac.new(_secret(), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:32]


def _new_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))


def _card(row: Dict[str, object], merchant: Optional[Dict[str, object]], balance: int = 0) -> Dict[str, object]:
    code = str(row.get("voucher_code") or "")
    token = str(row.get("qr_token") or "")
    payload = "{0}.{1}".format(code, token)
    return {
        "id": int(row["id"]),
        "merchant_id": int(row["merchant_id"]),
        "merchant_name": str((merchant or {}).get("name") or ""),
        "offered_benefit": str((merchant or {}).get("offered_benefit") or ""),
        "voucher_code": code,
        "qr_token": token,
        "qr_svg": qr_svg(payload),
        "points_cost": int(row.get("points_cost") or 0),
        "status": str(row.get("status") or ""),
        "points_balance": int(balance),
        "created_at": str(row.get("created_at") or ""),
    }


def list_vouchers(user_id: int) -> List[Dict[str, object]]:
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            rows = reward_store.fetch_vouchers_for_user(conn, int(user_id))
            cards = []
            for row in rows:
                merchant = reward_store.fetch_partner(conn, int(row["merchant_id"]))
                cards.append(_card(row, merchant))
        finally:
            conn.close()
    return cards


def claim_voucher(user_id: int, merchant_id: int) -> Dict[str, object]:
    """승인된 상점의 바우처를 포인트로 산다. 잔액이 부족하면 ValueError."""
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            conn.execute("BEGIN IMMEDIATE")
            merchant = reward_store.fetch_partner(conn, int(merchant_id))
            if not merchant or not merchant.get("is_active") or str(merchant.get("status") or "") != "APPROVED":
                raise LookupError(merchant_id)
            user = reward_store.fetch_user_by_id(conn, int(user_id))
            if not user:
                raise LookupError(user_id)
            cost = int(merchant.get("voucher_points") or 50)
            balance = int(user.get("points_balance") or 0)
            if balance < cost:
                raise ValueError("not enough points")
            code = ""
            voucher_id = 0
            for _ in range(5):
                candidate = _new_code()
                token = sign_voucher(candidate, int(merchant_id), int(user_id))
                try:
                    voucher_id = reward_store.insert_voucher(
                        conn,
                        int(user_id),
                        int(merchant_id),
                        candidate,
                        token,
                        cost,
                        _stamp(),
                    )
                    code = candidate
                    break
                except Exception:
                    if reward_store.fetch_voucher_by_code(conn, candidate):
                        continue
                    raise
            if not code:
                raise RuntimeError("voucher code was not issued")
            reward_store.insert_point_log(
                conn,
                int(user_id),
                str(user.get("email") or ""),
                -cost,
                "VOUCHER_CLAIM",
                code,
                _stamp(),
            )
            balance = reward_store.add_points(conn, int(user_id), -cost)
            stored = reward_store.fetch_voucher_by_code(conn, code)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()
    if not stored:
        raise RuntimeError("voucher was not stored")
    return _card(stored, merchant, balance)


def verify_voucher(voucher_code: str, qr_token: str = "", consume: bool = False) -> Dict[str, object]:
    code = str(voucher_code or "").strip().upper()
    token = str(qr_token or "").strip().lower()
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            row = reward_store.fetch_voucher_by_code(conn, code) if code else None
            if not row:
                return {
                    "valid": False,
                    "status": "UNKNOWN",
                    "store_name": "",
                    "offered_benefit": "",
                    "voucher_code": code,
                }
            expected = sign_voucher(code, int(row["merchant_id"]), int(row["user_id"]))
            if token and (len(token) != len(expected) or not hmac.compare_digest(token, expected)):
                return {
                    "valid": False,
                    "status": "INVALID",
                    "store_name": "",
                    "offered_benefit": "",
                    "voucher_code": code,
                }
            merchant = reward_store.fetch_partner(conn, int(row["merchant_id"]))
            status = str(row.get("status") or "")
            if status != "ISSUED":
                return {
                    "valid": False,
                    "status": status or "INVALID",
                    "store_name": str((merchant or {}).get("name") or ""),
                    "offered_benefit": str((merchant or {}).get("offered_benefit") or ""),
                    "voucher_code": code,
                }
            if consume:
                reward_store.mark_voucher_redeemed(conn, int(row["id"]))
                status = "REDEEMED"
            return {
                "valid": True,
                "status": status,
                "store_name": str((merchant or {}).get("name") or ""),
                "offered_benefit": str((merchant or {}).get("offered_benefit") or ""),
                "voucher_code": code,
            }
        finally:
            conn.close()
