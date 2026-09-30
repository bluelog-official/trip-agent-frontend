"""일정, 제목 형식, 해시태그가 도시마다 갈라지는지 검증한다."""

from app.services.content_variation import (
    Reserved,
    apply_variation,
    audit_varied_guide,
    build_daily_article_prompt,
    choose_variation,
    duration_key_for,
    vary_markdown,
    writer_duration_block,
)

_CITIES = [
    "Prague",
    "Lisbon",
    "Vienna",
    "Kyoto",
    "Taipei",
    "Osaka",
    "Singapore",
    "Danang",
    "Rome",
    "Seoul",
    "Paris",
    "Barcelona",
    "Tokyo",
    "New York",
    "Bangkok",
    "Sydney",
    "London",
    "Bali",
]

def _sample(city: str) -> str:
    days = []
    for number, name in enumerate(["Old town", "Museum", "Market", "A last walk, then the airport."], start=1):
        days.append(
            "### Day {0}: {1}\n\nWalk the neighborhood before the crowds. "
            "Leave time for the airport if this is the last day.\n".format(number, name)
        )
    return (
        "---\n"
        'title: "{city} in Four Days"\n'
        'city: "{city}"\n'
        "---\n"
        "# {city} in Four Days: A Walk\n\n"
        "{city} is easy on a first visit. This 3-night, 4-day route stays in a few neighborhoods.\n\n"
        "## A 3-Night, 4-Day {city} Itinerary\n\n"
        "{days}\n"
        "## Getting Around\n\n"
        "Use the local card for a 4-day trip.\n\n"
        "## Where to Eat in {city}\n\n"
        "| Category | Recommended Location | Estimated Cost | Rating |\n"
        "| --- | --- | --- | --- |\n"
        "| Lunch | A local room | $10 | 4.5/5 |\n\n"
        "## Local Tip\n\n"
        "Ask for the house water.\n"
    ).format(city=city, days="\n".join(days))


def test_known_cities_use_different_durations():
    assert duration_key_for("Prague") == "weekend"
    assert duration_key_for("Kyoto") == "three"
    assert duration_key_for("Rome") == "four"
    assert duration_key_for("Tokyo") == "five"
    assert duration_key_for("Bali") == "week"
    assert duration_key_for("Da Nang") == "three"


def test_batch_titles_and_hashtags_do_not_repeat():
    reserved = Reserved()
    titles = []
    forms = []
    tags = []
    for index, city in enumerate(_CITIES):
        updated, variation = vary_markdown(_sample(city), city, reserved, salt=index)
        assert not audit_varied_guide(updated), city
        assert "in Four Days" not in updated
        assert "A 3-Night, 4-Day" not in updated
        assert "3-night, 4-day" not in updated
        titles.append(variation.title)
        forms.append(variation.template_id)
        tags.append(tuple(variation.hashtags))
        assert 2 <= len(variation.hashtags) <= 4
    assert len(titles) == len(set(titles))
    assert len(forms) == len(set(forms))
    assert len(tags) == len(set(tags))
    assert sum("#LocalFood" in group for group in tags) < len(tags) / 2


def test_weekend_three_and_week_reshape_day_headings():
    reserved = Reserved()
    prague, prague_plan = vary_markdown(_sample("Prague"), "Prague", reserved, salt=0)
    tokyo, _tokyo_plan = vary_markdown(_sample("Tokyo"), "Tokyo", reserved, salt=1)
    bali, _bali_plan = vary_markdown(_sample("Bali"), "Bali", reserved, salt=2)
    assert prague_plan.duration_key == "weekend"
    assert "### Day 1 (Saturday):" in prague
    assert "### Day 2 (Sunday):" in prague
    assert "### Day 3:" not in prague
    assert "### Day 4:" not in tokyo or tokyo.count("### Day ") == 5
    assert tokyo.count("### Day ") == 5
    assert "### Days 1–2:" in bali
    assert "### Day 7:" in bali
    assert "One Week (7 Days)" in bali


def test_apply_is_idempotent():
    variation = choose_variation("Lisbon", Reserved(), salt=3, structural=True, language="en")
    once = apply_variation(_sample("Lisbon"), variation)
    twice = apply_variation(once, variation)
    assert once == twice
    assert "duration_key:" in once


def test_daily_prompt_follows_city_duration():
    weekend = choose_variation("Prague", Reserved(), structural=True, language="en")
    week = choose_variation("Bali", Reserved(), structural=True, language="en")
    weekend_prompt = build_daily_article_prompt("Prague", weekend)
    week_prompt = build_daily_article_prompt("Bali", week)
    assert "Day 1 (Saturday)" in weekend_prompt
    assert "Day 7" in week_prompt
    assert "3-night 4-day heading" in weekend_prompt
    assert "A Weekend in Prague" in weekend_prompt
    assert "in Four Days" not in weekend.title
    assert "in Four Days" not in week.title


def test_writer_prompt_drops_the_fixed_four_day_title():
    prompt = writer_duration_block("Kyoto", "en")
    assert "Duration for this city: 3 Days" in prompt
    assert "one four-day title" in prompt
    assert "#LocalFood" not in prompt
    korean = writer_duration_block("Kyoto", "ko")
    assert "3일" in korean
    assert "3박 4일" in korean
