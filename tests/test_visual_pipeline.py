"""Pexels Fallback, 본문 이미지 주입, 영문 신디케이션을 검증한다."""

import asyncio

import httpx

from app.agents.syndication_agent import run_syndication_agent
from app.agents.writer_agent import build_writer_prompt
from app.schemas.guide_schema import ResearchOutput
from app.services.guide_service import inject_guide_images
from app.services.pexels_service import (
    UNSPLASH_CURATION,
    build_image_queries,
    fetch_travel_image,
)


def _research() -> ResearchOutput:
    return ResearchOutput(
        attractions=["Colosseum", "Trevi Fountain"],
        food_spots=["Trapizzino"],
        seo_keywords=["rome food tour"],
        target_currency="€",
        local_tip="Book the Colosseum for late afternoon.",
    )


class _Client:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        return self._response


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_missing_pexels_key_uses_unsplash(monkeypatch):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)

    def fail_client(*args, **kwargs):
        raise AssertionError("Pexels must not be called without an API key")

    monkeypatch.setattr(httpx, "AsyncClient", fail_client)
    image = asyncio.run(fetch_travel_image("Rome travel", fallback_index=0))

    assert image["source"] == "unsplash"
    assert image["url"] == UNSPLASH_CURATION[0]
    assert image["photographer"] == "Unsplash"
    assert image["url"].startswith("https://images.unsplash.com/")


def test_quota_exceeded_uses_unsplash(monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _Client(_Response(429)))

    image = asyncio.run(fetch_travel_image("Rome food", fallback_index=1))

    assert image["source"] == "unsplash"
    assert image["url"] == UNSPLASH_CURATION[1]
    assert image["photographer"] == "Unsplash"


def test_pexels_success_keeps_photographer(monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    payload = {
        "photos": [
            {
                "alt": "Rome street at dusk",
                "photographer": "Ada Lovelace",
                "photographer_url": "https://www.pexels.com/@ada",
                "src": {"large2x": "https://images.pexels.com/photos/1.jpeg"},
            }
        ]
    }
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: _Client(_Response(200, payload)),
    )

    image = asyncio.run(fetch_travel_image("Rome"))

    assert image["source"] == "pexels"
    assert image["url"] == "https://images.pexels.com/photos/1.jpeg"
    assert image["photographer"] == "Ada Lovelace"
    assert image["photographer_url"] == "https://www.pexels.com/@ada"


def test_queries_follow_place_and_food_keywords():
    queries = build_image_queries(
        "Rome",
        attractions=["Colosseum", "Rome"],
        food_spots=["Trapizzino"],
    )
    assert queries == ["Rome", "Colosseum", "Trapizzino"]


def test_images_are_injected_as_thumbnail_and_section_footer():
    markdown = "## Sights\n\nColosseum.\n\n## Food\n\nPasta.\n"
    images = [
        {
            "url": "https://images.pexels.com/a.jpg",
            "alt": "Rome",
            "photographer": "Ada",
            "photographer_url": "https://www.pexels.com/@ada",
        },
        {
            "url": "https://images.pexels.com/b.jpg",
            "alt": "Sights",
            "photographer": "Grace",
            "photographer_url": "https://www.pexels.com/@grace",
        },
        {
            "url": "https://images.unsplash.com/c.jpg",
            "alt": "Food",
            "photographer": "Unsplash",
            "photographer_url": "https://unsplash.com",
        },
    ]

    rendered = inject_guide_images(markdown, images)

    assert rendered.startswith("![Rome](https://images.pexels.com/a.jpg)")
    assert "*Photo by [Ada](https://www.pexels.com/@ada)*" in rendered
    assert rendered.index("Colosseum.") < rendered.index("https://images.pexels.com/b.jpg")
    assert rendered.index("https://images.pexels.com/b.jpg") < rendered.index("## Food")
    assert rendered.index("Pasta.") < rendered.index("https://images.unsplash.com/c.jpg")
    assert rendered.strip().endswith("*Photo by [Unsplash](https://unsplash.com)*")


def test_english_syndication_matches_writing_language():
    research = _research()
    english = run_syndication_agent("Rome", research, "rome_guide.md", target_language="English")
    korean = run_syndication_agent("Rome", research, "rome_guide.md", target_language="ko")

    english_copy = " ".join(
        [
            english.social_teasers[0],
            english.reddit.title,
            english.reddit.body,
            english.quora.question,
            english.pinterest.pin_title,
        ]
    )
    assert "Colosseum" in "{0} {1}".format(english.reddit.title, english.reddit.body)
    assert "actually helped on a first visit" not in english.reddit.title
    assert english.reddit.subreddit in {"travel", "solotravel", "Europe"}
    assert english.quora.question.startswith("What should you prioritize")
    assert english.pinterest.pin_title == "Rome travel route and where to eat"
    assert not any("\uac00" <= char <= "\ud7a3" for char in english_copy)
    korean_reddit = "{0} {1}".format(korean.reddit.title, korean.reddit.body)
    assert "첫 방문" not in korean_reddit
    assert not any("\uac00" <= char <= "\ud7a3" for char in korean_reddit)
    assert "Colosseum" in korean_reddit
    assert korean.quora.question.startswith("Rome에 처음")

    prompt = build_writer_prompt("Rome", research, target_language="en")
    assert "natural English" in prompt
    assert "Strictly generate 100% pure target language without mixing foreign phrases" in prompt
    assert "도쿄 여행 필수 라멘 투어" in prompt
