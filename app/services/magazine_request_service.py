"""게스트 매거진 제보 저장. LLM 의존성 없음."""

import base64
import os
import re
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models.magazine_requests import PENDING_REVIEW, connect, fetch_request, fetch_requests, insert_request


_ROOT_DIR = Path(__file__).resolve().parents[2]
_LOCK = threading.Lock()
_DATA_URL = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+)$", re.DOTALL)
_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_MAX_PHOTO_BYTES = 2 * 1024 * 1024


def db_path() -> Path:
    override = os.getenv("MAGAZINE_REQUESTS_DB_PATH", "").strip()
    if override:
        return Path(override)
    return _ROOT_DIR / "output" / "magazine_requests.db"


def upload_dir() -> Path:
    override = os.getenv("MAGAZINE_UPLOAD_DIR", "").strip()
    if override:
        return Path(override)
    return _ROOT_DIR / "output" / "magazine_uploads"


def build_guide_source(row: Dict[str, object]) -> Dict[str, object]:
    """제보 한 건을 가이드 생성 입력으로 맞춘다."""
    country = str(row.get("country") or "").strip()
    city = str(row.get("city") or "").strip()
    nickname = str(row.get("nickname") or "").strip()
    author_type = str(row.get("author_type") or "")
    if author_type == "anonymous" or not nickname:
        author_label = "Anonymous"
    else:
        author_label = nickname
    destination = city if not country else "{0}, {1}".format(city, country)
    return {
        "request_id": int(row["id"]),
        "destination": destination,
        "keyword": str(row.get("place") or "").strip(),
        "country": country,
        "city": city,
        "author_label": author_label,
        "review": str(row.get("review") or ""),
        "photo_url": str(row.get("photo_url") or ""),
        "ready_for_one_click": str(row.get("status") or "") == PENDING_REVIEW,
    }


def _stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _decode_photo(photo_data: str) -> Tuple[bytes, str]:
    raw = (photo_data or "").strip()
    if len(raw) > _MAX_PHOTO_BYTES * 2:
        raise ValueError("photo is too large")
    match = _DATA_URL.match(raw)
    if match:
        mime = match.group(1).lower()
        payload = re.sub(r"\s+", "", match.group(2))
    else:
        mime = "image/jpeg"
        payload = re.sub(r"\s+", "", raw)
    if mime not in _EXT:
        raise ValueError("unsupported image type")
    try:
        blob = base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise ValueError("invalid photo data") from exc
    if not blob or len(blob) > _MAX_PHOTO_BYTES:
        raise ValueError("photo is too large")
    return blob, _EXT[mime]


def _store_photo(photo_data: str) -> Tuple[str, Path]:
    blob, ext = _decode_photo(photo_data)
    folder = upload_dir()
    folder.mkdir(parents=True, exist_ok=True)
    name = "{0}{1}".format(secrets.token_hex(8), ext)
    path = folder / name
    path.write_bytes(blob)
    return "magazine-uploads/{0}".format(name), path


def _with_source(row: Optional[Dict[str, object]]) -> Dict[str, object]:
    if not row:
        raise ValueError("magazine request was not stored")
    record = dict(row)
    record["guide_source"] = build_guide_source(record)
    return record


def create_magazine_request(payload: Dict[str, str]) -> Dict[str, object]:
    """제보를 저장하고 가이드 원천 필드를 붙여 반환한다."""
    photo_url = str(payload.get("photo_url") or "")
    photo_data = str(payload.get("photo_data") or "")
    saved: Optional[Path] = None
    if photo_data:
        photo_url, saved = _store_photo(photo_data)
    with _LOCK:
        conn = connect(db_path())
        try:
            request_id = insert_request(
                conn,
                author_type=str(payload["author_type"]),
                nickname=str(payload.get("nickname") or ""),
                email=str(payload.get("email") or ""),
                country=str(payload["country"]),
                city=str(payload["city"]),
                place=str(payload["place"]),
                review=str(payload["review"]),
                photo_url=photo_url,
                created_at=_stamp(),
            )
            row = fetch_request(conn, request_id)
        except Exception:
            if saved and saved.exists():
                saved.unlink()
            raise
        finally:
            conn.close()
    return _with_source(row)


def list_magazine_requests() -> List[Dict[str, object]]:
    with _LOCK:
        conn = connect(db_path())
        try:
            rows = fetch_requests(conn)
        finally:
            conn.close()
    return [_with_source(row) for row in rows]
