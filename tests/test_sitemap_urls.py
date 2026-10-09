"""sitemap loc는 공개 SITE_URL을 쓰고 script 태그를 남기지 않는다."""

from xml.etree import ElementTree

from fastapi.testclient import TestClient

from app.main import app
from app.services import scheduler_service


def test_sitemap_uses_site_url_and_drops_scripts(monkeypatch, tmp_path):
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "rome_guide.md").write_text(
        "## Rome\n\nA walking route.\n\n<script src=\"https://evil.example/a.js\"></script>\n<script/>\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scheduler_service, "GUIDES_DIR", guides)
    monkeypatch.setattr(scheduler_service, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(scheduler_service, "SITEMAP_PATH", tmp_path / "output" / "sitemap.xml")
    monkeypatch.setenv("SITE_URL", "https://bluelogtrip.com")
    monkeypatch.setenv("VITE_SITE_URL", "")

    xml = scheduler_service.read_sitemap("http://127.0.0.1:8000")

    assert xml.lstrip().startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "https://bluelogtrip.com/" in xml
    assert "https://bluelogtrip.com/guide/rome_guide.md" in xml
    assert "https://bluelogtrip.com/guides/rome_guide.md" in xml
    assert "https://bluelogtrip.com/wallet" in xml
    assert "https://bluelogtrip.com/community" in xml
    assert "<changefreq>daily</changefreq>" in xml
    assert "<priority>1.0</priority>" in xml
    assert "<changefreq>weekly</changefreq>" in xml
    assert "<priority>0.8</priority>" in xml
    assert "127.0.0.1" not in xml
    assert "localhost" not in xml
    assert ":8000" not in xml
    assert "<script" not in xml.lower()
    assert 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in xml
    root = ElementTree.fromstring(xml)
    locations = [node.text or "" for node in root.iter() if node.tag.endswith("loc")]
    assert locations[0] == "https://bluelogtrip.com/"
    assert "https://bluelogtrip.com/guide/rome_guide.md" in locations
    assert "https://bluelogtrip.com/guides/rome_guide.md" in locations


def test_sitemap_response_is_xml_without_scripts():
    client = TestClient(app)
    for path in ("/sitemap.xml", "/api/v1/sitemap.xml"):
        response = client.get(path)
        assert response.status_code == 200
        content_type = response.headers["content-type"].lower()
        assert content_type.startswith("application/xml")
        assert "charset=utf-8" in content_type
        assert "<script" not in response.text.lower()
        assert response.text.lstrip().startswith("<?xml")
        root = ElementTree.fromstring(response.text)
        locations = [node.text or "" for node in root.iter() if node.tag.endswith("loc")]
        assert locations[0].endswith("/")
        assert any(node.tag.endswith("changefreq") for node in root.iter())
        assert any(node.tag.endswith("priority") for node in root.iter())


def test_published_guide_urls_and_service_pages_are_listed(monkeypatch, tmp_path):
    monkeypatch.setattr(scheduler_service, "SITEMAP_PATH", tmp_path / "sitemap.xml")
    monkeypatch.setenv("SITE_URL", "https://bluelogtrip.com")
    monkeypatch.setenv("VITE_SITE_URL", "")

    xml = scheduler_service.read_sitemap("https://bluelogtrip.com")
    root = ElementTree.fromstring(xml)
    locations = [node.text or "" for node in root.iter() if node.tag.endswith("loc")]
    guide_locs = [loc for loc in locations if "/guides/" in loc and loc.endswith("_guide.md")]
    assert len(guide_locs) == 32
    assert "https://bluelogtrip.com/guides/seoul_guide.md" in guide_locs
    assert "https://bluelogtrip.com/guides/los_angeles_guide.md" in guide_locs
    assert "https://bluelogtrip.com/guides/dubrovnik_guide.md" in guide_locs
    assert "https://bluelogtrip.com/guide/seoul_guide.md" in locations
    for path in ("/events", "/wallet", "/promote-store", "/community", "/about", "/contact"):
        assert "https://bluelogtrip.com{0}".format(path) in locations


def test_localhost_origin_is_used_only_when_no_public_site_url(monkeypatch):
    monkeypatch.setenv("SITE_URL", "")
    monkeypatch.setenv("VITE_SITE_URL", "")

    assert scheduler_service.resolve_site_base_url("http://127.0.0.1:8000") == ""
    assert scheduler_service.resolve_site_base_url("http://localhost:5173") == "http://localhost:5173"
    assert scheduler_service.resolve_site_base_url("https://bluelogtrip.com") == "https://bluelogtrip.com"
