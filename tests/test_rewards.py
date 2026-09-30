"""포인트 적립. 제보 매거진이 발행되거나 추천 상위권에 들어가면 한 번만 쌓인다."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.rewards import router as rewards_router
from app.services.auth_service import issue_admin_token
from app.services.magazine_request_service import create_magazine_request, publish_verified_request, set_fact_check
from app.services.rewards_service import REASON_PUBLISHED, accrue_points, award_published_guide, award_top_rank
from app.services.vote_service import cast_vote


REVIEW = "직접 다녀온 골목 안쪽 국수집은 줄이 짧고 국물이 진해서 아침 첫 끼로 다시 가고 싶다. 정말 좋다."


def _guest(monkeypatch, tmp_path):
    monkeypatch.setenv("MAGAZINE_REQUESTS_DB_PATH", str(tmp_path / "magazine_requests.db"))
    monkeypatch.setenv("MAGAZINE_GUIDE_DIR", str(tmp_path / "guides"))
    monkeypatch.setenv("REWARDS_DB_PATH", str(tmp_path / "rewards.db"))
    monkeypatch.setenv("VOTES_DB_PATH", str(tmp_path / "votes.db"))
    return create_magazine_request(
        {
            "author_type": "public",
            "nickname": "Hana",
            "email": "hana@example.com",
            "country": "Japan",
            "city": "Tokyo",
            "place": "Yanaka",
            "review": REVIEW,
            "photo_url": "",
            "transport_info": "Subway pass",
            "discovery_story": "A local friend sent us there.",
            "reference_urls": "https://example.com/yanaka",
        }
    )


def test_accrue_is_idempotent_for_the_same_article(monkeypatch, tmp_path):
    monkeypatch.setenv("REWARDS_DB_PATH", str(tmp_path / "rewards.db"))
    first = accrue_points("hana@example.com", REASON_PUBLISHED, "tokyo_guest_1_guide.md", "google")
    second = accrue_points("hana@example.com", REASON_PUBLISHED, "tokyo_guest_1_guide.md", "google")
    assert first["created"] is True
    assert first["amount"] == 100
    assert first["points_balance"] == 100
    assert second["created"] is False
    assert second["points_balance"] == 100


def test_publish_and_top_rank_award_the_reporter(monkeypatch, tmp_path):
    row = _guest(monkeypatch, tmp_path)
    request_id = int(row["id"])
    set_fact_check(request_id, "VERIFIED", "Shop is still open.")
    published = publish_verified_request(request_id)
    guide_id = published["guide_id"]

    awarded = award_published_guide(guide_id)
    assert awarded["reason"] == "MAGAZINE_PUBLISHED"
    assert awarded["amount"] == 100
    assert awarded["email"] == "hana@example.com"

    voted = cast_vote(guide_id, "203.0.113.8")
    assert voted["created"] is True
    bonus = award_top_rank(guide_id)
    assert bonus["created"] is False
    assert bonus["points_balance"] == 150


def test_rewards_routes(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "bluelog123!")
    monkeypatch.delenv("ADMIN_TOKEN_SECRET", raising=False)
    monkeypatch.setenv("REWARDS_DB_PATH", str(tmp_path / "rewards.db"))
    application = FastAPI()
    application.include_router(rewards_router)
    client = TestClient(application)

    overview = client.get("/api/v1/rewards/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["publish_points"] == 100
    assert body["top_rank_points"] == 50
    assert body["partners"] == []

    hidden = client.post(
        "/api/v1/rewards/accrue",
        json={"email": "hana@example.com", "reason": "UGC_TOP_RANK_BONUS", "article_id": "a.md"},
    )
    assert hidden.status_code == 401
    token = issue_admin_token()
    created = client.post(
        "/api/v1/rewards/accrue",
        headers={"Authorization": "Bearer {0}".format(token)},
        json={
            "email": "hana@example.com",
            "reason": "UGC_TOP_RANK_BONUS",
            "article_id": "a.md",
            "auth_provider": "apple",
        },
    )
    assert created.status_code == 200
    assert created.json()["amount"] == 50
    assert created.json()["created"] is True
