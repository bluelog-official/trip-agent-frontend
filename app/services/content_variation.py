"""여행 가이드의 일정, 제목, 해시태그를 도시마다 다르게 고른다.

LLM을 호출하지 않는다. 생성기와 기존 마크다운 갱신이 같은 규칙을 쓴다.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_ROOT = Path(__file__).resolve().parents[2]
GUIDES_DIR = _ROOT / "guides"

_HANGUL = re.compile(r"[\uac00-\ud7a3]")
_DAY_LINE = re.compile(
    r"^### (?:Days?\s+(\d+)(?:\s*[–\-]\s*\d+)?(?:\s+\([^)]+\))?|(\d+)일\s*차)\s*:\s*(.*?)\s*$",
    re.MULTILINE,
)
_HASHTAG_LINE = re.compile(
    r"^(?:#[A-Za-z][A-Za-z0-9]*)(?:\s+#[A-Za-z][A-Za-z0-9]*)+\s*$"
)
_FRONTMATTER = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?")

# 도시 규모와 여행 방식. 모르는 도시는 이름 해시로 다섯 일정 중 하나를 고른다.
_CITY_DURATION = {
    "prague": "weekend",
    "lisbon": "weekend",
    "vienna": "weekend",
    "porto": "weekend",
    "edinburgh": "weekend",
    "dubrovnik": "weekend",
    "florence": "weekend",
    "kyoto": "three",
    "taipei": "three",
    "osaka": "three",
    "singapore": "three",
    "danang": "three",
    "chiang mai": "three",
    "busan": "three",
    "rome": "four",
    "seoul": "four",
    "paris": "four",
    "barcelona": "four",
    "madrid": "four",
    "amsterdam": "four",
    "berlin": "four",
    "tokyo": "five",
    "new york": "five",
    "bangkok": "five",
    "sydney": "five",
    "london": "five",
    "hong kong": "five",
    "los angeles": "five",
    "san francisco": "five",
    "mexico city": "five",
    "bali": "week",
    "hanoi": "week",
    "reykjavik": "week",
    "queenstown": "week",
    "cape town": "week",
    "vancouver": "week",
}

_SPAN_NOUN = {
    "weekend": "2 Days (Weekend)",
    "three": "3 Days",
    "four": "4 Days",
    "five": "5 Days",
    "week": "1 Week",
}
_SPAN_ARTICLE = {
    "weekend": "Weekend",
    "three": "3-Day",
    "four": "4-Day",
    "five": "5-Day",
    "week": "1-Week",
}
_SPAN_KO = {
    "weekend": "주말 2일",
    "three": "3일",
    "four": "4일",
    "five": "5일",
    "week": "1주일",
}
_SECTION_COUNT = {
    "weekend": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "week": 4,
}
_KO_CITY = {
    "los angeles": "로스앤젤레스",
    "new york": "뉴욕",
    "paris": "파리",
    "tokyo": "도쿄",
    "bali": "발리",
    "seoul": "서울",
    "osaka": "오사카",
    "kyoto": "교토",
    "busan": "부산",
}

# span 이 있으면 제목에 일정 길이가 들어간다. only 는 그 일정에만 쓴다.
_TEMPLATES = (
    {"id": "weekend_perfect", "lang": "en", "only": ("weekend",), "text": "A Perfect Weekend in {city}"},
    {"id": "exploring", "lang": "en", "text": "Exploring {city}: A {article} Itinerary"},
    {"id": "spots_food", "lang": "en", "text": "{city} Travel Guide: Top Spots & Food"},
    {"id": "how_to_spend", "lang": "en", "text": "How to Spend {noun} in {city}"},
    {"id": "where_to_go", "lang": "en", "text": "{city}: Where to Go in {noun}"},
    {"id": "slower_route", "lang": "en", "text": "{noun} in {city}: A Slower Route"},
    {"id": "first_time", "lang": "en", "text": "First Time in {city}: {noun}"},
    {"id": "neighborhoods", "lang": "en", "text": "{city} Neighborhood by Neighborhood"},
    {"id": "local_edit", "lang": "en", "text": "The {article} {city} Edit"},
    {"id": "on_foot", "lang": "en", "text": "{city} on Foot for {noun}"},
    {"id": "locals", "lang": "en", "text": "A Local Route Through {city} ({noun})"},
    {"id": "without_rush", "lang": "en", "text": "{city} Without the Rush: {noun}"},
    {"id": "what_to_do", "lang": "en", "text": "What to Do in {city} for {noun}"},
    {"id": "trip_notes", "lang": "en", "text": "{city} Trip Notes for {noun}"},
    {"id": "see_city", "lang": "en", "text": "See {city} in {noun}"},
    {"id": "walkers", "lang": "en", "text": "{city} for Travelers Who Walk"},
    {"id": "inside", "lang": "en", "text": "Inside {city}: {noun} Worth Planning"},
    {"id": "day_by_day", "lang": "en", "text": "{city} Day by Day: {noun}"},
    {"id": "wander", "lang": "en", "text": "Where to Eat and Wander in {city}"},
    {"id": "city_guide", "lang": "en", "text": "{city}: A {article} City Guide"},
    {"id": "pace", "lang": "en", "text": "A {article} Pace for {city}"},
    {"id": "open_hours", "lang": "en", "text": "{city} With Time to Spare ({noun})"},
    {"id": "field_notes", "lang": "en", "text": "Field Notes from {city}: {noun}"},
    {"id": "stay_close", "lang": "en", "text": "Stay Close in {city} for {noun}"},
    {"id": "ko_weekend", "lang": "ko", "only": ("weekend",), "text": "{ko} 주말 여행"},
    {"id": "ko_course", "lang": "ko", "text": "{ko} {ko_noun} 여행 코스"},
    {"id": "ko_spots", "lang": "ko", "text": "{ko} 여행 가이드: 명소와 맛집"},
    {"id": "ko_spend", "lang": "ko", "text": "{ko}에서 보내는 {ko_noun}"},
    {"id": "ko_walk", "lang": "ko", "text": "{ko_noun}로 걷는 {ko}"},
    {"id": "ko_lanes", "lang": "ko", "text": "{ko} 골목 일정 ({ko_noun})"},
    {"id": "ko_first", "lang": "ko", "text": "처음 가는 {ko}: {ko_noun}"},
    {"id": "ko_slow", "lang": "ko", "text": "서두르지 않는 {ko} {ko_noun}"},
)

_POOLS = {
    "prague": ["#Culture", "#Architecture", "#Nightlife", "#CityBreak", "#Photography", "#WeekendTrip"],
    "lisbon": ["#CityBreak", "#HiddenGems", "#Culture", "#SoloTravel", "#WeekendTrip", "#Photography"],
    "vienna": ["#Culture", "#Museums", "#Architecture", "#CityBreak", "#WeekendTrip", "#Photography"],
    "kyoto": ["#Culture", "#Nature", "#HiddenGems", "#SlowTravel", "#SoloTravel", "#Photography"],
    "taipei": ["#CityBreak", "#HiddenGems", "#Nightlife", "#Culture", "#SoloTravel", "#Photography"],
    "osaka": ["#Nightlife", "#CityBreak", "#HiddenGems", "#SoloTravel", "#Culture", "#Photography"],
    "singapore": ["#Nature", "#CityBreak", "#Architecture", "#SoloTravel", "#Photography", "#HiddenGems"],
    "danang": ["#Nature", "#Beach", "#SlowTravel", "#SoloTravel", "#HiddenGems", "#Photography"],
    "rome": ["#Culture", "#Architecture", "#Museums", "#CityBreak", "#HiddenGems", "#Photography"],
    "seoul": ["#CityBreak", "#Nightlife", "#Culture", "#HiddenGems", "#SoloTravel", "#Photography"],
    "paris": ["#Culture", "#Museums", "#Architecture", "#HiddenGems", "#CityBreak", "#Photography"],
    "barcelona": ["#Architecture", "#Culture", "#Beach", "#Nightlife", "#CityBreak", "#Photography"],
    "tokyo": ["#CityBreak", "#Nightlife", "#Culture", "#SoloTravel", "#HiddenGems", "#Photography"],
    "new york": ["#CityBreak", "#Culture", "#SoloTravel", "#Nightlife", "#Architecture", "#Photography"],
    "bangkok": ["#Nightlife", "#Culture", "#HiddenGems", "#CityBreak", "#SoloTravel", "#Photography"],
    "sydney": ["#Nature", "#Beach", "#CityBreak", "#SoloTravel", "#Photography", "#SlowTravel"],
    "london": ["#Culture", "#Museums", "#CityBreak", "#HiddenGems", "#SoloTravel", "#Architecture"],
    "bali": ["#Nature", "#Beach", "#SlowTravel", "#HiddenGems", "#SoloTravel", "#Photography"],
    "los angeles": ["#CityBreak", "#Beach", "#Nightlife", "#SoloTravel", "#Photography", "#Nature"],
}
_DEFAULT_POOL = [
    "#CityBreak",
    "#Culture",
    "#HiddenGems",
    "#SoloTravel",
    "#Nature",
    "#Photography",
    "#Architecture",
    "#SlowTravel",
]
# 음식 태그는 음식 도시 일부에만 넣고, 전 글에 #LocalFood 를 붙이지 않는다.
_FOOD_ACCENT = {
    "osaka": "#StreetFood",
    "bangkok": "#StreetFood",
    "taipei": "#Foodie",
    "singapore": "#LocalFood",
    "vienna": "#LocalFood",
    "danang": "#Foodie",
}
_FILLERS = ["#Photography", "#SoloTravel", "#HiddenGems", "#SlowTravel", "#WeekendTrip", "#Architecture"]

_WEEK_NOTES = [
    "Use the first two days for this route and leave the second afternoon open.",
    "Keep the next two days inside this area instead of adding another district.",
    "Give this part two days so the transfer does not replace the place you came to see.",
    "Keep the last day slow: the same area in the morning, then the airport buffer.",
]
_WEEK_NOTES_KO = [
    "처음 이틀은 이 동선만 움직이고 둘째 날 오후는 비워 두세요.",
    "다음 이틀은 같은 지역 안에 머무르세요.",
    "이동으로 일정이 지워지지 않게 이 구간은 이틀을 쓰세요.",
    "마지막 날은 오전만 같은 지역에 두고 공항으로 이동하세요.",
]
_DEPARTURE = re.compile(
    r"airport|depart|flight|Heathrow|Gatwick|Incheon|Taoyuan|Kansai|Narita|Haneda|"
    r"Changi|LAX|Suvarnabhumi|Don Mueang|출국|공항",
    re.IGNORECASE,
)


class Variation(object):
    """한 편의 가이드에 붙일 일정, 제목 형식, 해시태그."""

    def __init__(
        self,
        city: str,
        duration_key: str,
        template_id: str,
        title: str,
        hashtags: Sequence[str],
        language: str,
    ):
        self.city = city
        self.duration_key = duration_key
        self.template_id = template_id
        self.title = title
        self.hashtags = list(hashtags)
        self.language = language

    @property
    def label(self) -> str:
        if self.duration_key == "free":
            return ""
        if self.language == "ko":
            return _SPAN_KO[self.duration_key]
        return _SPAN_NOUN[self.duration_key]


class Reserved(object):
    """이미 쓴 제목 형식과 해시태그 조합. 다음 글이 같은 패턴을 피하게 한다."""

    def __init__(self):
        self.templates: Dict[str, int] = {}
        self.tags = set()
        self.titles = set()

    def template_count(self, template_id: str) -> int:
        return self.templates.get(template_id, 0)

    def remember(self, variation: Variation) -> None:
        self.templates[variation.template_id] = self.template_count(variation.template_id) + 1
        self.tags.add(tuple(variation.hashtags))
        self.titles.add(variation.title)


def normalize_city(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()
    if text in {"da nang", "danang"}:
        return "danang"
    return text


def display_city(city: str, language: str = "en") -> str:
    key = normalize_city(city)
    if language == "ko" and key in _KO_CITY:
        return _KO_CITY[key]
    if key == "danang":
        return "Da Nang"
    return " ".join(part.capitalize() for part in key.split())


def slugify_city(city: str) -> str:
    key = normalize_city(city)
    return key.replace(" ", "_") or "city"


def stable_index(text: str) -> int:
    total = 0
    for index, char in enumerate(text or ""):
        total += (index + 1) * ord(char)
    return total


def duration_key_for(city: str) -> str:
    key = normalize_city(city)
    if key in _CITY_DURATION:
        return _CITY_DURATION[key]
    cycle = ("weekend", "three", "four", "five", "week")
    return cycle[stable_index(key) % len(cycle)]


def document_language(markdown: str) -> str:
    sample = _FRONTMATTER.sub("", markdown or "")[:800]
    if _HANGUL.search(sample):
        return "ko"
    return "en"


def has_day_sections(markdown: str) -> bool:
    return len(_DAY_LINE.findall(markdown or "")) >= 2


def detect_day_count(markdown: str) -> Optional[int]:
    """일정 소제목이 없을 때 본문에 적힌 일수. 구조를 바꿀 수 없으면 제목이 이 일수를 따른다."""
    match = re.search(r"\b([2-7])\s*[- ]days?\b", markdown or "", re.IGNORECASE)
    if match:
        return int(match.group(1))
    if re.search(r"3박\s*4일|3박4일", markdown or ""):
        return 4
    if re.search(r"일주일|1주일", markdown or ""):
        return 7
    return None


def _resolve_duration(city: str, structural: bool, detected: Optional[int]) -> str:
    if structural:
        return duration_key_for(city)
    mapped = {2: "weekend", 3: "three", 4: "four", 5: "five", 7: "week"}
    if detected in mapped:
        return mapped[detected]
    return "free"


def _template_fits(spec: dict, duration_key: str, language: str) -> bool:
    if spec["lang"] != language:
        return False
    only = spec.get("only")
    if only and duration_key not in only:
        return False
    uses_span = any(token in spec["text"] for token in ("{noun}", "{article}", "{ko_noun}"))
    if duration_key == "free" and uses_span:
        return False
    return True


def _render_title(spec: dict, city: str, duration_key: str, language: str) -> str:
    noun = _SPAN_NOUN.get(duration_key, "")
    article = _SPAN_ARTICLE.get(duration_key, "")
    ko_noun = _SPAN_KO.get(duration_key, "")
    ko_name = display_city(city, "ko") if language == "ko" else display_city(city, "en")
    return spec["text"].format(
        city=display_city(city, "en"),
        noun=noun,
        article=article,
        ko=ko_name,
        ko_noun=ko_noun,
    )


def _pool_for(city: str) -> List[str]:
    pool = list(_POOLS.get(normalize_city(city), _DEFAULT_POOL))
    accent = _FOOD_ACCENT.get(normalize_city(city))
    if accent:
        pool = [accent] + [tag for tag in pool if tag != accent]
    return pool


def _pick_template(city: str, duration_key: str, language: str, salt: int, reserved: Reserved) -> dict:
    candidates = [spec for spec in _TEMPLATES if _template_fits(spec, duration_key, language)]
    if not candidates:
        candidates = [spec for spec in _TEMPLATES if spec["lang"] == language and "only" not in spec]
    start = (stable_index(normalize_city(city)) + salt) % len(candidates)
    rotated = candidates[start:] + candidates[:start]
    rotated.sort(key=lambda spec: reserved.template_count(spec["id"]))
    for spec in rotated:
        title = _render_title(spec, city, duration_key, language)
        if title not in reserved.titles and "in Four Days" not in title:
            return spec
    return rotated[0]


def _pick_hashtags(city: str, salt: int, reserved: Reserved) -> List[str]:
    pool = _pool_for(city)
    count = 2 + ((stable_index(normalize_city(city)) + salt) % 3)
    accent = _FOOD_ACCENT.get(normalize_city(city))
    for shift in range(len(pool) * 2):
        chosen: List[str] = []
        if accent:
            chosen.append(accent)
        cursor = 0
        while len(chosen) < count and cursor < len(pool) * 2:
            tag = pool[(stable_index(normalize_city(city)) + salt + shift + cursor) % len(pool)]
            cursor += 1
            if tag not in chosen:
                chosen.append(tag)
        if tuple(chosen) not in reserved.tags and "#LocalFood" != (chosen[0] if len(chosen) == 1 else ""):
            if not (len(chosen) == 1 and chosen[0] == "#LocalFood"):
                return chosen[:4]
    fallback = ["#CityBreak", "#Culture"]
    extra = _FILLERS[(stable_index(normalize_city(city)) + salt) % len(_FILLERS)]
    if extra not in fallback:
        fallback.append(extra)
    return fallback[:count]


def choose_variation(
    city: str,
    reserved: Reserved,
    salt: int = 0,
    structural: bool = True,
    detected_days: Optional[int] = None,
    language: str = "en",
) -> Variation:
    duration_key = _resolve_duration(city, structural, detected_days)
    spec = _pick_template(city, duration_key, language, salt, reserved)
    title = _render_title(spec, city, duration_key, language)
    hashtags = _pick_hashtags(city, salt, reserved)
    return Variation(
        city=display_city(city, "en"),
        duration_key=duration_key,
        template_id=spec["id"],
        title=title,
        hashtags=hashtags,
        language=language,
    )


def itinerary_heading(variation: Variation) -> str:
    city = display_city(variation.city, variation.language)
    key = variation.duration_key
    if variation.language == "ko":
        labels = {
            "weekend": "{0} 주말 일정".format(city),
            "three": "{0} 3일 일정".format(city),
            "four": "{0} 4일 일정".format(city),
            "five": "{0} 5일 일정".format(city),
            "week": "{0} 1주일(7일) 일정".format(city),
        }
        return labels.get(key, "{0} 여행 일정".format(city))
    if key == "weekend":
        return "A Weekend in {0}".format(city)
    if key == "three":
        return "3 Days in {0}".format(city)
    if key == "five":
        return "5 Days in {0}".format(city)
    if key == "week":
        return "One Week (7 Days) in {0}".format(city)
    options = [
        "Four Days in {0}",
        "A 4-Day Route through {0}",
        "{0} in 4 Days, Neighborhood by Neighborhood",
        "Day by Day: 4 Days in {0}",
    ]
    return options[stable_index(variation.template_id) % len(options)].format(city)


def prompt_day_rule(variation: Variation) -> str:
    key = variation.duration_key
    if key == "weekend":
        return (
            "two H3 sections labeled 'Day 1 (Saturday)' and 'Day 2 (Sunday)'. "
            "Each day needs a neighborhood route, timing, and one practical warning."
        )
    if key == "week":
        return (
            "four H3 sections labeled 'Days 1–2', 'Days 3–4', 'Days 5–6', and 'Day 7'. "
            "Each block needs a neighborhood route, timing, and one practical warning."
        )
    count = {"three": 3, "four": 4, "five": 5}.get(key, 4)
    return (
        "{0} H3 sections labeled Day 1 through Day {0}. "
        "Each day needs a neighborhood route, timing, and one practical warning."
    ).format(count)


def build_daily_article_prompt(city: str, variation: Variation) -> str:
    """일일 생성기가 쓰던 '3박 4일' 고정 지시 대신, 이 도시의 일정을 넣는다."""
    heading = itinerary_heading(variation)
    return (
        "Write an original English SEO travel guide for {city}.\n"
        "Do not wrap the answer in markdown fences. Do not add YAML frontmatter. "
        "Do not include HTML or script tags. Do not add hashtags.\n"
        "Do not default to a four-day title or a 3-night 4-day heading.\n"
        "Structure:\n"
        "1. One H1 title exactly: {title}\n"
        "2. A summary of two short paragraphs for a first-time visitor.\n"
        "3. An H2 '{heading}' with {day_rule}\n"
        "4. An H2 'Getting Around' with the local transit card or the simplest way to move.\n"
        "5. An H2 'Where to Eat in {city}' followed by this exact Markdown table header and at least four rows:\n"
        "| Category | Recommended Location | Estimated Cost | Rating |\n"
        "| --- | --- | --- | --- |\n"
        "Use realistic local prices and name specific places a visitor can find.\n"
        "6. An H2 'Local Tip' with one paragraph a guidebook usually skips.\n"
        "Keep the guide between 650 and 900 words. Sound like a careful local editor, not a brochure."
    ).format(
        city=variation.city,
        title=variation.title,
        heading=heading,
        day_rule=prompt_day_rule(variation),
    )


def writer_duration_block(destination: str, language: str = "en") -> str:
    """Writer 프롬프트에 붙이는 일정·해시태그 지시. 도시마다 길이가 다르다."""
    variation = variation_for_new_article(destination)
    tags = " ".join(variation.hashtags)
    if language == "ko":
        label = _SPAN_KO.get(variation.duration_key, variation.label or "4일")
        return (
            "이 도시의 체류 일정은 {label}입니다. 일정 소제목과 본문의 며칠 표현을 그 길이에 맞추세요. "
            "모든 도시를 3박 4일 같은 형식으로 쓰지 마세요. "
            "제목에 '{{도시}} 3박 4일' 한 가지 형식만 반복하지 마세요. "
            "글의 마지막 줄에는 다음 해시태그만 넣고, 음식 태그를 모든 글에 붙이지 마세요: {tags}"
        ).format(label=label, tags=tags)
    label = variation.label or "4 Days"
    return (
        "10. Duration for this city: {label}. Itinerary H2: '{heading}'. {day_rule} "
        "Do not use one four-day title for every city. "
        "Match the number of days to {label}. "
        "11. End with this hashtag line only: {tags}"
    ).format(
        label=label,
        heading=itinerary_heading(variation),
        day_rule=prompt_day_rule(variation),
        city=variation.city,
        tags=tags,
    )


def _frontmatter_value(markdown: str, key: str) -> str:
    match = _FRONTMATTER.match(markdown or "")
    if not match:
        return ""
    found = re.search(r"^{0}:\s*\"?([^\"\n]+)\"?".format(re.escape(key)), match.group(1), re.MULTILINE)
    return found.group(1).strip() if found else ""


def _yaml_quote(value: str) -> str:
    escaped = (value or "").replace("\\", "\\\\").replace('"', '\\"')
    return '"{0}"'.format(escaped)


def _hashtag_tokens(markdown: str) -> List[str]:
    front = _frontmatter_value(markdown, "hashtags")
    if front:
        return front.split()
    for line in reversed((markdown or "").splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        if _HASHTAG_LINE.match(stripped):
            return stripped.split()
        break
    return []


def load_reserved(directory: Optional[Path] = None) -> Reserved:
    reserved = Reserved()
    folder = directory or GUIDES_DIR
    if not folder.is_dir():
        return reserved
    for path in sorted(folder.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        form = _frontmatter_value(text, "title_form")
        if form:
            reserved.templates[form] = reserved.template_count(form) + 1
        tags = _hashtag_tokens(text)
        if tags:
            reserved.tags.add(tuple(tags))
        title = _frontmatter_value(text, "title")
        if title:
            reserved.titles.add(title)
    return reserved


def variation_for_new_article(city: str, guides_dir: Optional[Path] = None) -> Variation:
    """이미 발행된 도시면 그 파일의 일정을 재사용하고, 아니면 겹치지 않는 새 조합을 고른다."""
    folder = guides_dir or GUIDES_DIR
    path = folder / "{0}_guide.md".format(slugify_city(city))
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        key = _frontmatter_value(text, "duration_key")
        form = _frontmatter_value(text, "title_form")
        title = _frontmatter_value(text, "title")
        tags = _hashtag_tokens(text)
        if key and form and title and tags:
            return Variation(
                city=display_city(_frontmatter_value(text, "city") or city, "en"),
                duration_key=key,
                template_id=form,
                title=title,
                hashtags=tags,
                language="en",
            )
    return choose_variation(city, load_reserved(folder), salt=0, structural=True, language="en")


def _phrase_patterns(duration_key: str, language: str) -> List[Tuple[re.Pattern, str]]:
    if language == "ko":
        replacement = {
            "weekend": "주말 2일",
            "three": "3일",
            "four": "4일",
            "five": "5일",
            "week": "1주일",
        }.get(duration_key)
        if not replacement:
            return []
        return [
            (re.compile(r"3박\s*4일"), replacement),
            (re.compile(r"3박4일"), replacement),
        ]
    if duration_key == "four":
        return [
            (re.compile(r"\bin Four Days\b"), "in 4 Days"),
            (re.compile(r"3-Night, 4-Day"), "4-Day"),
            (re.compile(r"3-night, 4-day"), "4-day"),
            (re.compile(r"\bFour Days\b"), "4 Days"),
        ]
    if duration_key == "weekend":
        return [
            (re.compile(r"\bin Four Days\b"), "for a Weekend"),
            (re.compile(r"3-Night, 4-Day"), "Weekend"),
            (re.compile(r"3-night, 4-day"), "weekend"),
            (re.compile(r"\bFour Days\b"), "a Weekend"),
            (re.compile(r"\bfour days\b"), "a weekend"),
            (re.compile(r"\bfour-day\b", re.IGNORECASE), "weekend"),
            (re.compile(r"\b4-day\b", re.IGNORECASE), "weekend"),
            (re.compile(r"\bin 4 Days\b"), "for a Weekend"),
            (re.compile(r"\ba three-night stay\b", re.IGNORECASE), "a weekend"),
            (re.compile(r"\bthree nights\b", re.IGNORECASE), "two nights"),
            (re.compile(r"\bthree-night\b", re.IGNORECASE), "two-night"),
        ]
    if duration_key == "three":
        return [
            (re.compile(r"\bin Four Days\b"), "in 3 Days"),
            (re.compile(r"3-Night, 4-Day"), "3-Day"),
            (re.compile(r"3-night, 4-day"), "3-day"),
            (re.compile(r"\bFour Days\b"), "3 Days"),
            (re.compile(r"\bfour days\b"), "three days"),
            (re.compile(r"\bfour-day\b", re.IGNORECASE), "three-day"),
            (re.compile(r"\b4-day\b", re.IGNORECASE), "3-day"),
            (re.compile(r"\bin 4 Days\b"), "in 3 Days"),
            (re.compile(r"\ba three-night stay\b", re.IGNORECASE), "a two-night stay"),
            (re.compile(r"\bthree nights\b", re.IGNORECASE), "two nights"),
            (re.compile(r"\bthree-night\b", re.IGNORECASE), "two-night"),
        ]
    if duration_key == "five":
        return [
            (re.compile(r"\bin Four Days\b"), "in 5 Days"),
            (re.compile(r"3-Night, 4-Day"), "5-Day"),
            (re.compile(r"3-night, 4-day"), "5-day"),
            (re.compile(r"\bFour Days\b"), "5 Days"),
            (re.compile(r"\bfour days\b"), "five days"),
            (re.compile(r"\bfour-day\b", re.IGNORECASE), "five-day"),
            (re.compile(r"\b4-day\b", re.IGNORECASE), "5-day"),
            (re.compile(r"\bin 4 Days\b"), "in 5 Days"),
            (re.compile(r"\ba three-night stay\b", re.IGNORECASE), "a four-night stay"),
            (re.compile(r"\bthree nights\b", re.IGNORECASE), "four nights"),
            (re.compile(r"\bthree-night\b", re.IGNORECASE), "four-night"),
        ]
    if duration_key == "week":
        return [
            (re.compile(r"\bin Four Days\b"), "in 1 Week"),
            (re.compile(r"3-Night, 4-Day"), "7-Day"),
            (re.compile(r"3-night, 4-day"), "7-day"),
            (re.compile(r"\bFour Days\b"), "1 Week"),
            (re.compile(r"\bfour days\b"), "a week"),
            (re.compile(r"\bfour-day\b", re.IGNORECASE), "week-long"),
            (re.compile(r"\b4-day\b", re.IGNORECASE), "7-day"),
            (re.compile(r"\bin 4 Days\b"), "in 1 Week"),
            (re.compile(r"\ba three-night stay\b", re.IGNORECASE), "a six-night stay"),
            (re.compile(r"\bthree nights\b", re.IGNORECASE), "six nights"),
            (re.compile(r"\bthree-night\b", re.IGNORECASE), "six-night"),
        ]
    return []


def _sub_keep_case(pattern: re.Pattern, repl: str, text: str) -> str:
    def _replacer(match):
        original = match.group(0)
        if original[:1].isupper():
            return repl[:1].upper() + repl[1:]
        return repl

    return pattern.sub(_replacer, text)


def _replace_phrases(text: str, patterns: Sequence[Tuple[re.Pattern, str]]) -> str:
    if not patterns:
        return text
    lines = text.splitlines()
    in_front = bool(lines) and lines[0].strip() == "---"
    replaced = []
    for line in lines:
        if in_front:
            replaced.append(line)
            if line.strip() == "---" and len(replaced) > 1:
                in_front = False
            continue
        if line.strip().startswith("![") or "http://" in line or "https://" in line:
            replaced.append(line)
            continue
        updated = line
        for pattern, repl in patterns:
            updated = _sub_keep_case(pattern, repl, updated)
        replaced.append(updated)
    return "\n".join(replaced)


class _Day(object):
    def __init__(self, title: str, body: str):
        self.title = title.strip() or "Around the city"
        self.body = body.strip()


def _is_itinerary_heading(line: str, language: str) -> bool:
    if not line.startswith("## ") or line.startswith("### "):
        return False
    if language == "ko":
        return ("3박" in line) or ("일정" in line) or ("코스" in line and "일" in line)
    return any(token in line for token in ("Itinerary", "3-Night", "4-Day", "7-Day", "Weekend in", "Days in"))


def _parse_days(lines: Sequence[str]) -> List[_Day]:
    indexes = [index for index, line in enumerate(lines) if _DAY_LINE.match(line.strip())]
    days = []
    for position, start in enumerate(indexes):
        end = indexes[position + 1] if position + 1 < len(indexes) else len(lines)
        match = _DAY_LINE.match(lines[start].strip())
        title = match.group(3) if match else ""
        body = "\n".join(lines[start + 1:end]).strip()
        days.append(_Day(title, body))
    return days


def _split_itinerary(markdown: str, language: str):
    lines = markdown.splitlines()
    h2_at = None
    first_day = None
    for index, line in enumerate(lines):
        if first_day is None and _DAY_LINE.match(line.strip()):
            first_day = index
        if h2_at is None and _is_itinerary_heading(line, language):
            h2_at = index
    if first_day is None:
        return None
    if h2_at is None or h2_at > first_day:
        h2_at = first_day
        day_start = first_day
        preamble_end = first_day
    else:
        day_start = first_day
        preamble_end = h2_at
    next_h2 = None
    for index in range(day_start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            next_h2 = index
            break
    end = next_h2 if next_h2 is not None else len(lines)
    preamble = lines[:preamble_end]
    between = lines[h2_at + 1:day_start] if h2_at < day_start else []
    days = _parse_days(lines[day_start:end])
    rest = lines[end:]
    if len(days) < 2:
        return None
    return preamble, between, days, rest


def _split_departure(day: _Day, language: str) -> Tuple[_Day, Optional[_Day]]:
    title = "출국" if language == "ko" else "Departure"
    slower = "여유 있는 마무리" if language == "ko" else "A slower close"
    bullet_keep = []
    bullet_move = []
    saw_bullet = False
    for line in day.body.splitlines():
        if re.match(r"^(\*|-)\s+", line) and _DEPARTURE.search(line):
            saw_bullet = True
            bullet_move.append(line)
        else:
            bullet_keep.append(line)
    if saw_bullet and any(line.strip() for line in bullet_keep):
        return _Day(day.title, "\n".join(bullet_keep)), _Day(title, "\n".join(bullet_move))
    if "![" in day.body or "](http" in day.body:
        rows = [line for line in day.body.splitlines() if line.strip()]
        if len(rows) >= 2:
            return _Day(day.title, "\n".join(rows[:-1])), _Day(title, rows[-1])
        return day, None
    sentences = re.split(r"(?<=[.!?])\s+", day.body.strip())
    if len(sentences) >= 2:
        cut = len(sentences) - 1
        for index in range(len(sentences) - 1, 0, -1):
            if _DEPARTURE.search(sentences[index]):
                cut = index
                break
        extra_title = title if _DEPARTURE.search(" ".join(sentences[cut:])) else slower
        return _Day(day.title, " ".join(sentences[:cut])), _Day(extra_title, " ".join(sentences[cut:]))
    rows = [line for line in day.body.splitlines() if line.strip()]
    if len(rows) >= 2:
        return _Day(day.title, "\n".join(rows[:-1])), _Day(title, rows[-1])
    return day, None


def _regroup(days: List[_Day], duration_key: str, language: str) -> List[List[_Day]]:
    if duration_key == "weekend":
        if len(days) <= 2:
            return [[day] for day in days]
        midpoint = max(1, len(days) // 2)
        return [days[:midpoint], days[midpoint:]]
    if duration_key == "three":
        if len(days) <= 3:
            return [[day] for day in days]
        return [[days[0]], [days[1]], days[2:]]
    if duration_key == "five":
        if len(days) >= 5:
            return [[day] for day in days[:5]]
        if len(days) == 4:
            kept, extra = _split_departure(days[-1], language)
            if extra and extra.body.strip():
                return [[days[0]], [days[1]], [days[2]], [kept], [extra]]
        return [[day] for day in days]
    if duration_key == "week":
        if len(days) >= 4:
            return [[day] for day in days[:4]]
        return [[day] for day in days]
    return [[day] for day in days]


def _group_labels(duration_key: str, language: str, count: int) -> List[str]:
    if duration_key == "weekend":
        labels = ["1일 차 (토요일)", "2일 차 (일요일)"] if language == "ko" else ["Day 1 (Saturday)", "Day 2 (Sunday)"]
        return labels[:count]
    if duration_key == "week":
        labels = (
            ["1–2일 차", "3–4일 차", "5–6일 차", "7일 차"]
            if language == "ko"
            else ["Days 1–2", "Days 3–4", "Days 5–6", "Day 7"]
        )
        return labels[:count]
    if language == "ko":
        return ["{0}일 차".format(index) for index in range(1, count + 1)]
    return ["Day {0}".format(index) for index in range(1, count + 1)]


def _render_days(groups: Sequence[Sequence[_Day]], variation: Variation) -> List[str]:
    labels = _group_labels(variation.duration_key, variation.language, len(groups))
    notes = _WEEK_NOTES_KO if variation.language == "ko" else _WEEK_NOTES
    rendered = []
    for index, group in enumerate(groups):
        first = group[0]
        rendered.append("### {0}: {1}".format(labels[index], first.title))
        rendered.append("")
        if variation.duration_key == "week" and index < len(notes):
            rendered.append(notes[index])
            rendered.append("")
        if first.body:
            rendered.append(first.body)
            rendered.append("")
        for extra in group[1:]:
            rendered.append("**{0}**".format(extra.title))
            rendered.append("")
            if extra.body:
                rendered.append(extra.body)
                rendered.append("")
    return rendered


def _replace_title_heading(text: str, title: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            lines[index] = "# {0}".format(title)
            return "\n".join(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            if index > 0 and lines[index - 1].strip() == "---":
                continue
            lines.insert(index, "# {0}".format(title))
            lines.insert(index + 1, "")
            return "\n".join(lines)
    return "# {0}\n\n{1}".format(title, text.lstrip("\n"))


def _upsert_frontmatter(text: str, fields: Dict[str, str]) -> str:
    match = _FRONTMATTER.match(text)
    rows = ["{0}: {1}".format(key, _yaml_quote(value)) for key, value in fields.items()]
    if not match:
        block = "---\n{0}\n---\n\n".format("\n".join(rows))
        return block + text.lstrip("\n")
    existing = match.group(1).splitlines()
    seen = set()
    merged = []
    for line in existing:
        key = line.split(":", 1)[0].strip()
        if key in fields:
            merged.append("{0}: {1}".format(key, _yaml_quote(fields[key])))
            seen.add(key)
        else:
            merged.append(line)
    for key, value in fields.items():
        if key not in seen:
            merged.append("{0}: {1}".format(key, _yaml_quote(value)))
    rest = text[match.end():]
    if not rest.startswith("\n"):
        rest = "\n" + rest
    return "---\n{0}\n---\n{1}".format("\n".join(merged), rest)


def _strip_hashtag_lines(text: str) -> str:
    kept = []
    for line in text.splitlines():
        if _HASHTAG_LINE.match(line.strip()):
            continue
        kept.append(line)
    return "\n".join(kept).rstrip() + "\n"


def _rebuild_itinerary(markdown: str, variation: Variation) -> str:
    parts = _split_itinerary(markdown, variation.language)
    if parts is None or variation.duration_key == "free":
        return markdown
    preamble, between, days, rest = parts
    groups = _regroup(days, variation.duration_key, variation.language)
    heading = "## {0}".format(itinerary_heading(variation))
    blocks = list(preamble)
    if blocks and blocks[-1].strip():
        blocks.append("")
    blocks.append(heading)
    blocks.append("")
    for line in between:
        if line.strip():
            blocks.append(line)
    if any(line.strip() for line in between):
        blocks.append("")
    blocks.extend(_render_days(groups, variation))
    if rest:
        if blocks and blocks[-1].strip():
            blocks.append("")
        blocks.extend(rest)
    return "\n".join(blocks).rstrip() + "\n"


def apply_variation(markdown: str, variation: Variation) -> str:
    """제목, 일정 소제목, 해시태그를 variation 에 맞게 덮어쓴다. 이미 처리된 파일은 유지한다."""
    if _frontmatter_value(markdown or "", "duration_key"):
        return markdown if markdown.endswith("\n") else markdown + "\n"
    updated = _replace_phrases(markdown or "", _phrase_patterns(variation.duration_key, variation.language))
    if has_day_sections(updated) and variation.duration_key != "free":
        updated = _rebuild_itinerary(updated, variation)
    updated = _replace_title_heading(updated, variation.title)
    updated = _strip_hashtag_lines(updated).rstrip() + "\n\n" + " ".join(variation.hashtags) + "\n"
    fields = {
        "title": variation.title,
        "city": variation.city,
        "duration": variation.label or _SPAN_NOUN.get(duration_key_for(variation.city), ""),
        "duration_key": variation.duration_key,
        "title_form": variation.template_id,
        "hashtags": " ".join(variation.hashtags),
    }
    if not fields["duration"]:
        del fields["duration"]
    return _upsert_frontmatter(updated, fields)


def vary_markdown(
    markdown: str,
    city: str,
    reserved: Reserved,
    salt: int = 0,
    language: str = "",
) -> Tuple[str, Variation]:
    existing_key = _frontmatter_value(markdown, "duration_key")
    existing_form = _frontmatter_value(markdown, "title_form")
    existing_title = _frontmatter_value(markdown, "title")
    existing_tags = _hashtag_tokens(markdown)
    if existing_key and existing_form and existing_title and existing_tags:
        variation = Variation(
            city=display_city(city, "en"),
            duration_key=existing_key,
            template_id=existing_form,
            title=existing_title,
            hashtags=existing_tags,
            language=language or document_language(markdown),
        )
        reserved.remember(variation)
        return markdown if markdown.endswith("\n") else markdown + "\n", variation
    lang = language or document_language(markdown)
    structural = has_day_sections(markdown)
    detected = None if structural else detect_day_count(markdown)
    variation = choose_variation(
        city,
        reserved,
        salt=salt,
        structural=structural,
        detected_days=detected,
        language=lang,
    )
    updated = apply_variation(markdown, variation)
    reserved.remember(variation)
    return updated, variation


def audit_varied_guide(markdown: str) -> List[str]:
    """발행 파일이 고정 4일 제목과 단일 해시태그에서 벗어났는지 확인한다."""
    issues = []
    if re.search(r"\bin Four Days\b", markdown or ""):
        issues.append("stock title")
    if "A 3-Night, 4-Day" in (markdown or "") or "3-night, 4-day" in (markdown or ""):
        issues.append("stock itinerary")
    tags = _hashtag_tokens(markdown)
    if not 2 <= len(tags) <= 4:
        issues.append("hashtag count")
    if tags == ["#LocalFood"]:
        issues.append("only local food")
    key = _frontmatter_value(markdown, "duration_key")
    if key in _SECTION_COUNT and has_day_sections(markdown):
        count = len(_DAY_LINE.findall(markdown))
        if count != _SECTION_COUNT[key]:
            issues.append("day count {0}!={1}".format(count, _SECTION_COUNT[key]))
        if key == "week" and "7 Days" not in markdown and "1주일" not in markdown and "7일" not in markdown:
            issues.append("week label")
    return issues


def finish_writer_article(markdown: str, destination: str, language: str = "en") -> str:
    """모델이 4일 고정으로 써도 도시 일정과 해시태그 줄을 맞춘다."""
    lang = "ko" if (language or "").strip().lower() in {"ko", "kr", "korean"} else "en"
    if _frontmatter_value(markdown or "", "duration_key"):
        return markdown if (markdown or "").endswith("\n") else (markdown or "") + "\n"
    base = variation_for_new_article(destination)
    if lang == "ko":
        key = base.duration_key if base.duration_key != "free" else duration_key_for(destination)
        spec = next(item for item in _TEMPLATES if item["id"] == "ko_course")
        variation = Variation(
            city=display_city(destination, "en"),
            duration_key=key,
            template_id=spec["id"],
            title=_render_title(spec, destination, key, "ko"),
            hashtags=base.hashtags,
            language="ko",
        )
    else:
        variation = base
    if has_day_sections(markdown or "") and variation.duration_key != "free":
        return apply_variation(markdown, variation)
    return _strip_hashtag_lines(markdown or "").rstrip() + "\n\n" + " ".join(variation.hashtags) + "\n"
