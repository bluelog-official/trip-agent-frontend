"""시크릿 기동 차단, CORS 고정, 보안 헤더, IP 속도 제한."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import enforce_production_secrets
from app.core.limiter import limiter
from app.main import FRONTEND_URL, _cors_allow_origins, app
from app.routers.magazine_requests import router as magazine_router
from app.routers.partners import router as partners_router


REVIEW = "직접 다녀온 골목 안쪽 국수집은 줄이 짧고 국물이 진해서 아침 첫 끼로 다시 가고 싶다. 정말 좋다."
STRONG_VOUCHER = "vchr_" + ("a" * 40)
STRONG_OAUTH = "oaut_" + ("b" * 40)


@pytest.fixture
def rate_limits():
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.enabled = False
    limiter.reset()


def test_placeholder_and_test_secrets_stop_startup(monkeypatch):
    monkeypatch.setenv("VOUCHER_SECRET", "your_super_secret_voucher_key_32bytes_min")
    monkeypatch.setenv("OAUTH_TOKEN_SECRET", "test-secret")
    with pytest.raises(SystemExit):
        enforce_production_secrets(force=True)

    monkeypatch.setenv("VOUCHER_SECRET", "")
    monkeypatch.setenv("OAUTH_TOKEN_SECRET", "")
    with pytest.raises(SystemExit):
        enforce_production_secrets(force=True)


def test_long_unique_secrets_pass_and_pytest_skips_the_boot_check(monkeypatch):
    monkeypatch.setenv("VOUCHER_SECRET", STRONG_VOUCHER)
    monkeypatch.setenv("OAUTH_TOKEN_SECRET", STRONG_OAUTH)
    enforce_production_secrets(force=True)

    monkeypatch.setenv("VOUCHER_SECRET", "test-voucher")
    monkeypatch.setenv("OAUTH_TOKEN_SECRET", "test-secret")
    enforce_production_secrets(force=False)


def test_cors_allowlist_is_explicit():
    origins = _cors_allow_origins("https://bluelog.travel", "https://bluelogtrip.com")
    assert "*" not in origins
    assert "https://bluelogtrip.com" in origins
    assert "https://www.bluelogtrip.com" in origins
    assert "https://bluelog.travel" in origins
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert all("*" not in origin for origin in origins)


def test_security_headers_and_pinned_cors():
    client = TestClient(app)
    allowed = client.get("/robots.txt", headers={"Origin": "https://bluelogtrip.com"})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://bluelogtrip.com"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert allowed.headers["x-frame-options"] == "DENY"
    assert allowed.headers["x-content-type-options"] == "nosniff"
    assert allowed.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert allowed.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert allowed.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"

    blocked = client.get("/robots.txt", headers={"Origin": "https://evil.example"})
    assert blocked.headers.get("access-control-allow-origin") in (None, "")
    assert blocked.headers["x-frame-options"] == "DENY"

    preview = client.get(
        "/robots.txt",
        headers={"Origin": "https://travel-agent-system.vercel.app"},
    )
    assert preview.headers.get("access-control-allow-origin") in (None, "")
    assert FRONTEND_URL != "*"


def test_voucher_and_signin_routes_are_limited(rate_limits):
    client = TestClient(app)
    claim_codes = [
        client.post("/api/vouchers/claim", json={"merchant_id": 1}).status_code
        for _ in range(11)
    ]
    assert claim_codes[:10] == [401] * 10
    assert claim_codes[10] == 429

    verify_codes = [
        client.post(
            "/api/vouchers/verify",
            json={"voucher_code": "ABCD2345", "consume": False},
        ).status_code
        for _ in range(11)
    ]
    assert 429 not in verify_codes[:10]
    assert verify_codes[10] == 429

    signin_codes = [
        client.get("/api/auth/signin/google").status_code
        for _ in range(11)
    ]
    assert 429 not in signin_codes[:10]
    assert signin_codes[10] == 429


def test_magazine_request_and_promote_store_are_limited(rate_limits, monkeypatch, tmp_path):
    monkeypatch.setenv("MAGAZINE_REQUESTS_DB_PATH", str(tmp_path / "magazine_requests.db"))
    monkeypatch.setenv("MAGAZINE_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MAGAZINE_GUIDE_DIR", str(tmp_path / "guides"))
    monkeypatch.setenv("REWARDS_DB_PATH", str(tmp_path / "rewards.db"))
    application = FastAPI()
    application.state.limiter = limiter
    application.include_router(magazine_router)
    application.include_router(partners_router)
    client = TestClient(application)

    magazine = {
        "author_type": "anonymous",
        "nickname": "",
        "email": "",
        "country": "Japan",
        "city": "Tokyo",
        "place": "Yanaka Ginza",
        "review": REVIEW,
        "photo_url": "https://example.com/yanaka.jpg",
    }
    magazine_codes = [
        client.post("/api/magazine-requests", json=magazine).status_code
        for _ in range(6)
    ]
    assert magazine_codes[:5] == [200] * 5
    assert magazine_codes[5] == 429

    partner = {
        "store_name": "Hanok Noodle",
        "category": "K-Food",
        "address": "Seoul, Ikseon-dong 12",
        "contact_email": "shop@example.com",
        "phone": "010-0000-0000",
        "store_description": "A small noodle counter with a short morning queue.",
        "catalog_images": "https://example.com/shop.jpg",
        "offered_benefit": "10% off a bowl",
    }
    partner_codes = [
        client.post("/api/partners", json=partner).status_code
        for _ in range(6)
    ]
    assert partner_codes[:5] == [200] * 5
    assert partner_codes[5] == 429
