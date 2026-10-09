"""매거진, K-Culture, 제휴 상점의 Open Graph HTML. LLM 의존성 없음."""

import re
from html import escape
from pathlib import Path
from typing import Dict

from app.services.scheduler_service import GUIDES_DIR, OUTPUT_DIR, resolve_site_base_url


_IMAGE = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)")
_HEADING = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_FRONT_KEY = re.compile(r'^([A-Za-z0-9_]+):\s*"?([^"\n]+)"?\s*$', re.MULTILINE)
_GUIDE_ID = re.compile(r"^[a-z0-9_]+_guide\.md$")

K_CULTURE_PAGES = {
    "/k-culture": {
        "title": "Korea culture guides · BlueLog Trip",
        "description": "K-Food, K-Beauty, K-Pop, and neighborhood walks in Korea.",
        "theme": "",
    },
    "/k-culture/k-food": {
        "title": "K-Food guides · BlueLog Trip",
        "description": "Neighborhood meals and market stops from Korea city guides.",
        "theme": "k-food",
    },
    "/k-culture/k-beauty": {
        "title": "K-Beauty guides · BlueLog Trip",
        "description": "Beauty streets and shop routes from Korea city guides.",
        "theme": "k-beauty",
    },
    "/k-culture/k-pop": {
        "title": "K-Pop and culture guides · BlueLog Trip",
        "description": "Pop-culture stops and neighborhood walks in Korea.",
        "theme": "k-pop",
    },
    "/k-culture/k-trend": {
        "title": "K-Trend guides · BlueLog Trip",
        "description": "Current neighborhood routes and trend stops in Korea.",
        "theme": "k-trend",
    },
}

_THEME_TOKENS = {
    "k-food": ("k-food", "kfood"),
    "k-beauty": ("k-beauty", "kbeauty"),
    "k-pop": ("k-pop", "kpop"),
    "k-trend": ("k-trend", "ktrend", "heritage"),
}


def clean_public_path(raw: str) -> str:
    path = (raw or "/").split("?", 1)[0].split("#", 1)[0].strip()
    if not path.startswith("/"):
        path = "/{0}".format(path)
    if path != "/":
        path = path.rstrip("/") or "/"
    return path


def _frontmatter(markdown: str) -> Dict[str, str]:
    match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---", markdown or "")
    if not match:
        return {}
    found: Dict[str, str] = {}
    for key, value in _FRONT_KEY.findall(match.group(1)):
        found[key] = value.strip()
    return found


def _article_text(markdown: str, limit: int = 1200) -> str:
    """가이드 본문에서 크롤러가 읽는 문단을 모은다."""
    body = re.sub(r"^---[\s\S]*?---", "", markdown or "", count=1).strip()
    parts = []
    for block in re.split(r"\n\s*\n", body):
        line = " ".join(block.split())
        if not line or line.startswith("#") or line.startswith("!") or line.startswith("|"):
            continue
        if line.lower().startswith("*photo by") or line.lower().startswith("photo by"):
            continue
        parts.append(line)
        if sum(len(part) for part in parts) >= limit:
            break
    return " ".join(parts)[:limit]


def _paragraph(markdown: str) -> str:
    body = re.sub(r"^---[\s\S]*?---", "", markdown or "", count=1).strip()
    for block in re.split(r"\n\s*\n", body):
        line = " ".join(block.split())
        if not line or line.startswith("#") or line.startswith("!") or line.startswith("|"):
            continue
        return line[:240]
    return ""


def _abs_url(site_url: str, path: str) -> str:
    origin = (site_url or "").rstrip("/")
    if not origin:
        return path
    return "{0}{1}".format(origin, path if path.startswith("/") else "/{0}".format(path))


def _guide_path(guide_id: str) -> Path:
    for directory in (GUIDES_DIR, OUTPUT_DIR):
        candidate = directory / guide_id
        if candidate.is_file():
            return candidate
    return GUIDES_DIR / guide_id


def _read_guide(guide_id: str) -> str:
    path = _guide_path(guide_id)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _card_from_markdown(guide_id: str, markdown: str, site_url: str) -> Dict[str, str]:
    meta = _frontmatter(markdown)
    heading = _HEADING.search(markdown or "")
    title = meta.get("title") or (heading.group(1).strip() if heading else guide_id)
    description = _paragraph(markdown) or title
    image = meta.get("image_url") or ""
    if not image.startswith("http"):
        found = _IMAGE.search(markdown or "")
        image = found.group(1) if found else ""
    return {
        "title": "{0} · BlueLog Trip".format(title.replace(" · BlueLog Trip", "")),
        "description": description,
        "text": _article_text(markdown) or description,
        "image": image if image.startswith("http") else "",
        "url": _abs_url(site_url, "/guides/{0}".format(guide_id)),
        "type": "article",
    }


def _theme_cover(theme: str) -> str:
    tokens = _THEME_TOKENS.get(theme) or ()
    if not GUIDES_DIR.is_dir():
        return ""
    for path in sorted(GUIDES_DIR.glob("*_guide.md")):
        name = path.name.lower()
        if tokens and not any(token in name for token in tokens):
            continue
        markdown = _read_guide(path.name)
        image = _frontmatter(markdown).get("image_url") or ""
        if image.startswith("http"):
            return image
    return ""


def _partner_card(partner_id: int, site_url: str) -> Dict[str, str]:
    url = _abs_url(site_url, "/partners/{0}".format(partner_id))
    blank = {
        "title": "Partner shop · BlueLog Trip",
        "description": "An approved partner shop on BlueLog Trip.",
        "image": "",
        "url": url,
        "type": "website",
    }
    try:
        from app.models import rewards as reward_store
        from app.services.rewards_service import db_path

        database = db_path()
        if not database.is_file():
            return blank
        conn = reward_store.connect(database)
        try:
            row = reward_store.fetch_partner(conn, partner_id)
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 - 상점 조회 실패가 공유 카드를 막지 않는다
        return blank
    if not row or not row.get("is_active"):
        return blank
    name = str(row.get("name") or "Partner shop")
    city = str(row.get("city") or "")
    description = str(row.get("store_description") or row.get("offered_benefit") or "").strip()
    if not description:
        description = "Partner shop in {0}.".format(city) if city else "An approved partner shop on BlueLog Trip."
    image = ""
    for line in str(row.get("catalog_images") or "").splitlines():
        candidate = line.strip()
        if candidate.startswith("http://") or candidate.startswith("https://"):
            image = candidate
            break
    return {
        "title": "{0} · BlueLog Trip".format(name),
        "description": description[:240],
        "image": image,
        "url": url,
        "type": "website",
    }


def resolve_share_card(path: str, site_url: str = "") -> Dict[str, str]:
    """공개 경로의 제목, 설명, 이미지, 절대 URL."""
    origin = resolve_site_base_url(site_url) or "https://bluelogtrip.com"
    public_path = clean_public_path(path)
    guide_match = re.match(r"^/guides?/([^/]+)$", public_path)
    if guide_match:
        guide_id = guide_match.group(1)
        if _GUIDE_ID.match(guide_id):
            markdown = _read_guide(guide_id)
            if markdown:
                return _card_from_markdown(guide_id, markdown, origin)
    if public_path in K_CULTURE_PAGES:
        page = K_CULTURE_PAGES[public_path]
        return {
            "title": page["title"],
            "description": page["description"],
            "image": _theme_cover(page["theme"]),
            "url": _abs_url(origin, public_path),
            "type": "website",
        }
    partner_match = re.match(r"^/partners/(\d+)$", public_path)
    if partner_match:
        return _partner_card(int(partner_match.group(1)), origin)
    if public_path == "/events":
        return {
            "title": "Events & Rewards · BlueLog Trip",
            "description": "How guest reports earn points, and how partner shop vouchers work.",
            "image": "",
            "url": _abs_url(origin, "/events"),
            "type": "website",
        }
    return {
        "title": "BlueLog Trip - Curated Local City Guides",
        "description": "BlueLog Trip - Curated Local City Guides",
        "image": "",
        "url": _abs_url(origin, "/"),
        "type": "website",
    }


def _meta(attribute: str, key: str, content: str) -> str:
    value = (content or "").strip()
    if not value:
        return ""
    return '<meta {0}="{1}" content="{2}" />'.format(attribute, escape(key, quote=True), escape(value, quote=True))


def render_opengraph_html(path: str, site_url: str = "") -> str:
    """소셜 크롤러가 자바스크립트 없이 읽는 카드 HTML."""
    card = resolve_share_card(path, site_url)
    image = card.get("image") or ""
    if image.startswith("http://"):
        image = ""
    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8" />',
        "<title>{0}</title>".format(escape(card["title"])),
        _meta("name", "description", card["description"]),
        '<link rel="canonical" href="{0}" />'.format(escape(card["url"], quote=True)),
        _meta("property", "og:site_name", "BlueLog Trip"),
        _meta("property", "og:type", card.get("type") or "website"),
        _meta("property", "og:title", card["title"]),
        _meta("property", "og:description", card["description"]),
        _meta("property", "og:url", card["url"]),
        _meta("property", "og:image", image),
        _meta("name", "twitter:card", "summary_large_image" if image else "summary"),
        _meta("name", "twitter:title", card["title"]),
        _meta("name", "twitter:description", card["description"]),
        _meta("name", "twitter:image", image),
        "</head>",
        "<body>",
        "<article>",
        "<h1>{0}</h1>".format(escape(card["title"])),
        "<p>{0}</p>".format(escape(card.get("text") or card["description"])),
        "<p><a href=\"{0}\">{1}</a></p>".format(escape(card["url"], quote=True), escape(card["title"])),
        "</article>",
        "</body>",
        "</html>",
    ]
    return "\n".join(line for line in lines if line)
