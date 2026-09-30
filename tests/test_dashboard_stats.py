"""관리자 대시보드 통계. 가이드 생성 LLM은 호출하지 않는다."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import guide_service, scheduler_service, stats_service
from app.services.auth_service import issue_admin_token
from app.services.marketing_service import save_marketing_alert
from app.services.scheduler_service import read_daily_batch_status

HIGH_ARTICLE = (
    "## Neighborhoods\n\n"
    + ("Local travelers compare neighborhood prices before they book a room. " * 12)
    + "\n\n| Place | Cost |\n| --- | --- |\n| Market | 12 |\n"
)
LOW_ARTICLE = "Draft only."


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "bluelog123!")
    monkeypatch.delenv("ADMIN_TOKEN_SECRET", raising=False)
    return TestClient(app)


def _auth_header(token):
    return {"Authorization": "Bearer {0}".format(token)}


def _isolate_guides(monkeypatch, tmp_path):
    guides = tmp_path / "guides"
    output = tmp_path / "output"
    guides.mkdir()
    output.mkdir()
    previous_store = dict(guide_service._GUIDE_STORE)
    guide_service._GUIDE_STORE.clear()
    monkeypatch.setattr(guide_service, "_GUIDES_DIR", guides)
    monkeypatch.setattr(guide_service, "_OUTPUT_DIR", output)
    monkeypatch.setattr(scheduler_service, "OUTPUT_DIR", output)
    monkeypatch.setattr(scheduler_service, "_batch_running", False)
    monkeypatch.setattr(scheduler_service, "_batch_city", "")
    return guides, output, previous_store


def _restore_store(previous_store):
    guide_service._GUIDE_STORE.clear()
    guide_service._GUIDE_STORE.update(previous_store)


def test_dashboard_stats_requires_bearer_token(client):
    missing = client.get("/api/v1/admin/dashboard-stats")
    assert missing.status_code == 401
    forged = client.get(
        "/api/v1/admin/dashboard-stats",
        headers=_auth_header("not-a-real-token"),
    )
    assert forged.status_code == 401


def test_dashboard_stats_counts_approval_gate(client, monkeypatch, tmp_path):
    guides, output, previous_store = _isolate_guides(monkeypatch, tmp_path)
    monkeypatch.setenv("STATS_DB_PATH", str(tmp_path / "visitor_stats.db"))
    stats_service.reset_visitor_cache()
    seoul = guides / "seoul_guide.md"
    busan = guides / "busan_guide.md"
    osaka = guides / "osaka_guide.md"
    seoul.write_text(HIGH_ARTICLE, encoding="utf-8")
    busan.write_text(HIGH_ARTICLE, encoding="utf-8")
    osaka.write_text(LOW_ARTICLE, encoding="utf-8")
    os.utime(seoul, (1_700_000_000, 1_700_000_000))
    os.utime(busan, (1_700_010_000, 1_700_010_000))
    os.utime(osaka, (1_700_020_000, 1_700_020_000))
    (output / "approved_guides.json").write_text(
        json.dumps(["seoul_guide.md"]),
        encoding="utf-8",
    )
    (output / "batch_status.json").write_text(
        json.dumps(
            {
                "last_run": "2026-09-26 09:00",
                "status": "SUCCESS",
                "target_city": "Tokyo",
            }
        ),
        encoding="utf-8",
    )

    try:
        token = issue_admin_token()
        response = client.get("/api/v1/admin/dashboard-stats", headers=_auth_header(token))
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["total_guides_count"] == 3
        assert payload["approved_count"] == 1
        assert payload["pending_count"] == 2
        assert payload["daily_batch_status"] == {
            "last_run": "2026-09-26 09:00",
            "status": "SUCCESS",
            "target_city": "Tokyo",
        }
        assert payload["agent_health"] == {
            "research_agent": "OK",
            "writer_agent": "OK",
            "qa_agent": "OK",
            "syndication_agent": "OK",
        }
        recent = payload["recent_guides"]
        assert [item["filename"] for item in recent] == [
            "osaka_guide.md",
            "busan_guide.md",
            "seoul_guide.md",
        ]
        assert recent[0]["city"] == "Osaka"
        assert recent[0]["qa_score"] < 75
        assert recent[0]["is_approved"] is False
        assert recent[0]["created_at"]
        assert recent[2]["city"] == "Seoul"
        assert recent[2]["qa_score"] >= 75
        assert recent[2]["is_approved"] is True
        assert recent[1]["is_approved"] is False
        assert recent[1]["qa_score"] >= 75
        assert payload["marketing_alerts"] == []
    finally:
        _restore_store(previous_store)


def test_stale_running_batch_is_reported_as_failed(monkeypatch, tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(scheduler_service, "OUTPUT_DIR", output)
    monkeypatch.setattr(scheduler_service, "_batch_running", False)
    monkeypatch.setattr(scheduler_service, "_batch_city", "")
    (output / "batch_status.json").write_text(
        json.dumps(
            {
                "last_run": "2026-09-26 09:00",
                "status": "RUNNING",
                "target_city": "Paris",
            }
        ),
        encoding="utf-8",
    )
    assert read_daily_batch_status() == {
        "last_run": "2026-09-26 09:00",
        "status": "FAILED",
        "target_city": "Paris",
    }


def test_dashboard_stats_lists_marketing_alerts_and_dismiss(client, monkeypatch, tmp_path):
    guides, output, previous_store = _isolate_guides(monkeypatch, tmp_path)
    monkeypatch.setenv("STATS_DB_PATH", str(tmp_path / "visitor_stats.db"))
    stats_service.reset_visitor_cache()
    (guides / "kyoto_guide.md").write_text(HIGH_ARTICLE, encoding="utf-8")
    save_marketing_alert(
        guide_id="kyoto_guide.md",
        channel="reddit_draft",
        title="r/travel: Kyoto walking day",
        body="## r/travel\n\n**Kyoto walking day**\n",
    )
    try:
        token = issue_admin_token()
        listed = client.get("/api/v1/admin/dashboard-stats", headers=_auth_header(token))
        assert listed.status_code == 200, listed.text
        alerts = listed.json()["marketing_alerts"]
        assert len(alerts) == 1
        assert alerts[0]["guide_id"] == "kyoto_guide.md"
        assert alerts[0]["channel"] == "reddit_draft"
        assert "r/travel" in alerts[0]["body"]
        alert_id = alerts[0]["id"]

        missing_auth = client.delete("/api/v1/admin/marketing-alerts/{0}".format(alert_id))
        assert missing_auth.status_code == 401

        dismissed = client.delete(
            "/api/v1/admin/marketing-alerts/{0}".format(alert_id),
            headers=_auth_header(token),
        )
        assert dismissed.status_code == 200, dismissed.text
        assert dismissed.json() == {"ok": True, "id": alert_id}

        again = client.get("/api/v1/admin/dashboard-stats", headers=_auth_header(token))
        assert again.status_code == 200
        assert again.json()["marketing_alerts"] == []

        missing = client.delete(
            "/api/v1/admin/marketing-alerts/999",
            headers=_auth_header(token),
        )
        assert missing.status_code == 404
    finally:
        _restore_store(previous_store)
