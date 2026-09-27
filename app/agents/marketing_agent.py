"""게시글 승인 이후 채널별 홍보 뼈대. 실제 게시는 Pinterest·Discord만 준비하고 Reddit은 초안만 남긴다."""

import os
import re
from typing import Any, Dict
from urllib.parse import quote

import requests

from app.services.marketing_service import save_marketing_alert
from app.services.reddit_draft_service import (
    build_reddit_draft,
    destination_from_guide_id,
    reddit_draft_needs_refresh,
)

_IMAGE_URL = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)")
_DEFAULT_SITE_URL = "https://bluelogtrip.com"


def _site_url() -> str:
    raw = os.getenv("SITE_URL", _DEFAULT_SITE_URL).strip().rstrip("/")
    if raw.startswith("[") or "://" not in raw:
        return _DEFAULT_SITE_URL
    return raw


def _as_dict(guide_data: Any) -> Dict[str, Any]:
    if isinstance(guide_data, dict):
        return guide_data
    dump = getattr(guide_data, "model_dump", None)
    if callable(dump):
        payload = dump()
        if isinstance(payload, dict):
            return payload
    return {}


def _syndication(guide_data: Dict[str, Any]) -> Dict[str, Any]:
    payload = guide_data.get("syndication") or {}
    return payload if isinstance(payload, dict) else {}


def _guide_title(guide_data: Dict[str, Any]) -> str:
    syndication = _syndication(guide_data)
    pin = syndication.get("pinterest") or {}
    reddit = syndication.get("reddit") or {}
    for value in (pin.get("pin_title"), reddit.get("title"), guide_data.get("id")):
        text = str(value or "").strip()
        if text:
            return text
    return "New guide"


def _guide_url(guide_data: Dict[str, Any]) -> str:
    guide_id = str(guide_data.get("id") or "").strip()
    if not guide_id:
        return _site_url()
    return "{0}/guide/{1}".format(_site_url(), quote(guide_id, safe=""))


def _first_image_url(guide_data: Dict[str, Any]) -> str:
    article = str(guide_data.get("article_markdown") or guide_data.get("content") or "")
    match = _IMAGE_URL.search(article)
    if not match:
        return ""
    return match.group(1)


def post_to_pinterest(guide_data: Any) -> Dict[str, Any]:
    """이미지와 요약을 Pinterest Pins API 페이로드로만 만든다. 토큰이 있어도 아직 전송하지 않는다."""
    payload = _as_dict(guide_data)
    syndication = _syndication(payload)
    pin = syndication.get("pinterest") or {}
    if not isinstance(pin, dict):
        pin = {}
    description = str(pin.get("description") or "").strip()
    if not description:
        teasers = syndication.get("social_teasers") or []
        if isinstance(teasers, list) and teasers:
            description = str(teasers[0]).strip()
    pin_body = {
        "board_id": os.getenv("PINTEREST_BOARD_ID", "").strip(),
        "title": str(pin.get("pin_title") or _guide_title(payload))[:100],
        "description": description[:500],
        "alt_text": str(pin.get("image_alt") or _guide_title(payload))[:500],
        "link": _guide_url(payload),
        "media_source": {
            "source_type": "image_url",
            "url": _first_image_url(payload),
        },
    }
    print("📌 [Marketing] Pinterest pin scaffold: {0}".format(pin_body["title"]))
    return {
        "ok": True,
        "skipped": True,
        "reason": "scaffold",
        "board_name": str(pin.get("board") or "travel"),
        "pin": pin_body,
    }


def send_discord_webhook(guide_data: Any) -> Dict[str, Any]:
    """DISCORD_WEBHOOK_URL이 있으면 새 글 발행 알림을 보낸다."""
    payload = _as_dict(guide_data)
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    message = "New guide published: {0}\n{1}".format(_guide_title(payload), _guide_url(payload))
    if not webhook:
        print("📣 [Marketing] Discord webhook skipped (DISCORD_WEBHOOK_URL missing)")
        return {"ok": False, "skipped": True, "reason": "DISCORD_WEBHOOK_URL missing"}
    try:
        response = requests.post(webhook, json={"content": message}, timeout=8)
    except requests.RequestException as exc:
        print("⚠️ [Marketing] Discord webhook 실패: {0}".format(exc))
        return {"ok": False, "skipped": False, "error": str(exc)}
    ok = response.status_code < 400
    if ok:
        print("📣 [Marketing] Discord webhook {0}".format(response.status_code))
    else:
        print("⚠️ [Marketing] Discord webhook {0}".format(response.status_code))
    return {"ok": ok, "skipped": False, "status_code": response.status_code}


def draft_reddit_post(guide_data: Any) -> Dict[str, Any]:
    """r/travel 등에 바로 올리지 않고 마크다운 초안을 관리자 알림으로 저장한다."""
    payload = _as_dict(guide_data)
    syndication = _syndication(payload)
    reddit = syndication.get("reddit") or {}
    if not isinstance(reddit, dict):
        reddit = {}
    subreddit = str(reddit.get("subreddit") or "travel").strip() or "travel"
    title = str(reddit.get("title") or _guide_title(payload)).strip()
    body = str(reddit.get("body") or "").strip()
    if reddit_draft_needs_refresh(title, body):
        guide_id = str(payload.get("id") or "").strip()
        destination = str(payload.get("destination") or destination_from_guide_id(guide_id)).strip()
        research = payload.get("research") if isinstance(payload.get("research"), dict) else {}
        refreshed = build_reddit_draft(
            destination=destination,
            attractions=list(research.get("attractions") or []),
            food_spots=list(research.get("food_spots") or []),
            local_tip=str(research.get("local_tip") or ""),
            currency=str(research.get("target_currency") or ""),
            article_markdown=str(payload.get("article_markdown") or payload.get("content") or ""),
        )
        subreddit = refreshed["subreddit"]
        title = refreshed["title"]
        body = refreshed["body"]
    guide_url = _guide_url(payload)
    markdown = "\n".join(
        [
            "## r/{0}".format(subreddit),
            "",
            "**{0}**".format(title),
            "",
            body,
            "",
            "Guide: {0}".format(guide_url),
            "",
        ]
    )
    guide_id = str(payload.get("id") or "").strip()
    saved = save_marketing_alert(
        guide_id=guide_id,
        channel="reddit_draft",
        title="r/{0}: {1}".format(subreddit, title),
        body=markdown,
    )
    print("📝 [Marketing] Reddit draft saved for {0}".format(guide_id or title))
    return {
        "ok": True,
        "posted": False,
        "subreddit": subreddit,
        "markdown": markdown,
        "alert": saved,
    }


def run_marketing_pipeline(guide_data: Any) -> Dict[str, Any]:
    """승인 응답을 막지 않도록 채널별 실패를 삼킨다."""
    steps = (
        ("pinterest", post_to_pinterest),
        ("discord", send_discord_webhook),
        ("reddit", draft_reddit_post),
    )
    results: Dict[str, Any] = {}
    for name, step in steps:
        try:
            results[name] = step(guide_data)
        except Exception as exc:  # noqa: BLE001 - 백그라운드 채널 실패가 승인을 되돌리면 안 된다
            print("⚠️ [Marketing] {0} 실패: {1}".format(name, exc))
            results[name] = {"ok": False, "error": str(exc)}
    return results
