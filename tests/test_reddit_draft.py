"""해외 Reddit 초안: 영문, 도시 스팟, 스타일·서브레딧 분산."""

from pathlib import Path

from app.agents.syndication_agent import run_syndication_agent
from app.schemas.guide_schema import ResearchOutput
from app.services.reddit_draft_service import (
    build_reddit_draft,
    recommend_subreddit,
    select_post_style,
)

def _has_hangul(text: str) -> bool:
    return any("\uac00" <= char <= "\ud7a3" for char in text)


def test_japanese_and_european_subreddits_follow_region():
    for city in ("Tokyo", "Osaka", "Kyoto"):
        assert recommend_subreddit(city) in {"JapanTravel", "travel"}
    japan = {recommend_subreddit(city) for city in ("Tokyo", "Osaka", "Kyoto", "Hiroshima", "Nara", "Fukuoka")}
    assert "JapanTravel" in japan
    assert "travel" in japan

    for city in ("Prague", "Paris", "Rome", "Barcelona"):
        assert recommend_subreddit(city) in {"travel", "solotravel", "Europe"}
    europe = {
        recommend_subreddit(city)
        for city in ("Prague", "Paris", "Rome", "Barcelona", "Vienna", "Lisbon", "Amsterdam", "Berlin")
    }
    assert europe == {"travel", "solotravel", "Europe"}

    for city in ("Taipei", "New York", "Singapore", "Seoul"):
        assert recommend_subreddit(city) in {"travel", "solotravel"}
        assert recommend_subreddit(city) != "Europe"
        assert recommend_subreddit(city) != "JapanTravel"


def test_post_styles_rotate_across_cities():
    styles = {
        select_post_style(city)
        for city in ("Osaka", "Prague", "Taipei", "Tokyo", "Kyoto", "Rome", "Paris", "London")
    }
    assert styles == {"experience", "question", "tips"}


def test_osaka_prague_taipei_drafts_use_real_spots_and_english():
    osaka = build_reddit_draft(
        "Osaka",
        attractions=["Dotonbori", "Universal Studios Japan"],
        food_spots=["Takoyaki"],
        local_tip="도톤보리는 해 진 뒤에 네온이 낫다.",
        currency="¥",
        article_markdown="## Day plan\n\nA 3-day loop.\n",
    )
    prague = build_reddit_draft(
        "Prague",
        attractions=["Old Town Square", "Charles Bridge"],
        food_spots=["Lokál"],
        local_tip="Cross Charles Bridge before 8am.",
        currency="Kč",
    )
    taipei = build_reddit_draft(
        "Taipei",
        attractions=["Taipei 101", "Shilin Night Market"],
        currency="NT$",
    )

    drafts = (osaka, prague, taipei)
    assert {item["style"] for item in drafts} == {"experience", "question", "tips"}
    assert osaka["subreddit"] in {"JapanTravel", "travel"}
    assert prague["subreddit"] in {"travel", "solotravel", "Europe"}
    assert taipei["subreddit"] in {"travel", "solotravel"}

    osaka_text = "{0}\n{1}".format(osaka["title"], osaka["body"])
    assert "Dotonbori" in osaka_text
    assert "Universal Studios Japan" in osaka_text
    assert "도톤보리" not in osaka_text
    assert "¥" in osaka["body"]
    assert "Tags: Osaka" in osaka["body"]
    assert "Japan" in osaka["body"]

    prague_text = "{0}\n{1}".format(prague["title"], prague["body"])
    assert "Old Town Square" in prague_text
    assert "Charles Bridge" in prague_text
    assert "Cross Charles Bridge before 8am." in prague["body"]
    assert "Europe" in prague["body"]

    taipei_text = "{0}\n{1}".format(taipei["title"], taipei["body"])
    assert "Taipei 101" in taipei_text
    assert "Shilin Night Market" in taipei_text
    assert "Tags: Taipei" in taipei["body"]

    for draft in drafts:
        blob = "{0}\n{1}".format(draft["title"], draft["body"])
        assert not _has_hangul(blob)
        assert "첫 방문" not in blob
        assert "actually helped on a first visit" not in blob


def test_style_titles_match_the_three_post_shapes():
    samples = {
        "experience": None,
        "question": None,
        "tips": None,
    }
    for city in ("Osaka", "Prague", "Taipei", "Tokyo", "Kyoto", "Rome", "Paris", "London", "Vienna"):
        style = select_post_style(city)
        if samples[style] is None:
            samples[style] = build_reddit_draft(city, attractions=["Sample Spot", "Second Stop"])
    assert samples["experience"]["title"].startswith("My ")
    assert "budget breakdown" in samples["experience"]["title"]
    assert samples["experience"]["title"].find("Sample Spot") > 0
    assert samples["question"]["title"].startswith("Is ")
    assert "enough" in samples["question"]["title"]
    assert "route around" in samples["question"]["title"]
    assert samples["tips"]["title"].startswith("Quick tips & transit guide for first-timers in ")
    assert "Sample Spot" in samples["tips"]["body"]


def test_guide_headings_override_the_fallback_list():
    article = Path("kyoto_guide.md").read_text(encoding="utf-8")
    draft = build_reddit_draft("Kyoto", article_markdown=article, attractions=["교토 후시미이나리"])
    text = "{0}\n{1}".format(draft["title"], draft["body"])
    assert "Fushimi Inari Taisha" in text
    assert "Arashiyama Bamboo Grove" in text or "Kinkaku-ji" in text
    assert not _has_hangul(text)
    assert draft["subreddit"] in {"JapanTravel", "travel"}


def test_korean_guide_still_gets_an_english_reddit_draft():
    research = ResearchOutput(
        attractions=["도톤보리", "유니버설 스튜디오 재팬"],
        food_spots=["타코야키"],
        seo_keywords=["오사카 가성비"],
        target_currency="¥",
        local_tip="네온은 저녁에 보는 편이 낫다.",
    )
    korean = run_syndication_agent("Osaka", research, "osaka_guide.md", target_language="ko")
    text = "{0}\n{1}".format(korean.reddit.title, korean.reddit.body)
    assert korean.reddit.subreddit in {"JapanTravel", "travel"}
    assert "Dotonbori" in text
    assert "Universal Studios Japan" in text
    assert not _has_hangul(text)
    assert "처음" in korean.quora.question
    assert _has_hangul(korean.pinterest.pin_title)


def test_new_guide_response_uses_article_spots_in_english():
    from app.services.guide_service import build_generate_response

    research = ResearchOutput(
        attractions=["도톤보리"],
        food_spots=["타코야키"],
        seo_keywords=["오사카 가성비"],
        target_currency="¥",
        local_tip="저녁에 보는 편이 낫다.",
    )
    response = build_generate_response(
        "Osaka",
        "## Dotonbori\n\nNight walk.\n\n## Osaka Castle\n\nMorning gate.\n",
        "test-research",
        "test-writer",
        research,
        target_language="ko",
    )
    text = "{0}\n{1}".format(response.syndication.reddit.title, response.syndication.reddit.body)
    assert "Dotonbori" in text
    assert "Osaka Castle" in text
    assert "도톤보리" not in text
    assert not _has_hangul(text)
    assert response.syndication.reddit.subreddit in {"JapanTravel", "travel"}


def test_english_guide_reddit_draft_stays_english_with_spots():
    research = ResearchOutput(
        attractions=["Colosseum", "Trevi Fountain"],
        food_spots=["Trapizzino"],
        seo_keywords=["rome food tour"],
        target_currency="€",
        local_tip="Book the Colosseum for late afternoon.",
    )
    english = run_syndication_agent(
        "Rome",
        research,
        "rome_guide.md",
        target_language="English",
        article_markdown="## Colosseum\n\nA 4-day plan.\n",
    )
    text = "{0}\n{1}".format(english.reddit.title, english.reddit.body)
    if not english.reddit.title.startswith("Quick tips"):
        assert "4-day" in english.reddit.title or "4 days" in english.reddit.title
    assert "Colosseum" in text
    assert "Trevi Fountain" in text
    assert english.reddit.subreddit in {"travel", "solotravel", "Europe"}
    assert english.quora.question.startswith("What should you prioritize")
    assert not _has_hangul(text)


def test_marketing_alert_rewrites_korean_boilerplate(monkeypatch, tmp_path):
    monkeypatch.setenv("STATS_DB_PATH", str(tmp_path / "visitor_stats.db"))
    from app.agents.marketing_agent import draft_reddit_post
    from app.services import stats_service

    stats_service.reset_visitor_cache()
    result = draft_reddit_post(
        {
            "id": "prague_guide.md",
            "article_markdown": "## Old Town Square\n\n## Charles Bridge\n\nA 3-day walk.\n",
            "syndication": {
                "reddit": {
                    "subreddit": "travel",
                    "title": "Prague 첫 방문 때 실제로 도움이 됐던 동선",
                    "body": "프라하를 처음 가는 기준으로 관광지와 식사를 하루 동선으로 묶어 봤다.",
                }
            },
        }
    )
    assert result["posted"] is False
    assert result["subreddit"] in {"travel", "solotravel", "Europe"}
    assert "Old Town Square" in result["markdown"]
    assert "Charles Bridge" in result["markdown"]
    assert "첫 방문" not in result["markdown"]
    assert not _has_hangul(result["markdown"])

    kept = draft_reddit_post(
        {
            "id": "kyoto_guide.md",
            "article_markdown": "![Fushimi](https://images.example/kyoto.jpg)\n\n## Walk\n",
            "syndication": {
                "reddit": {
                    "subreddit": "travel",
                    "title": "Kyoto without the main-strip rush",
                    "body": "We started at Fushimi before the tour groups.",
                }
            },
        }
    )
    assert kept["subreddit"] == "travel"
    assert "Kyoto without the main-strip rush" in kept["markdown"]
    assert "Fushimi" in kept["markdown"]
