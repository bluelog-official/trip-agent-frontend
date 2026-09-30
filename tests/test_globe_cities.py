"""지구본 도시 핀: 기간 필터, 발행 건수, 좌표, 상위 5 순위."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.services import globe_service, guide_service
from app.services.globe_service import build_globe_map

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=ZoneInfo("Asia/Seoul"))

RECORDS = [
    {
        "city": "Paris",
        "qa_score": 80,
        "published_at": "2026-09-28 10:00",
        "hashtags": ["Architecture", "Gastronomy"],
    },
    {
        "city": "Paris",
        "qa_score": 90,
        "published_at": "2026-09-20 10:00",
        "hashtags": ["Gastronomy", "Nightlife"],
    },
    {"city": "Seoul", "qa_score": 99, "published_at": "2026-08-01 10:00", "hashtags": ["Culture"]},
    {"city": "Tokyo", "qa_score": 70, "published_at": "2025-09-01 10:00"},
    {"city": "London", "qa_score": 60, "published_at": "2026-09-10 10:00"},
    {"city": "Rome", "qa_score": 50, "published_at": "2026-09-29 10:00", "hashtags": ["Museums"]},
    {"city": "Lisbon", "qa_score": 40, "published_at": "2026-09-05 10:00"},
    {"city": "Unknownville", "qa_score": 100, "published_at": "2026-09-29 10:00"},
]


@pytest.fixture
def client():
    try:
        from app.main import app
    except Exception as exc:  # noqa: BLE001 - 로컬 venv의 litellm 수입 실패와 구분한다
        pytest.skip("app import unavailable: {0}".format(exc.__class__.__name__))
    return TestClient(app)


def _isolate_guides(monkeypatch, tmp_path):
    guides = tmp_path / "guides"
    output = tmp_path / "output"
    guides.mkdir()
    output.mkdir()
    previous_store = dict(guide_service._GUIDE_STORE)
    guide_service._GUIDE_STORE.clear()
    monkeypatch.setattr(guide_service, "_GUIDES_DIR", guides)
    monkeypatch.setattr(guide_service, "_OUTPUT_DIR", output)
    return guides, previous_store


def _restore_store(previous_store):
    guide_service._GUIDE_STORE.clear()
    guide_service._GUIDE_STORE.update(previous_store)


def _by_slug(period):
    payload = build_globe_map(period, RECORDS, now=NOW)
    return payload["period"], {item["slug"]: item for item in payload["cities"]}


def test_period_filter_changes_pins_and_explains_rank():
    period, week = _by_slug("1w")
    assert period == "1w"
    assert set(week) == {"paris", "rome"}
    assert week["paris"]["published_count"] == 1
    assert week["paris"]["quality_score"] == 80
    assert week["paris"]["keywords"] == ["Architecture", "Gastronomy"]
    assert week["paris"]["trending_percent"] == 0
    assert week["paris"]["trending_new"] is False
    assert week["rome"]["trending_new"] is True
    assert week["rome"]["trending_percent"] is None
    assert week["paris"]["rank"] == 1
    assert week["paris"]["is_top"] is True
    assert week["paris"]["lat"] == 48.8566

    _period, month = _by_slug("1 month")
    assert set(month) == {"paris", "london", "rome", "lisbon"}
    assert month["paris"]["published_count"] == 2
    assert month["paris"]["quality_score"] == 85
    assert month["paris"]["keywords"] == ["Gastronomy", "Architecture"]

    _period, everyone = _by_slug("all")
    assert [item for item in (point["slug"] for point in build_globe_map("all", RECORDS, now=NOW)["cities"])] == [
        "paris",
        "seoul",
        "tokyo",
        "london",
        "rome",
        "lisbon",
    ]
    assert everyone["paris"]["city_ko"] == "파리"
    assert everyone["paris"]["published_count"] == 2
    assert everyone["rome"]["is_top"] is True
    assert everyone["lisbon"]["rank"] == 6
    assert everyone["lisbon"]["is_top"] is False
    assert "unknownville" not in everyone


def test_unknown_period_is_rejected():
    with pytest.raises(ValueError):
        build_globe_map("decade", RECORDS, now=NOW)


def test_catalog_files_use_frontmatter_dates(monkeypatch, tmp_path):
    guides, previous_store = _isolate_guides(monkeypatch, tmp_path)
    monkeypatch.setattr(globe_service, "_now", lambda moment=None: NOW)

    def article(date, tags):
        return '---\ndate: "{0}"\nhashtags: "{1}"\n---\n# City\n'.format(date, tags)

    (guides / "paris_guide.md").write_text(
        article("2026-09-28", "#Architecture #Gastronomy"),
        encoding="utf-8",
    )
    (guides / "seoul_guide.md").write_text(article("2026-08-01", "#Culture"), encoding="utf-8")
    (guides / "mystery_guide.md").write_text(article("2026-09-29", "#Nature"), encoding="utf-8")
    try:
        catalog = build_globe_map("1w")
        assert catalog["period"] == "1w"
        assert [item["slug"] for item in catalog["cities"]] == ["paris"]
        assert catalog["cities"][0]["keywords"] == ["Architecture", "Gastronomy"]
        assert catalog["cities"][0]["published_count"] == 1
        everyone = {item["slug"] for item in build_globe_map("all")["cities"]}
        assert everyone == {"paris", "seoul"}
    finally:
        _restore_store(previous_store)


def test_globe_cities_endpoint_filters_by_frontmatter_date(client, monkeypatch, tmp_path):
    guides, previous_store = _isolate_guides(monkeypatch, tmp_path)
    monkeypatch.setattr(globe_service, "_now", lambda moment=None: NOW)

    def article(date, tags):
        return '---\ndate: "{0}"\nhashtags: "{1}"\n---\n# City\n'.format(date, tags)

    (guides / "paris_guide.md").write_text(
        article("2026-09-28", "#Architecture #Gastronomy"),
        encoding="utf-8",
    )
    (guides / "seoul_guide.md").write_text(article("2026-08-01", "#Culture"), encoding="utf-8")
    (guides / "mystery_guide.md").write_text(article("2026-09-29", "#Nature"), encoding="utf-8")
    try:
        all_time = client.get("/api/v1/globe/cities")
        assert all_time.status_code == 200, all_time.text
        all_slugs = {item["slug"] for item in all_time.json()["cities"]}
        assert all_slugs == {"paris", "seoul"}
        week = client.get("/api/v1/globe/cities", params={"period": "1w"})
        assert week.status_code == 200, week.text
        body = week.json()
        assert body["period"] == "1w"
        assert [item["slug"] for item in body["cities"]] == ["paris"]
        rejected = client.get("/api/v1/globe/cities", params={"period": "nope"})
        assert rejected.status_code == 400
    finally:
        _restore_store(previous_store)
