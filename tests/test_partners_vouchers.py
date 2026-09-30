"""제휴 입점 승인과 포인트 바우처. LLM은 호출하지 않는다."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.partners import router as partners_router
from app.routers.rewards import router as rewards_router
from app.routers.vouchers import router as vouchers_router
from app.services.auth_service import issue_admin_token
from app.services.oauth_service import complete_social_login
from app.services.rewards_service import accrue_points


def _client(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "bluelog123!")
    monkeypatch.delenv("ADMIN_TOKEN_SECRET", raising=False)
    monkeypatch.setenv("REWARDS_DB_PATH", str(tmp_path / "rewards.db"))
    monkeypatch.setenv("MAGAZINE_REQUESTS_DB_PATH", str(tmp_path / "magazine_requests.db"))
    monkeypatch.setenv("MAGAZINE_GUIDE_DIR", str(tmp_path / "guides"))
    monkeypatch.setenv("MAGAZINE_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("OAUTH_TOKEN_SECRET", "test-secret")
    monkeypatch.setenv("VOUCHER_SECRET", "test-voucher")
    application = FastAPI()
    application.include_router(partners_router)
    application.include_router(vouchers_router)
    application.include_router(rewards_router)
    return TestClient(application)


def _apply():
    return {
        "store_name": "Hanok Noodle",
        "category": "K-Food",
        "address": "Seoul, Ikseon-dong 12",
        "contact_email": "shop@example.com",
        "phone": "010-0000-0000",
        "store_description": "A small noodle counter with a short morning queue.",
        "catalog_images": "https://example.com/shop.jpg",
        "offered_benefit": "10% off a bowl",
    }


def test_apply_approve_and_claim_voucher(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    hidden = client.get("/api/v1/admin/partners")
    assert hidden.status_code == 401

    created = client.post("/api/partners", json=_apply())
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "PENDING_APPROVAL"
    assert body["is_active"] is False
    partner_id = body["id"]

    empty = client.get("/api/v1/rewards/overview")
    assert empty.json()["partners"] == []

    token = issue_admin_token()
    headers = {"Authorization": "Bearer {0}".format(token)}
    approved = client.post(
        "/api/v1/admin/partners/{0}/approve".format(partner_id),
        headers=headers,
    )
    assert approved.status_code == 200
    guide_id = approved.json()["guide_id"]
    article = (tmp_path / "guides" / guide_id).read_text(encoding="utf-8")
    assert "Partner Verified Magazine" in article
    assert approved.json()["partner"]["is_active"] is True
    assert article == approved.json()["article_markdown"]

    listed = client.get("/api/v1/rewards/overview")
    partners = listed.json()["partners"]
    assert len(partners) == 1
    assert partners[0]["name"] == "Hanok Noodle"
    assert partners[0]["offered_benefit"] == "10% off a bowl"
    assert "contact_email" not in partners[0]

    denied = client.post("/api/vouchers/claim", json={"merchant_id": partner_id})
    assert denied.status_code == 401

    account = complete_social_login("google", "hana@example.com", "google-sub", "Hana")
    accrue_points("hana@example.com", "MAGAZINE_PUBLISHED", "hanok_partner_guide.md")
    user_headers = {"Authorization": "Bearer {0}".format(account["access_token"])}
    claimed = client.post("/api/vouchers/claim", headers=user_headers, json={"merchant_id": partner_id})
    assert claimed.status_code == 200
    voucher = claimed.json()
    assert len(voucher["voucher_code"]) == 8
    assert voucher["qr_svg"].startswith("<svg")
    assert voucher["points_balance"] == 50
    assert voucher["status"] == "ISSUED"

    checked = client.post(
        "/api/vouchers/verify",
        json={"voucher_code": voucher["voucher_code"], "qr_token": voucher["qr_token"]},
    )
    assert checked.status_code == 200
    assert checked.json()["valid"] is True
    assert checked.json()["store_name"] == "Hanok Noodle"

    redeemed = client.post(
        "/api/vouchers/verify",
        json={"voucher_code": voucher["voucher_code"].lower(), "consume": True},
    )
    assert redeemed.json()["valid"] is True
    assert redeemed.json()["status"] == "REDEEMED"
    again = client.post("/api/vouchers/verify", json={"voucher_code": voucher["voucher_code"]})
    assert again.json()["valid"] is False
    assert again.json()["status"] == "REDEEMED"

    second = client.post("/api/vouchers/claim", headers=user_headers, json={"merchant_id": partner_id})
    assert second.status_code == 200
    assert second.json()["points_balance"] == 0
    poor = client.post("/api/vouchers/claim", headers=user_headers, json={"merchant_id": partner_id})
    assert poor.status_code == 400
