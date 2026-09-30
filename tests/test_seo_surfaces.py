"""ads.txt, robots.txt, Open Graph HTML, 그리고 K-Culture·제휴 상점 sitemap."""

from xml.etree import ElementTree

from fastapi.testclient import TestClient

from app.main import app
from app.models import rewards as reward_store
from app.services import opengraph_service, scheduler_service, seo_files


def test_ads_txt_uses_publisher_env_and_disables_without_one(monkeypatch, tmp_path):
    monkeypatch.setattr(seo_files, "FALLBACK_ADS_TXT", tmp_path / "missing-ads.txt")
    monkeypatch.setenv("VITE_ADSENSE_PUBLISHER_ID", "pub-1234567890123456")
    monkeypatch.setenv("ADSENSE_PUBLISHER_ID", "")
    monkeypatch.setenv("VITE_ADSENSE_CLIENT_ID", "")
    assert seo_files.ads_txt_body() == "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n"

    monkeypatch.setenv("VITE_ADSENSE_PUBLISHER_ID", "")
    monkeypatch.setenv("VITE_ADSENSE_CLIENT_ID", "ca-pub-9999999999999999")
    assert seo_files.ads_txt_body().startswith("google.com, pub-9999999999999999, DIRECT,")

    monkeypatch.setenv("VITE_ADSENSE_CLIENT_ID", "")
    assert seo_files.ads_txt_body().startswith("# ads.txt disabled")


def test_ads_and_robots_routes():
    client = TestClient(app)
    ads = client.get("/ads.txt")
    assert ads.status_code == 200
    assert ads.headers["content-type"].startswith("text/plain")
    assert "google.com," in ads.text or ads.text.startswith("# ads.txt disabled")

    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "User-agent: *" in robots.text
    assert "Allow: /" in robots.text
    assert "Sitemap: " in robots.text
    assert robots.text.strip().endswith("/sitemap.xml")


def test_opengraph_html_for_a_guide_and_kculture(tmp_path, monkeypatch):
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "seoul_kpop_guide.md").write_text(
        """---
title: "Seoul K-Pop Walk"
image_url: "https://images.example/seoul.jpg"
---
# Seoul K-Pop Walk

A morning ticket hall and an afternoon neighborhood.

""",
        encoding="utf-8",
    )
    monkeypatch.setattr(opengraph_service, "GUIDES_DIR", guides)
    monkeypatch.setattr(opengraph_service, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setenv("SITE_URL", "https://bluelogtrip.com")

    card = opengraph_service.resolve_share_card("/guide/seoul_kpop_guide.md", "https://bluelogtrip.com")
    assert card["title"].startswith("Seoul K-Pop Walk")
    assert card["image"] == "https://images.example/seoul.jpg"
    assert card["url"] == "https://bluelogtrip.com/guide/seoul_kpop_guide.md"

    html = opengraph_service.render_opengraph_html("/k-culture/k-pop", "https://bluelogtrip.com")
    assert 'property="og:title"' in html
    assert 'property="og:description"' in html
    assert 'property="og:url"' in html
    assert "https://bluelogtrip.com/k-culture/k-pop" in html
    assert 'name="twitter:card"' in html
    assert "<script" not in html.lower()

    client = TestClient(app)
    response = client.get("/api/v1/opengraph", params={"path": "/events", "site": "https://bluelogtrip.com"})
    assert response.status_code == 200
    assert "og:title" in response.text
    assert "Events" in response.text


def test_sitemap_lists_kculture_and_active_partners(monkeypatch, tmp_path):
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "rome_guide.md").write_text("# Rome\n\nA walking route.\n", encoding="utf-8")
    monkeypatch.setattr(scheduler_service, "GUIDES_DIR", guides)
    monkeypatch.setattr(scheduler_service, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(scheduler_service, "SITEMAP_PATH", tmp_path / "output" / "sitemap.xml")
    monkeypatch.setenv("SITE_URL", "https://bluelogtrip.com")
    monkeypatch.setenv("VITE_SITE_URL", "")
    monkeypatch.setenv("REWARDS_DB_PATH", str(tmp_path / "rewards.db"))

    conn = reward_store.connect(tmp_path / "rewards.db")
    partner_id = reward_store.insert_partner(
        conn,
        {
            "name": "Hanok Noodle",
            "city": "Seoul",
            "discount_rate": 10,
            "category": "food",
            "address": "Seoul",
            "contact_email": "shop@example.com",
            "phone": "",
            "store_description": "A noodle counter.",
            "catalog_images": "",
            "offered_benefit": "10% off",
            "voucher_points": 50,
            "created_at": "2026-10-01T00:00:00Z",
        },
    )
    reward_store.activate_partner(conn, partner_id, "rome_guide.md")
    conn.close()

    xml = scheduler_service.read_sitemap("http://127.0.0.1:8000")
    root = ElementTree.fromstring(xml)
    locations = [node.text or "" for node in root.iter() if node.tag.endswith("loc")]
    assert "https://bluelogtrip.com/k-culture" in locations
    assert "https://bluelogtrip.com/k-culture/k-food" in locations
    assert "https://bluelogtrip.com/k-culture/k-pop" in locations
    assert "https://bluelogtrip.com/guide/rome_guide.md" in locations
    assert "https://bluelogtrip.com/partners/{0}".format(partner_id) in locations
    assert "https://bluelogtrip.com/events" in locations
    tags = {node.tag.rsplit("}", 1)[-1] for node in root.iter()}
    assert {"loc", "lastmod", "changefreq", "priority"} <= tags
