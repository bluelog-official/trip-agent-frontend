"""제휴 입점 신청과 승인. 승인 시 Partner Verified Magazine 파일을 쓴다."""

import re
import threading
from datetime import datetime, timezone
from typing import Dict, List

from app.models import rewards as reward_store
from app.services.magazine_request_service import guide_dir, store_upload
from app.services.rewards_service import db_path


_LOCK = threading.Lock()
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
VOUCHER_POINTS = 50


def _stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "partner"


def _city(address: str) -> str:
    part = str(address or "").split(",")[0].strip()
    return (part or "Local")[:80]


def _rate(benefit: str) -> float:
    match = _PERCENT.search(benefit or "")
    if not match:
        return 0.0
    return float(match.group(1))


def _application(row: Dict[str, object]) -> Dict[str, object]:
    return {
        "id": int(row["id"]),
        "store_name": str(row.get("name") or ""),
        "category": str(row.get("category") or ""),
        "address": str(row.get("address") or ""),
        "contact_email": str(row.get("contact_email") or ""),
        "phone": str(row.get("phone") or ""),
        "store_description": str(row.get("store_description") or ""),
        "catalog_images": str(row.get("catalog_images") or ""),
        "offered_benefit": str(row.get("offered_benefit") or ""),
        "city": str(row.get("city") or ""),
        "status": str(row.get("status") or "PENDING_APPROVAL"),
        "is_active": bool(row.get("is_active")),
        "voucher_points": int(row.get("voucher_points") or VOUCHER_POINTS),
        "guide_id": str(row.get("guide_id") or ""),
        "discount_rate": float(row.get("discount_rate") or 0),
        "created_at": str(row.get("created_at") or ""),
    }


def render_partner_magazine(row: Dict[str, object]) -> str:
    name = str(row.get("name") or "Partner")
    city = str(row.get("city") or "")
    category = str(row.get("category") or "")
    benefit = str(row.get("offered_benefit") or "")
    description = str(row.get("store_description") or "")
    address = str(row.get("address") or "")
    images = [line for line in str(row.get("catalog_images") or "").splitlines() if line.strip()]
    photos = "\n".join("![{0}]({1})".format(name, url) for url in images if url.startswith(("http://", "https://", "magazine-uploads/")))
    title = "{0} Partner Verified Magazine".format(name.replace('"', "'"))
    return """---
title: "{title}"
city: "{city}"
category: "{category}"
status: "Partner Verified Magazine"
partner: true
---
# {title}

{description}

## Benefit for guests

{benefit}

## Visit

{address}

{photos}
""".format(
        title=title,
        city=city.replace('"', "'"),
        category=category.replace('"', "'"),
        description=description,
        benefit=benefit,
        address=address,
        photos=photos,
    )


DEMO_CAFE_NAME = "BlueLog Travel Cafe"


def ensure_demo_cafe() -> int:
    """바우처 확인용 카페가 없으면 50포인트 승인 상점으로 넣는다."""
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            for row in reward_store.fetch_partners(conn, active_only=False):
                if str(row.get("name") or "").strip().lower() != DEMO_CAFE_NAME.lower():
                    continue
                partner_id = int(row["id"])
                if str(row.get("status") or "") != "APPROVED" or not row.get("is_active"):
                    guide_id = str(row.get("guide_id") or "").strip() or "bluelog_travel_cafe_partner_guide.md"
                    reward_store.activate_partner(conn, partner_id, guide_id)
                if int(row.get("voucher_points") or 0) != VOUCHER_POINTS:
                    conn.execute(
                        "UPDATE partner_merchants SET voucher_points = ? WHERE id = ?",
                        (VOUCHER_POINTS, partner_id),
                    )
                return partner_id
            partner_id = reward_store.insert_partner(
                conn,
                {
                    "name": DEMO_CAFE_NAME,
                    "city": "Seoul",
                    "discount_rate": 10,
                    "category": "Cafe",
                    "address": "Seoul",
                    "contact_email": "",
                    "phone": "",
                    "store_description": "BlueLog test cafe for point vouchers.",
                    "catalog_images": "",
                    "offered_benefit": "10% off a drink",
                    "voucher_points": VOUCHER_POINTS,
                    "created_at": _stamp(),
                },
            )
            reward_store.activate_partner(conn, partner_id, "bluelog_travel_cafe_partner_guide.md")
            return partner_id
        finally:
            conn.close()


def apply_partner(payload: Dict[str, str]) -> Dict[str, object]:
    images = str(payload.get("catalog_images") or "")
    catalog_data = str(payload.get("catalog_data") or "")
    if catalog_data:
        stored = store_upload(catalog_data)
        images = "\n".join(part for part in (images, stored) if part)
    fields = {
        "name": str(payload["store_name"]),
        "city": _city(str(payload.get("address") or "")),
        "discount_rate": _rate(str(payload.get("offered_benefit") or "")),
        "category": str(payload.get("category") or ""),
        "address": str(payload.get("address") or ""),
        "contact_email": str(payload.get("contact_email") or ""),
        "phone": str(payload.get("phone") or ""),
        "store_description": str(payload.get("store_description") or ""),
        "catalog_images": images,
        "offered_benefit": str(payload.get("offered_benefit") or ""),
        "voucher_points": VOUCHER_POINTS,
        "created_at": _stamp(),
    }
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            partner_id = reward_store.insert_partner(conn, fields)
            row = reward_store.fetch_partner(conn, partner_id)
        finally:
            conn.close()
    if not row:
        raise RuntimeError("partner application was not stored")
    return _application(row)


def list_partner_applications() -> List[Dict[str, object]]:
    with _LOCK:
        conn = reward_store.connect(db_path())
        try:
            rows = reward_store.fetch_partners(conn, active_only=False)
        finally:
            conn.close()
    return [_application(row) for row in rows]


def approve_partner(partner_id: int) -> Dict[str, object]:
    """PENDING_APPROVAL 상점을 승인하고 제휴 매거진 파일을 쓴다."""
    with _LOCK:
        conn = reward_store.connect(db_path())
        path = None
        activated = False
        try:
            row = reward_store.fetch_partner(conn, int(partner_id))
            if not row:
                raise LookupError(partner_id)
            if str(row.get("status") or "") == "APPROVED" and str(row.get("guide_id") or "").strip():
                raise ValueError("this store is already approved")
            if str(row.get("status") or "") not in {"PENDING_APPROVAL", "PLANNED"}:
                raise ValueError("only a pending store can be approved")
            guide_id = "{0}_partner_{1}_guide.md".format(_slug(str(row.get("name") or "")), int(partner_id))
            article = render_partner_magazine(row)
            folder = guide_dir()
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / guide_id
            path.write_text(article, encoding="utf-8")
            reward_store.activate_partner(conn, int(partner_id), guide_id)
            activated = True
            stored = reward_store.fetch_partner(conn, int(partner_id))
        except Exception:
            if path is not None and path.exists() and not activated:
                path.unlink()
            raise
        finally:
            conn.close()
    record = _application(stored)
    record["article_markdown"] = article
    return record
