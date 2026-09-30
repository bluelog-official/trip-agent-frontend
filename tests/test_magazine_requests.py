"""게스트 매거진 제보. 가이드 생성 LLM은 호출하지 않는다."""

import base64
import hashlib
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.magazine_requests import router as magazine_router
from app.services.auth_service import issue_admin_token
from app.services.magazine_request_service import build_guide_source


REVIEW = "직접 다녀온 골목 안쪽 국수집은 줄이 짧고 국물이 진해서 아침 첫 끼로 다시 가고 싶다. 정말 좋다."


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "bluelog123!")
    monkeypatch.delenv("ADMIN_TOKEN_SECRET", raising=False)
    monkeypatch.setenv("MAGAZINE_REQUESTS_DB_PATH", str(tmp_path / "magazine_requests.db"))
    monkeypatch.setenv("MAGAZINE_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MAGAZINE_GUIDE_DIR", str(tmp_path / "guides"))
    application = FastAPI()
    application.include_router(magazine_router)
    return TestClient(application)


def _payload(**overrides):
    body = {
        "author_type": "anonymous",
        "nickname": "",
        "email": "",
        "country": "Japan",
        "city": "Tokyo",
        "place": "Yanaka Ginza",
        "review": REVIEW,
        "photo_url": "https://example.com/yanaka.jpg",
    }
    body.update(overrides)
    return body


def test_guide_source_uses_city_and_place():
    source = build_guide_source(
        {
            "id": 4,
            "author_type": "public",
            "nickname": "Mira",
            "country": "Japan",
            "city": "Tokyo",
            "place": "Yanaka Ginza",
            "review": REVIEW,
            "photo_url": "https://example.com/yanaka.jpg",
            "status": "PENDING_REVIEW",
        }
    )
    assert source["destination"] == "Tokyo, Japan"
    assert source["keyword"] == "Yanaka Ginza"
    assert source["author_label"] == "Mira"
    assert source["ready_for_one_click"] is False

    verified_row = {
        "id": 4,
        "author_type": "public",
        "nickname": "Mira",
        "country": "Japan",
        "city": "Tokyo",
        "place": "Yanaka Ginza",
        "review": REVIEW,
        "photo_url": "https://example.com/yanaka.jpg",
        "status": "PENDING_REVIEW",
        "fact_check_status": "VERIFIED",
        "transport_info": "Use a subway day pass.",
        "discovery_story": "A coworker insisted we go.",
        "reference_urls": "https://example.com/notes",
    }
    ready = build_guide_source(verified_row)
    assert ready["ready_for_one_click"] is True
    assert ready["transport_info"] == "Use a subway day pass."


def test_anonymous_request_is_pending_review(client):
    response = client.post("/api/magazine-requests", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING_REVIEW"
    assert body["fact_check_status"] == "PENDING"
    assert body["author_type"] == "anonymous"
    assert body["guide_source"]["destination"] == "Tokyo, Japan"
    assert body["guide_source"]["keyword"] == "Yanaka Ginza"
    assert body["guide_source"]["author_label"] == "Anonymous"
    assert body["guide_source"]["ready_for_one_click"] is False
    assert body["submit_language"] == "en"


def test_public_name_requires_nickname_and_review_length(client):
    short = client.post("/api/magazine-requests", json=_payload(review="너무 짧다"))
    assert short.status_code == 422
    missing_name = client.post(
        "/api/magazine-requests",
        json=_payload(author_type="public", nickname=""),
    )
    assert missing_name.status_code == 422
    named = client.post(
        "/api/magazine-requests",
        json=_payload(author_type="public", nickname="하나", email="hana@example.com"),
    )
    assert named.status_code == 200
    assert named.json()["guide_source"]["author_label"] == "하나"


def test_photo_upload_is_stored_and_admin_list_requires_token(client, tmp_path):
    png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n" + b"travel-photo"
    ).decode("ascii")
    created = client.post(
        "/api/magazine-requests",
        json=_payload(
            photo_url="",
            photo_data="data:image/png;base64,{0}".format(png),
        ),
    )
    assert created.status_code == 200
    photo_url = created.json()["photo_url"]
    assert photo_url.startswith("magazine-uploads/")
    assert (tmp_path / "uploads" / photo_url.split("/", 1)[1]).is_file()

    hidden = client.get("/api/v1/admin/magazine-requests")
    assert hidden.status_code == 401
    token = issue_admin_token()
    listed = client.get(
        "/api/v1/admin/magazine-requests",
        headers={"Authorization": "Bearer {0}".format(token)},
    )
    assert listed.status_code == 200
    rows = listed.json()["requests"]
    assert len(rows) == 1
    assert rows[0]["status"] == "PENDING_REVIEW"
    assert rows[0]["fact_check_status"] == "PENDING"
    assert rows[0]["guide_source"]["ready_for_one_click"] is False
    assert rows[0]["photo_url"] == photo_url


def test_reliability_fields_and_verified_one_click_draft(client, tmp_path):
    token = issue_admin_token()
    headers = {"Authorization": "Bearer {0}".format(token)}
    created = client.post(
        "/api/magazine-requests",
        json=_payload(
            email="hana@example.com",
            transport_info="Buy a subway day pass and walk the last stop.",
            discovery_story="A coworker insisted after their own visit.",
            reference_urls="https://example.com/blog https://youtu.be/yanaka",
            submit_language="ko",
        ),
    )
    assert created.status_code == 200
    body = created.json()
    assert body["submit_language"] == "ko"
    assert "subway day pass" in body["transport_info"]
    assert body["reference_urls"] == "https://example.com/blog\nhttps://youtu.be/yanaka"
    request_id = body["id"]

    blocked = client.post(
        "/api/v1/admin/magazine-requests/{0}/publish".format(request_id),
        headers=headers,
    )
    assert blocked.status_code == 400

    checked = client.patch(
        "/api/v1/admin/magazine-requests/{0}/fact-check".format(request_id),
        headers=headers,
        json={
            "fact_check_status": "VERIFIED",
            "verification_note": "The alley shop is listed on the local map.",
        },
    )
    assert checked.status_code == 200
    assert checked.json()["fact_check_status"] == "VERIFIED"
    assert checked.json()["guide_source"]["ready_for_one_click"] is True
    assert "local map" in checked.json()["verification_note"]

    published = client.post(
        "/api/v1/admin/magazine-requests/{0}/publish".format(request_id),
        headers=headers,
    )
    assert published.status_code == 200
    guide_id = published.json()["guide_id"]
    article = (tmp_path / "guides" / guide_id).read_text(encoding="utf-8")
    assert "subway day pass" in article
    assert "coworker insisted" in article
    assert "https://youtu.be/yanaka" in article
    assert "language: \"en\"" in article
    assert not re.search(r"[\uac00-\ud7a3]", article)
    assert published.json()["article_markdown"] == article
    korean_id = published.json()["korean_guide_id"]
    korean = (tmp_path / "guides" / korean_id).read_text(encoding="utf-8")
    assert "가는 길" in korean
    assert "지하철" in korean
    digest = published.json()["english_sha256"]
    assert digest == hashlib.sha256(article.encode("utf-8")).hexdigest()
    assert len(digest) == 64

    again = client.post(
        "/api/v1/admin/magazine-requests/{0}/publish".format(request_id),
        headers=headers,
    )
    assert again.status_code == 400


def test_reference_url_must_be_http(client):
    response = client.post(
        "/api/magazine-requests",
        json=_payload(reference_urls="notes.txt"),
    )
    assert response.status_code == 422
