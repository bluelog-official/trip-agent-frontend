"""IP당 글 하나 추천, 기간 집계, 지도 순위의 최우선 가중치."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.globe_service import build_globe_map
from app.services.vote_service import cast_vote, counts_for_period, vote_statuses

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=ZoneInfo("Asia/Seoul"))
WEEK_VOTE = datetime(2026, 9, 28, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))
OLD_VOTE = datetime(2026, 8, 1, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("VOTES_DB_PATH", str(tmp_path / "votes.db"))
    from app.routers.votes import router as vote_router

    application = FastAPI()
    application.include_router(vote_router)
    return TestClient(application)


def test_one_ip_votes_once_per_article(client):
    first = client.post(
        "/api/votes",
        json={"article_id": "paris_guide.md"},
        headers={"X-Forwarded-For": "203.0.113.10, 10.0.0.8"},
    )
    assert first.status_code == 201
    body = first.json()
    assert body["created"] is True
    assert body["voted"] is True
    assert body["vote_count"] == 1

    duplicate = client.post(
        "/api/votes",
        json={"article_id": "paris_guide.md"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["created"] is False
    assert duplicate.json()["vote_count"] == 1
    assert "Already voted" in duplicate.json()["detail"]

    other_article = client.post(
        "/api/votes",
        json={"article_id": "rome_guide.md"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert other_article.status_code == 201
    assert other_article.json()["vote_count"] == 1

    other_ip = client.post(
        "/api/votes",
        json={"article_id": "paris_guide.md"},
        headers={"X-Forwarded-For": "198.51.100.4"},
    )
    assert other_ip.status_code == 201
    assert other_ip.json()["vote_count"] == 2

    status = client.get(
        "/api/votes",
        params={"article_ids": "paris_guide.md,rome_guide.md,missing_guide.md"},
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert status.status_code == 200
    rows = {item["article_id"]: item for item in status.json()["votes"]}
    assert rows["paris_guide.md"]["vote_count"] == 2
    assert rows["paris_guide.md"]["voted"] is True
    assert rows["rome_guide.md"]["voted"] is True
    assert rows["missing_guide.md"]["vote_count"] == 0
    assert rows["missing_guide.md"]["voted"] is False


def test_empty_article_id_is_rejected(client):
    response = client.post("/api/votes", json={"article_id": "  "})
    assert response.status_code == 422


def test_period_counts_and_vote_rank(monkeypatch, tmp_path):
    monkeypatch.setenv("VOTES_DB_PATH", str(tmp_path / "votes.db"))
    cast_vote("rome_guide.md", "203.0.113.8", created_at=WEEK_VOTE)
    cast_vote("rome_guide.md", "203.0.113.9", created_at=WEEK_VOTE)
    cast_vote("paris_guide.md", "203.0.113.8", created_at=OLD_VOTE)
    cast_vote("paris_guide.md", "198.51.100.2", created_at=WEEK_VOTE)

    week = counts_for_period("1w", now=NOW)
    assert week["rome_guide.md"] == 2
    assert week["paris_guide.md"] == 1
    assert counts_for_period("1m", now=NOW)["paris_guide.md"] == 1
    assert counts_for_period("all", now=NOW)["paris_guide.md"] == 2

    records = [
        {
            "city": "Paris",
            "filename": "paris_guide.md",
            "qa_score": 90,
            "published_at": "2026-09-28 10:00",
            "hashtags": ["Gastronomy"],
            "thumbnail": "https://example.com/paris.jpg",
        },
        {
            "city": "Rome",
            "filename": "rome_guide.md",
            "qa_score": 40,
            "published_at": "2026-09-29 10:00",
            "hashtags": ["Museums"],
        },
    ]
    ranked = build_globe_map("1w", records, now=NOW, vote_counts=week)
    assert [item["slug"] for item in ranked["cities"]] == ["rome", "paris"]
    rome = ranked["cities"][0]
    assert rome["vote_count"] == 2
    assert rome["is_top"] is True
    assert rome["article_id"] == "rome_guide.md"
    assert rome["flag"]
    assert rome["country"] == "Italy"
    paris = ranked["cities"][1]
    assert paris["vote_count"] == 1
    assert paris["thumbnail"] == "https://example.com/paris.jpg"
    assert paris["rank"] == 2

    untouched = build_globe_map("1w", records, now=NOW)
    assert [item["slug"] for item in untouched["cities"]] == ["paris", "rome"]

    seen = vote_statuses(["rome_guide.md"], "203.0.113.8")
    assert seen[0]["voted"] is True
    assert seen[0]["vote_count"] == 2
