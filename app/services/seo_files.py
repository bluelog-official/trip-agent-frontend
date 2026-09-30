"""ads.txt와 robots.txt. LLM 의존성 없음."""

import os
import re
from pathlib import Path

from app.services.scheduler_service import resolve_site_base_url, sitemap_public_url


_ROOT = Path(__file__).resolve().parents[2]
FALLBACK_ADS_TXT = _ROOT / "frontend" / "public" / "ads.txt"
ADS_TXT_CERT = "f08c47fec0942fa0"
DEFAULT_SITEMAP_ORIGIN = "https://bluelogtrip.com"
_PUBLISHER = re.compile(r"^(?:ca-)?pub-(\d{10,20})$", re.IGNORECASE)
_ADS_LINE = re.compile(
    r"^google\.com,\s*(pub-\d{10,20}),\s*DIRECT,\s*f08c47fec0942fa0\s*$",
    re.IGNORECASE,
)


def normalize_publisher_id(raw: str) -> str:
    """ca-pub- 또는 pub- 계정을 ads.txt용 pub- 숫자로 맞춘다."""
    value = (raw or "").strip()
    if not value or value.startswith("%") or "VITE_" in value:
        return ""
    match = _PUBLISHER.match(value)
    if not match:
        return ""
    return "pub-{0}".format(match.group(1))


def publisher_id_from_env() -> str:
    for key in ("VITE_ADSENSE_PUBLISHER_ID", "ADSENSE_PUBLISHER_ID", "VITE_ADSENSE_CLIENT_ID"):
        found = normalize_publisher_id(os.getenv(key, ""))
        if found:
            return found
    return ""


def ads_txt_line(publisher_id: str) -> str:
    publisher = normalize_publisher_id(publisher_id)
    if not publisher:
        return ""
    return "google.com, {0}, DIRECT, {1}".format(publisher, ADS_TXT_CERT)


def _fallback_ads_line() -> str:
    try:
        text = FALLBACK_ADS_TXT.read_text(encoding="utf-8")
    except OSError:
        return ""
    for raw in text.splitlines():
        line = raw.strip()
        if _ADS_LINE.match(line):
            return line
    return ""


def ads_txt_body() -> str:
    """환경변수 계정이 있으면 그 줄, 없으면 공개 ads.txt, 둘 다 없으면 비활성 주석."""
    line = ads_txt_line(publisher_id_from_env()) or _fallback_ads_line()
    if not line:
        return "# ads.txt disabled: set VITE_ADSENSE_PUBLISHER_ID\n"
    return "{0}\n".format(line)


def robots_txt_body(site_url: str = "") -> str:
    """모든 크롤러를 허용하고 공개 sitemap 주소를 적는다."""
    origin = resolve_site_base_url(site_url) or DEFAULT_SITEMAP_ORIGIN
    sitemap = sitemap_public_url(origin)
    return "User-agent: *\nAllow: /\n\nSitemap: {0}\n".format(sitemap)
