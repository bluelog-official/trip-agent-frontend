"""게스트 매거진 제보 저장. LLM 의존성 없음."""

import base64
import os
import re
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models.magazine_requests import (
    FACT_VERIFIED,
    connect,
    fetch_by_guide_id,
    fetch_request,
    fetch_requests,
    insert_request,
    mark_published,
    update_fact_check,
)


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


def guide_dir() -> Path:
    override = os.getenv("MAGAZINE_GUIDE_DIR", "").strip()
    if override:
        return Path(override)
    return _ROOT_DIR / "output"


def build_guide_source(row: Dict[str, object]) -> Dict[str, object]:
    """제보 한 건을 가이드 생성 입력으로 맞춘다. VERIFIED 이고 초안이 없을 때만 원클릭이 열린다."""
    country = str(row.get("country") or "").strip()
    city = str(row.get("city") or "").strip()
    nickname = str(row.get("nickname") or "").strip()
    author_type = str(row.get("author_type") or "")
    if author_type == "anonymous" or not nickname:
        author_label = "Anonymous"
    else:
        author_label = nickname
    destination = city if not country else "{0}, {1}".format(city, country)
    fact_status = str(row.get("fact_check_status") or "PENDING")
    published_id = str(row.get("published_guide_id") or "").strip()
    return {
        "request_id": int(row["id"]),
        "destination": destination,
        "keyword": str(row.get("place") or "").strip(),
        "country": country,
        "city": city,
        "author_label": author_label,
        "review": str(row.get("review") or ""),
        "photo_url": str(row.get("photo_url") or ""),
        "transport_info": str(row.get("transport_info") or ""),
        "discovery_story": str(row.get("discovery_story") or ""),
        "reference_urls": str(row.get("reference_urls") or ""),
        "fact_check_status": fact_status,
        "ready_for_one_click": fact_status == FACT_VERIFIED and not published_id,
    }


def _slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "guest"


def guest_guide_id(row: Dict[str, object]) -> str:
    city = _slug(str(row.get("city") or "city"))
    return "{0}_guest_{1}_guide.md".format(city, int(row["id"]))


def _plain(value: object) -> str:
    return str(value).replace("{", "{{").replace("}", "}}")


def render_guest_magazine(row: Dict[str, object]) -> str:
    """검증된 제보의 교통·발굴·참고 주소를 매거진 본문에 넣는다. LLM을 호출하지 않는다."""
    source = build_guide_source(row)
    city = source["city"] or "City"
    place = source["keyword"] or "Place"
    country = source["country"]
    title = "{0} in {1}".format(place, city)
    transport = source["transport_info"] or "The guest did not add a transit note."
    discovery = source["discovery_story"] or "The guest did not add how they found this place."
    urls = [line for line in str(source["reference_urls"] or "").splitlines() if line.strip()]
    if urls:
        sources = "\n".join("- [{0}]({0})".format(url) for url in urls)
    else:
        sources = "No outside link was attached to this report."
    photo = source["photo_url"]
    photo_line = "\n![{0}]({1})\n".format(place, photo) if photo.startswith(("http://", "https://")) else ""
    return """---
title: "{title}"
city: "{city}"
country: "{country}"
status: "Guest source"
fact_check: "{fact}"
---
# {title}

{author} visited {place} in {destination}. This draft keeps the guest's own notes so the desk can publish them after review.
{photo}
## What the guest noticed

{review}

## Getting there

{transport}

## How this place was found

{discovery}

## References the guest used

{sources}

## Where to go

| Category | Recommended Location | Estimated Cost | Rating |
| --- | --- | --- | --- |
| Guest pick | {place} | Ask on site | Guest report |
""".format(
        title=_plain(title.replace('"', "'")),
        city=_plain(city.replace('"', "'")),
        country=_plain(country.replace('"', "'")),
        fact=_plain(source["fact_check_status"]),
        author=_plain(source["author_label"]),
        place=_plain(place),
        destination=_plain(source["destination"]),
        photo=_plain(photo_line),
        review=_plain(source["review"]),
        transport=_plain(transport),
        discovery=_plain(discovery),
        sources=_plain(sources),
    )


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
                transport_info=str(payload.get("transport_info") or ""),
                discovery_story=str(payload.get("discovery_story") or ""),
                reference_urls=str(payload.get("reference_urls") or ""),
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


def set_fact_check(request_id: int, fact_check_status: str, verification_note: str) -> Dict[str, object]:
    """어드민이 장소 실재 여부를 PENDING, VERIFIED, REJECTED로 남긴다."""
    with _LOCK:
        conn = connect(db_path())
        try:
            current = fetch_request(conn, request_id)
            if not current:
                raise LookupError(request_id)
            update_fact_check(conn, request_id, fact_check_status, verification_note)
            row = fetch_request(conn, request_id)
        finally:
            conn.close()
    return _with_source(row)


def find_request_by_guide(guide_id: str) -> Optional[Dict[str, object]]:
    with _LOCK:
        conn = connect(db_path())
        try:
            row = fetch_by_guide_id(conn, guide_id)
        finally:
            conn.close()
    if not row:
        return None
    return _with_source(row)


def publish_verified_request(request_id: int) -> Dict[str, object]:
    """VERIFIED 제보만 매거진 초안 파일로 반영한다."""
    with _LOCK:
        conn = connect(db_path())
        try:
            row = fetch_request(conn, request_id)
            if not row:
                raise LookupError(request_id)
            if str(row.get("fact_check_status") or "") != FACT_VERIFIED:
                raise ValueError("only verified requests can become a magazine draft")
            if str(row.get("published_guide_id") or "").strip():
                raise ValueError("this request already has a magazine draft")
            guide_id = guest_guide_id(row)
            article = render_guest_magazine(row)
            folder = guide_dir()
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / guide_id
            path.write_text(article, encoding="utf-8")
            mark_published(conn, request_id, guide_id)
            stored = fetch_request(conn, request_id)
        except Exception:
            raise
        finally:
            conn.close()
    record = _with_source(stored)
    record["article_markdown"] = article
    record["guide_id"] = guide_id
    return record
