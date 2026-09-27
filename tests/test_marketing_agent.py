"""승인 이후 마케팅 뼈대. Reddit은 게시하지 않고 초안 알림만 저장한다."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.agents.marketing_agent import (
    draft_reddit_post,
    post_to_pinterest,
    run_marketing_pipeline,
    send_discord_webhook,
)
from app.main import app
from app.services import stats_service
from app.services.auth_service import issue_admin_token


GUIDE = {
    "id": "kyoto_guide.md",
    "article_markdown": "![Fushimi](https://images.example/kyoto.jpg)\n\n## Walk\n",
    "syndication": {
        "social_teasers": ["A short Kyoto walk"],
        "platform_hashtags": ["#travel"],
        "reddit": {
            "subreddit": "travel",
            "title": "Kyoto without the main-strip rush",
            "body": "We started at Fushimi before the tour groups.",
        },
        "quora": {"question": "Kyoto?", "answer": "Walk first."},
        "pinterest": {
            "board": "City walks",
            "pin_title": "Kyoto walking day",
            "description": "One quiet route through Kyoto.",
            "image_alt": "Torii gates in Kyoto",
        },
        "backlink": {
            "anchor_text": "Kyoto guide",
            "target_path": "/guide/kyoto_guide.md",
            "outreach_note": "Local route.",
        },
    },
}


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("STATS_DB_PATH", str(tmp_path / "visitor_stats.db"))
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("PINTEREST_BOARD_ID", raising=False)
    stats_service.reset_visitor_cache()


def test_pinterest_payload_uses_image_and_summary(isolated_db, monkeypatch):
    monkeypatch.setenv("PINTEREST_BOARD_ID", "board-123")
    result = post_to_pinterest(GUIDE)
    pin = result["pin"]
    assert result["skipped"] is True
    assert result["board_name"] == "City walks"
    assert pin["board_id"] == "board-123"
    assert pin["title"] == "Kyoto walking day"
    assert pin["description"] == "One quiet route through Kyoto."
    assert pin["media_source"]["source_type"] == "image_url"
    assert pin["media_source"]["url"] == "https://images.example/kyoto.jpg"
    assert pin["link"].endswith("/guide/kyoto_guide.md")


def test_discord_skips_without_webhook(isolated_db):
    result = send_discord_webhook(GUIDE)
    assert result["skipped"] is True
    assert result["ok"] is False


def test_discord_posts_when_webhook_is_configured(isolated_db, monkeypatch):
    captured = {}

    class Response:
        status_code = 204

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/api/webhooks/1/token")
    monkeypatch.setattr("app.agents.marketing_agent.requests.post", fake_post)
    result = send_discord_webhook(GUIDE)
    assert result["ok"] is True
    assert result["status_code"] == 204
    assert captured["timeout"] == 8
    assert "Kyoto walking day" in captured["json"]["content"]
    assert "https://discord.example/api/webhooks/1/token" == captured["url"]


def test_korean_boilerplate_reddit_draft_is_rewritten_in_english(isolated_db):
    guide = {
        "id": "prague_guide.md",
        "destination": "Prague",
        "article_markdown": (
            "## Old Town Square\n\nMorning coffee.\n\n"
            "## Charles Bridge\n\nCross early.\n\n"
            "A 3-day walk.\n"
        ),
        "syndication": {
            "reddit": {
                "subreddit": "travel",
                "title": "Prague 첫 방문 때 실제로 도움이 됐던 동선",
                "body": "프라하을 처음 가는 기준으로 관광지(Old Town)와 식사를 하루 동선으로 묶어 봤다.",
            }
        },
    }
    result = draft_reddit_post(guide)
    assert result["posted"] is False
    assert result["subreddit"] in {"travel", "solotravel", "Europe"}
    markdown = result["markdown"]
    assert "Old Town Square" in markdown
    assert "Charles Bridge" in markdown
    assert "첫 방문" not in markdown
    assert not any("\uac00" <= char <= "\ud7a3" for char in markdown)


def test_reddit_draft_is_stored_not_posted(isolated_db):
    result = draft_reddit_post(GUIDE)
    assert result["posted"] is False
    assert result["subreddit"] == "travel"
    assert "r/travel" in result["markdown"]
    assert "Fushimi" in result["markdown"]
    assert result["alert"]["channel"] == "reddit_draft"
    assert result["alert"]["id"] == 1

    again = run_marketing_pipeline(GUIDE)
    assert again["reddit"]["posted"] is False
    assert again["reddit"]["alert"]["id"] == 2
    assert again["pinterest"]["pin"]["title"] == "Kyoto walking day"
    assert again["discord"]["skipped"] is True


def test_approve_runs_marketing_after_publish(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "bluelog123!")
    monkeypatch.delenv("ADMIN_TOKEN_SECRET", raising=False)
    monkeypatch.setenv("STATS_DB_PATH", str(tmp_path / "visitor_stats.db"))
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    stats_service.reset_visitor_cache()

    published = dict(GUIDE)
    published["qa_result"] = {"is_approved": True, "quality_score": 90, "violations": []}

    async def _publish(guide_id):
        assert guide_id == "kyoto_guide.md"
        return published

    monkeypatch.setattr("app.main.publish_approved_guide", _publish)
    client = TestClient(app)
    token = issue_admin_token()
    response = client.post(
        "/api/v1/guides/kyoto_guide.md/approve",
        headers={"Authorization": "Bearer {0}".format(token)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["qa_result"]["is_approved"] is True
    conn = sqlite3.connect(str(tmp_path / "visitor_stats.db"))
    try:
        row = conn.execute(
            "SELECT channel, body FROM marketing_alerts WHERE guide_id = ?",
            ("kyoto_guide.md",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "reddit_draft"
    assert "r/travel" in row[1]
