"""소셜 로그인이 같은 게스트 이메일의 포인트와 제보를 계정으로 합친다."""

from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models import rewards as reward_store
from app.routers.oauth import router as oauth_router
from app.routers.rewards import router as rewards_router
from app.routers.wallet import router as wallet_router
from app.services.auth_service import issue_admin_token
from app.services.magazine_request_service import create_magazine_request, store_xrpl_tx_hash
from app.services.oauth_service import complete_social_login, decode_jwt_payload
from app.services.rewards_service import REASON_PUBLISHED, accrue_points, db_path
from app.services.wallet_service import publish_state


REVIEW = "직접 다녀온 골목 안쪽 국수집은 줄이 짧고 국물이 진해서 아침 첫 끼로 다시 가고 싶다. 정말 좋다."


def _paths(monkeypatch, tmp_path):
    monkeypatch.setenv("REWARDS_DB_PATH", str(tmp_path / "rewards.db"))
    monkeypatch.setenv("MAGAZINE_REQUESTS_DB_PATH", str(tmp_path / "magazine_requests.db"))
    monkeypatch.setenv("OAUTH_TOKEN_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_URL", "https://bluelogtrip.com")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("APPLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("APPLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("KAKAO_CLIENT_ID", raising=False)
    monkeypatch.delenv("KAKAO_CLIENT_SECRET", raising=False)


def _guest_report(email="hana@example.com"):
    return create_magazine_request(
        {
            "author_type": "public",
            "nickname": "Hana",
            "email": email,
            "country": "Korea",
            "city": "Seoul",
            "place": "Ikseon-dong",
            "review": REVIEW,
            "photo_url": "",
            "transport_info": "Jongno walk",
            "discovery_story": "A friend sent the alley.",
            "reference_urls": "https://example.com/ikseon",
        }
    )


def test_social_login_merges_guest_points_and_reports(monkeypatch, tmp_path):
    _paths(monkeypatch, tmp_path)
    report = _guest_report()
    other = _guest_report("other@example.com")
    accrue_points("hana@example.com", REASON_PUBLISHED, "seoul_guest_1_guide.md", "email")
    conn = reward_store.connect(db_path())
    reward_store.insert_point_log(
        conn,
        999,
        "hana@example.com",
        50,
        "UGC_TOP_RANK_BONUS",
        "seoul_guest_1_guide.md",
        "2026-10-01T00:00:00Z",
    )
    conn.close()

    first = complete_social_login("google", "Hana@Example.com", "google-sub", "Hana Kim")
    assert first["auth_provider"] == "google"
    assert first["points_balance"] == 150
    assert first["migrated_point_logs"] == 1
    assert first["migrated_reports"] == 1
    assert first["access_token"]

    store_xrpl_tx_hash(int(report["id"]), "ABCDEF123456")
    application = FastAPI()
    application.include_router(oauth_router)
    application.include_router(wallet_router)
    application.include_router(rewards_router)
    client = TestClient(application)
    wallet = client.get(
        "/api/v1/wallet",
        headers={"Authorization": "Bearer {0}".format(first["access_token"])},
    )
    assert wallet.status_code == 200
    body = wallet.json()
    assert body["points_balance"] == 150
    assert body["email"] == "hana@example.com"
    assert body["name"] == "Hana Kim"
    assert {row["reason"] for row in body["logs"]} == {"MAGAZINE_PUBLISHED", "UGC_TOP_RANK_BONUS"}
    owned = {row["id"]: row for row in body["reports"]}
    assert owned[int(report["id"])]["publish_state"] == "PENDING"
    assert owned[int(report["id"])]["guest_email"] == "hana@example.com"
    assert owned[int(report["id"])]["xrpl_url"] == "https://livenet.xrpl.org/transactions/ABCDEF123456"
    assert int(other["id"]) not in owned

    second = complete_social_login("google", "hana@example.com", "google-sub", "Hana Kim")
    assert second["points_balance"] == 150
    assert second["migrated_point_logs"] == 0
    assert second["migrated_reports"] == 0

    denied = client.post(
        "/api/v1/rewards/accrue",
        headers={"Authorization": "Bearer {0}".format(first["access_token"])},
        json={"email": "hana@example.com", "reason": "MAGAZINE_PUBLISHED", "article_id": "x.md"},
    )
    assert denied.status_code == 401
    admin = client.post(
        "/api/v1/rewards/accrue",
        headers={"Authorization": "Bearer {0}".format(issue_admin_token())},
        json={"email": "hana@example.com", "reason": "MAGAZINE_PUBLISHED", "article_id": "x.md"},
    )
    assert admin.status_code == 200


def test_oauth_callback_issues_a_wallet_session(monkeypatch, tmp_path):
    _paths(monkeypatch, tmp_path)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setattr(
        "app.routers.oauth.fetch_provider_profile",
        lambda provider, code, redirect, user_json="": {
            "email": "hana@example.com",
            "subject": "sub-1",
            "name": "Hana",
        },
    )
    application = FastAPI()
    application.include_router(oauth_router)
    client = TestClient(application)

    missing = client.get("/api/auth/signin/kakao")
    assert missing.status_code == 503

    start = client.get("/api/auth/signin/google")
    assert start.status_code == 200
    state = parse_qs(urlparse(start.json()["authorize_url"]).query)["state"][0]
    bad = client.get("/api/auth/callback/google?code=abc&state=nope", follow_redirects=False)
    assert bad.status_code == 400

    callback = client.get(
        "/api/auth/callback/google?code=abc&state={0}".format(state),
        follow_redirects=False,
    )
    assert callback.status_code == 303
    location = callback.headers["location"]
    assert location.startswith("https://bluelogtrip.com/wallet#session=")
    token = parse_qs(urlparse(location).fragment)["session"][0]
    session = client.get("/api/auth/session", headers={"Authorization": "Bearer {0}".format(token)})
    assert session.status_code == 200
    assert session.json()["email"] == "hana@example.com"
    assert session.json()["auth_provider"] == "google"


def test_wallet_saved_guides_round_trip(monkeypatch, tmp_path):
    _paths(monkeypatch, tmp_path)
    account = complete_social_login("kakao", "mina@example.com", "kakao-9", "Mina")
    application = FastAPI()
    application.include_router(wallet_router)
    client = TestClient(application)
    headers = {"Authorization": "Bearer {0}".format(account["access_token"])}
    saved = client.post(
        "/api/v1/wallet/saved",
        headers=headers,
        json={"guide_id": "korea_3_days_kbeauty_kfood_guide.md"},
    )
    assert saved.status_code == 200
    assert saved.json() == ["korea_3_days_kbeauty_kfood_guide.md"]
    removed = client.delete(
        "/api/v1/wallet/saved/korea_3_days_kbeauty_kfood_guide.md",
        headers=headers,
    )
    assert removed.status_code == 200
    assert removed.json() == []
    rejected = client.post("/api/v1/wallet/saved", headers=headers, json={"guide_id": "../secret"})
    assert rejected.status_code == 400


def test_publish_state_and_apple_token_payload():
    assert publish_state("PENDING_REVIEW", "PENDING") == "PENDING"
    assert publish_state("PENDING_REVIEW", "VERIFIED") == "VERIFIED"
    assert publish_state("PUBLISHED", "VERIFIED") == "PUBLISHED"
    assert publish_state("PENDING_REVIEW", "REJECTED") == "REJECTED"
    payload = decode_jwt_payload("aaa.{0}.ccc".format(
        __import__("base64").urlsafe_b64encode(b'{"email":"a@b.c","sub":"s"}').decode("ascii").rstrip("=")
    ))
    assert payload["email"] == "a@b.c"
