"""기간 × 예산 매거진 파일명, 큐레이션 지시, 오프라인 본문.

LLM을 호출하지 않는다. 생성 스크립트와 프롬프트가 같은 표를 본다.
"""

import re
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from app.schemas.magazine_matrix import BUDGET_KEYS, DURATION_KEYS, MagazineMatrix
from app.services.content_variation import display_city, slugify_city


_MATRIX_NAME = re.compile(
    r"^(?P<city>.+)_(?P<duration>1_days|3_days|1_week)_(?P<budget>50usd|100usd|200usd|budget|luxury)_guide\.md$",
    re.IGNORECASE,
)
_FRONTMATTER = re.compile(r"^---\r?\n[\s\S]*?\r?\n---\r?\n?")

# 파일명 토큰과 목록 필터 칩이 공유하는 표.
DURATION_LABELS = {
    "1_days": "1 Day",
    "3_days": "3 Days",
    "1_week": "1 Week",
}
BUDGET_LABELS = {
    "50usd": "Under $50/day",
    "100usd": "$100/day",
    "200usd": "$200/day",
    "budget": "Under $50/day",
    "luxury": "Luxury",
}
BUDGET_FILTERS = {
    "50usd": "under_50",
    "budget": "under_50",
    "100usd": "per_100",
    "200usd": "per_200",
    "luxury": "luxury",
}
BUDGET_TIERS = {
    "50usd": "value",
    "budget": "value",
    "100usd": "standard",
    "200usd": "comfort",
    "luxury": "luxury",
}
BUDGET_CAPS = {
    "50usd": 50,
    "budget": 50,
    "100usd": 100,
    "200usd": 200,
    "luxury": None,
}
DAY_HEADINGS = {
    "1_days": ["Day 1"],
    "3_days": ["Day 1", "Day 2", "Day 3"],
    "1_week": ["Days 1–2", "Days 3–4", "Days 5–6", "Day 7"],
}
_DURATION_ALIASES = {
    "1_day": "1_days",
    "1_days": "1_days",
    "one_day": "1_days",
    "3_day": "3_days",
    "3_days": "3_days",
    "three_days": "3_days",
    "1_week": "1_week",
    "one_week": "1_week",
    "week": "1_week",
}
_BUDGET_ALIASES = {
    "50usd": "50usd",
    "50": "50usd",
    "under50": "50usd",
    "under50day": "50usd",
    "under50usd": "50usd",
    "100usd": "100usd",
    "100": "100usd",
    "100day": "100usd",
    "200usd": "200usd",
    "200": "200usd",
    "200day": "200usd",
    "budget": "budget",
    "luxury": "luxury",
}

# 도시별 오프라인 동선. 없는 도시는 시장·역세권 틀로 채운다.
_CITY_CURATION = {
    "tokyo": {
        "transit": (
            "Ride Suica or Pasmo on the Yamanote loop and walk the last ten minutes. "
            "Changing lines twice costs more time than the fare saves."
        ),
        "zones": {
            "value": [
                ("Asakusa", "Be at Senso-ji before 9:00. Walk Nakamise once, then leave toward the Sumida before the lane becomes a shuffle."),
                ("Ueno and Yanaka", "Keep Ueno Park free. Skip the museum ticket unless it still fits the day cap, then walk the Yanaka slope."),
                ("Ameya-Yokocho", "Eat in the market. A stall with a short queue beats a picture-menu room on the main lane."),
                ("Kanda", "Use the last block for the book street and one standing meal before the train."),
            ],
            "standard": [
                ("Kiyosumi", "Start at the coffee street, then one paid garden ticket. Do not add a second museum."),
                ("Kuramae", "Walk the craft shops on foot. Buy one thing you can carry, or buy nothing."),
                ("Tokyo Station", "The useful stop is the basement food hall, not the shopping mall above it."),
                ("Ningyocho", "Keep the evening inside this neighborhood so the last train is one ride."),
            ],
            "comfort": [
                ("Kagurazaka", "Stay on the slope. Book one counter for the evening and do not cross the city after it."),
                ("Ebisu", "Use the afternoon for a gallery or a small garden, then eat south of the station."),
                ("Daikanyama", "Walk the back streets. A taxi is for the hop from Kagurazaka, not for every block."),
                ("Nakameguro", "End on the canal. One reserved seat is the spend; the walk is free."),
            ],
            "luxury": [
                ("Ginza", "Hold one basement counter, then stay on the side streets. The logo avenue is not the meal."),
                ("Azabudai", "Give the afternoon to one quiet room. Do not stack a second landmark."),
                ("Hiroo", "Walk to dinner. The reservation is the plan, not a list of doors."),
                ("Hibiya", "Close near the park so the car, if you use one, is a single hop back."),
            ],
        },
        "tables": {
            "value": [
                ("Standing soba", "Asakusa tachigui counter", "$4–8", "4.4/5"),
                ("Market stall", "Ameya-Yokocho skewer stall", "$6–10", "4.3/5"),
                ("Kissaten set", "Yanaka coffee shop", "$5–9", "4.5/5"),
                ("Station pickup", "Tokyo Station basement bento", "$8–12", "4.2/5"),
            ],
            "standard": [
                ("Set lunch", "Kiyosumi neighborhood kitchen", "$12–18", "4.4/5"),
                ("Craft cafe", "Kuramae side-street coffee", "$6–10", "4.3/5"),
                ("Basement meal", "Tokyo Station food-hall counter", "$14–22", "4.5/5"),
                ("Evening set", "Ningyocho local restaurant", "$18–28", "4.4/5"),
            ],
            "comfort": [
                ("Counter lunch", "Kagurazaka small restaurant", "$28–45", "4.6/5"),
                ("Cafe stop", "Daikanyama back street", "$8–14", "4.4/5"),
                ("Reserved dinner", "Ebisu counter seats", "$50–80", "4.7/5"),
                ("Canal dessert", "Nakameguro kissaten", "$10–16", "4.3/5"),
            ],
            "luxury": [
                ("Held counter", "Ginza depachika counter", "$60–120", "4.8/5"),
                ("Quiet lunch", "Azabudai dining room", "$70–140", "4.7/5"),
                ("Evening kaiseki", "Hiroo reserved counter", "$120–220", "4.8/5"),
                ("Tea stop", "Hibiya side-street salon", "$15–30", "4.5/5"),
            ],
        },
        "o2o": {
            "value": (
                "Charge Suica at a station machine or in the transit app, then collect a bento you held "
                "at the Tokyo Station basement counter. Ameya-Yokocho stays a cash stall. The phone only holds the station meal."
            ),
            "standard": (
                "Buy the garden ticket on the venue site and enter the gate with the QR code. "
                "Pick up the basement meal at the Tokyo Station counter you selected online. Both stops are in the district, not a delivery drop."
            ),
            "comfort": (
                "Hold the Kagurazaka counter on the restaurant's site, then take one taxi from the station to the slope. "
                "Pay the car in the taxi app if you want, and pay the meal at the counter."
            ),
            "luxury": (
                "Hold a Ginza food-hall counter through the store site, then sit in that room. "
                "The reservation is the online half. The meal is still a visit."
            ),
        },
    },
}

_TIER_PLACE_LINE = {
    "value": "Choose free grounds, market lunches, and at most one low ticket. Skip tasting menus.",
    "standard": "Allow one paid entry and sit-down set meals. Keep the second half of the day on foot.",
    "comfort": "Spend the cap on one reserved local counter and a single taxi hop, not on a longer checklist.",
    "luxury": "Spend on one reserved counter and a quiet room. Do not add stops to justify the budget.",
}
_TIER_MEAL_LINE = {
    "value": "Eat at offline counters and market stalls. They do not deliver. Order at the stall and sit nearby.",
    "standard": "Use neighborhood restaurants a resident would book for a weekday lunch. No hotel room service.",
    "comfort": "Book a local counter in person or on the shop's own site. Skip chains and hotel dining rooms.",
    "luxury": "The table is a held counter in a commercial district. It is still a local room, not a resort buffet.",
}
_CAP_LINE = {
    "value": "Keep transit, tickets, and meals inside $50 for the day.",
    "standard": "Plan about $100 for the day: one ticket, two meals, and the train.",
    "comfort": "About $200 covers one taxi hop, a reserved counter, and the train.",
    "luxury": "There is no daily cap. One serious table is the spend.",
}


def _blank(value: str) -> bool:
    return not str(value or "").strip()


def canonical_duration(value: str) -> str:
    token = re.sub(r"[\s-]+", "_", str(value or "").strip().casefold())
    key = _DURATION_ALIASES.get(token)
    if key is None or key not in DURATION_KEYS:
        raise ValueError("Unknown duration: {0}".format(value))
    return key


def canonical_budget(value: str) -> str:
    token = re.sub(r"[\s$/_-]+", "", str(value or "").strip().casefold())
    key = _BUDGET_ALIASES.get(token)
    if key is None or key not in BUDGET_KEYS:
        raise ValueError("Unknown budget: {0}".format(value))
    return key


def matrix_filename(city_slug: str, duration_key: str, budget_key: str) -> str:
    return "{0}_{1}_{2}_guide.md".format(city_slug, duration_key, budget_key)


def _hashtags(duration_key: str, budget_key: str) -> List[str]:
    duration_tag = {"1_days": "#OneDay", "3_days": "#ThreeDays", "1_week": "#OneWeek"}[duration_key]
    budget_tag = {
        "50usd": "#Under50",
        "budget": "#BudgetStay",
        "100usd": "#HundredADay",
        "200usd": "#TwoHundred",
        "luxury": "#LuxuryStay",
    }[budget_key]
    return [duration_tag, budget_tag, "#OfflineTable"]


def build_matrix(city: str, duration_key: str, budget_key: str) -> MagazineMatrix:
    slug = slugify_city(city)
    label = display_city(slug.replace("_", " "), "en")
    tier = BUDGET_TIERS[budget_key]
    return MagazineMatrix(
        city=label,
        city_slug=slug,
        duration_key=duration_key,
        duration_label=DURATION_LABELS[duration_key],
        budget_key=budget_key,
        budget_label=BUDGET_LABELS[budget_key],
        budget_filter=BUDGET_FILTERS[budget_key],
        filename=matrix_filename(slug, duration_key, budget_key),
        tier=tier,
        daily_cap_usd=BUDGET_CAPS[budget_key],
        title="{0}: {1} on {2}".format(label, DURATION_LABELS[duration_key], BUDGET_LABELS[budget_key]),
        title_form="matrix_{0}_{1}".format(duration_key, budget_key),
        hashtags=_hashtags(duration_key, budget_key),
        day_headings=list(DAY_HEADINGS[duration_key]),
    )


def resolve_matrix(city: str, duration: str = "", budget: str = "") -> Optional[MagazineMatrix]:
    """둘 다 비어 있으면 기존 단일 가이드. 하나만 있으면 오류."""
    if _blank(duration) and _blank(budget):
        return None
    if _blank(duration) or _blank(budget):
        raise ValueError("duration and budget must both be set")
    if _blank(city):
        raise ValueError("city is required")
    return build_matrix(city, canonical_duration(duration), canonical_budget(budget))


def parse_matrix_guide_id(guide_id: str) -> Optional[MagazineMatrix]:
    """매트릭스 파일명이면 도시·기간·예산을 되돌린다. 기존 `{city}_guide.md`는 None."""
    name = str(guide_id or "").strip().replace("\\", "/").split("/")[-1]
    match = _MATRIX_NAME.match(name)
    if match is None:
        return None
    city_slug = match.group("city").casefold()
    return build_matrix(
        city_slug.replace("_", " "),
        match.group("duration").casefold(),
        match.group("budget").casefold(),
    )


def _zones(spec: MagazineMatrix) -> List[Tuple[str, str]]:
    city_row = _CITY_CURATION.get(spec.city_slug)
    if city_row is not None:
        return list(city_row["zones"][spec.tier])
    city = spec.city
    return [
        ("{0} market".format(city), "Start at the morning market. Eat there before the lanes fill."),
        ("{0} station quarter".format(city), "Use the station retail halls for one pickup, then walk out of the mall."),
        ("{0} old streets".format(city), "Keep the afternoon inside one neighborhood so the return is a single ride."),
        ("{0} evening district".format(city), "End near the hotel. The last meal is a counter, not a tour."),
    ]


def _table(spec: MagazineMatrix) -> List[Tuple[str, str, str, str]]:
    city_row = _CITY_CURATION.get(spec.city_slug)
    if city_row is not None:
        return list(city_row["tables"][spec.tier])
    city = spec.city
    if spec.tier == "luxury":
        return [
            ("Held counter", "{0} commercial-district counter".format(city), "$60–140", "4.7/5"),
            ("Quiet lunch", "{0} side-street dining room".format(city), "$50–110", "4.6/5"),
            ("Evening table", "{0} reserved local restaurant".format(city), "$90–180", "4.8/5"),
            ("Tea stop", "{0} salon off the main avenue".format(city), "$12–24", "4.4/5"),
        ]
    if spec.tier == "comfort":
        return [
            ("Counter lunch", "{0} neighborhood restaurant".format(city), "$25–45", "4.5/5"),
            ("Cafe", "{0} back-street coffee".format(city), "$6–12", "4.3/5"),
            ("Reserved dinner", "{0} local counter".format(city), "$45–80", "4.6/5"),
            ("Sweet stop", "{0} station kissaten".format(city), "$8–14", "4.2/5"),
        ]
    if spec.tier == "standard":
        return [
            ("Set lunch", "{0} weekday kitchen".format(city), "$12–20", "4.4/5"),
            ("Market plate", "{0} covered market".format(city), "$8–14", "4.3/5"),
            ("Basement meal", "{0} station food hall".format(city), "$12–22", "4.4/5"),
            ("Evening set", "{0} side-street restaurant".format(city), "$16–28", "4.5/5"),
        ]
    return [
        ("Market stall", "{0} morning market stall".format(city), "$4–9", "4.3/5"),
        ("Standing meal", "{0} station counter".format(city), "$5–10", "4.2/5"),
        ("Coffee set", "{0} neighborhood kissaten".format(city), "$4–8", "4.4/5"),
        ("Pickup bento", "{0} station basement".format(city), "$7–12", "4.2/5"),
    ]


def _o2o(spec: MagazineMatrix) -> str:
    city_row = _CITY_CURATION.get(spec.city_slug)
    if city_row is not None:
        return city_row["o2o"][spec.tier]
    city = spec.city
    if spec.tier == "value":
        return (
            "Hold a station-basement bento in the retail app, then collect it at the {0} station counter. "
            "The market stalls stay cash. The phone is only the hold."
        ).format(city)
    if spec.tier == "standard":
        return (
            "Buy one sight ticket on the venue site and enter with the code. "
            "Pick up a meal you selected at the {0} station food hall. Both are visits, not deliveries."
        ).format(city)
    if spec.tier == "comfort":
        return (
            "Reserve the counter on the restaurant site, then take one taxi from {0} station to that street. "
            "Pay the meal at the table."
        ).format(city)
    return (
        "Hold a counter in the {0} commercial district through the store site, then sit in that room. "
        "The booking is online. The meal is on site."
    ).format(city)


def _transit(spec: MagazineMatrix) -> str:
    city_row = _CITY_CURATION.get(spec.city_slug)
    if city_row is not None:
        return city_row["transit"]
    return (
        "Use the city's day transit card and walk inside each district. "
        "A taxi is only for the {0} tier, and only once."
    ).format(spec.tier)


def curation_brief(spec: MagazineMatrix) -> Dict[str, str]:
    """프롬프트와 오프라인 본문이 같이 쓰는 큐레이션 문장."""
    zones = _zones(spec)
    route = " ".join("{0}: {1}".format(name, note) for name, note in zones[: len(spec.day_headings)])
    return {
        "route": route,
        "meals": _TIER_MEAL_LINE[spec.tier],
        "o2o": _o2o(spec),
        "places": _TIER_PLACE_LINE[spec.tier],
        "cap": _CAP_LINE[spec.tier],
        "transit": _transit(spec),
        "days": ", ".join(spec.day_headings),
    }


def matrix_prompt_block(spec: MagazineMatrix, language: str = "en") -> str:
    brief = curation_brief(spec)
    if language == "ko":
        return (
            "[기간 × 예산]\n"
            "- 도시: {city}\n"
            "- 체류: {duration} ({duration_key}). 이 길이만 쓰세요. 다른 일수로 늘리거나 줄이지 마세요.\n"
            "- 하루 예산: {budget} ({budget_key}). {cap}\n"
            "- 동선: {route}\n"
            "- 소제목: {days}\n"
            "- 오프라인 맛집: {meals}\n"
            "- O2O 상권: {o2o}\n"
            "- 장소 구성: {places}\n"
            "- 이동: {transit}"
        ).format(
            city=spec.city,
            duration=spec.duration_label,
            duration_key=spec.duration_key,
            budget=spec.budget_label,
            budget_key=spec.budget_key,
            cap=brief["cap"],
            route=brief["route"],
            days=brief["days"],
            meals=brief["meals"],
            o2o=brief["o2o"],
            places=brief["places"],
            transit=brief["transit"],
        )
    return (
        "[Duration x budget]\n"
        "- City: {city}\n"
        "- Duration: {duration} ({duration_key}). Write only this stay. Do not stretch or shrink the number of days.\n"
        "- Daily budget: {budget} ({budget_key}). {cap}\n"
        "- Route: {route}\n"
        "- Headings: {days}\n"
        "- Offline restaurants: {meals} Name specific counters in the cost table with realistic prices.\n"
        "- O2O district: {o2o}\n"
        "- Place mix: {places}\n"
        "- Getting around: {transit}"
    ).format(
        city=spec.city,
        duration=spec.duration_label,
        duration_key=spec.duration_key,
        budget=spec.budget_label,
        budget_key=spec.budget_key,
        cap=brief["cap"],
        route=brief["route"],
        days=brief["days"],
        meals=brief["meals"],
        o2o=brief["o2o"],
        places=brief["places"],
        transit=brief["transit"],
    )


def prompt_block_for(city: str, duration: str = "", budget: str = "", language: str = "en") -> str:
    spec = resolve_matrix(city, duration, budget)
    if spec is None:
        return ""
    return matrix_prompt_block(spec, language)


def build_matrix_article_prompt(spec: MagazineMatrix) -> str:
    """일일 생성기와 같은 영어 가이드 골격에 기간·예산 표를 붙인다."""
    block = matrix_prompt_block(spec, "en")
    return (
        "Write an original English SEO travel magazine for {city}.\n"
        "Do not wrap the answer in markdown fences. Do not add YAML frontmatter. "
        "Do not include HTML or script tags.\n"
        "{block}\n"
        "Structure:\n"
        "1. One H1 title exactly: {title}\n"
        "2. Two short paragraphs for a first-time visitor on this budget.\n"
        "3. An H2 '{duration} in {city}' with these H3 headings: {days}. "
        "Each heading needs a neighborhood route, timing, and one practical warning.\n"
        "4. An H2 'Getting Around'.\n"
        "5. An H2 'Where to Eat in {city}' and this Markdown table, with at least four offline places:\n"
        "| Category | Recommended Location | Estimated Cost | Rating |\n"
        "| --- | --- | --- | --- |\n"
        "6. An H2 'O2O District' explaining the reserve-online, visit-in-person stop.\n"
        "7. An H2 'Local Tip' with one paragraph a guidebook usually skips.\n"
        "Keep the guide between 650 and 900 words. Sound like a careful local editor, not a brochure."
    ).format(
        city=spec.city,
        block=block,
        title=spec.title,
        duration=spec.duration_label,
        days=", ".join(spec.day_headings),
    )


def _yaml_quote(value: str) -> str:
    escaped = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return '"{0}"'.format(escaped)


def _table_markdown(rows: Sequence[Tuple[str, str, str, str]]) -> str:
    lines = [
        "| Category | Recommended Location | Estimated Cost | Rating |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append("| {0} | {1} | {2} | {3} |".format(*row))
    return "\n".join(lines)


def render_offline_guide(spec: MagazineMatrix, today: Optional[date] = None) -> str:
    """API 키 없이 기간·예산 규칙으로 마크다운 파일을 만든다."""
    brief = curation_brief(spec)
    zones = _zones(spec)
    sections: List[str] = []
    for index, heading in enumerate(spec.day_headings):
        name, note = zones[index % len(zones)]
        sections.append("### {0}: {1}\n\n{2} {3}".format(heading, name, note, brief["cap"]))
    body = "\n\n".join(
        [
            "# {0}".format(spec.title),
            (
                "{city} on a {duration} stay only works if the budget decides the route before the map does. "
                "This magazine keeps the walk inside a few neighborhoods and spends {budget_label} on meals you eat on site."
            ).format(city=spec.city, duration=spec.duration_label.lower(), budget_label=spec.budget_label),
            "{0} {1}".format(brief["places"], brief["meals"]),
            "## {0} in {1}\n\n{2}".format(spec.duration_label, spec.city, "\n\n".join(sections)),
            "## Getting Around\n\n{0}".format(brief["transit"]),
            "## Where to Eat in {0}\n\n{1}\n\n{2}".format(spec.city, brief["meals"], _table_markdown(_table(spec))),
            "## O2O District\n\n{0}".format(brief["o2o"]),
            (
                "## Local Tip\n\n"
                "Order at the counter before you look for a seat. On this budget the useful line is the short one "
                "inside the market, not the restaurant with a host at the door. Leave when the district fills, "
                "even if the list still has one more stop."
            ),
            " ".join(spec.hashtags),
        ]
    )
    stamp = (today or date.today()).isoformat()
    front = "\n".join(
        [
            "---",
            "title: {0}".format(_yaml_quote(spec.title)),
            "date: {0}".format(_yaml_quote(stamp)),
            "city: {0}".format(_yaml_quote(spec.city)),
            'status: "Verified Travel Guide"',
            "duration: {0}".format(_yaml_quote(spec.duration_label)),
            "duration_key: {0}".format(_yaml_quote(spec.duration_key)),
            "budget: {0}".format(_yaml_quote(spec.budget_label)),
            "budget_key: {0}".format(_yaml_quote(spec.budget_key)),
            "title_form: {0}".format(_yaml_quote(spec.title_form)),
            "hashtags: {0}".format(_yaml_quote(" ".join(spec.hashtags))),
            "---",
            "",
        ]
    )
    return front + body.strip() + "\n"


def attach_matrix_frontmatter(markdown: str, spec: MagazineMatrix, today: Optional[date] = None) -> str:
    """모델 본문 앞에 기간·예산 메타데이터를 붙인다. 이미 있는 프론트매터는 교체한다."""
    body = _FRONTMATTER.sub("", markdown or "").strip()
    tags = " ".join(spec.hashtags)
    if tags not in body:
        body = "{0}\n\n{1}".format(body.rstrip(), tags)
    stamped = render_offline_guide(spec, today=today)
    header = stamped.split("---", 2)[1]
    return "---{0}---\n\n{1}\n".format(header, body.strip())


EXAMPLE_MATRIX: Tuple[Tuple[str, str, str], ...] = (
    ("Tokyo", "1_days", "50usd"),
    ("Tokyo", "3_days", "200usd"),
    ("Tokyo", "1_week", "budget"),
)
