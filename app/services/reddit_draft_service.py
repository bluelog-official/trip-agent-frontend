"""해외 Reddit 초안을 가이드 스팟으로 조립한다. LLM 의존성 없음."""

import re
import unicodedata
from typing import Dict, List, Sequence, Tuple

_HANGUL = re.compile(r"[\uac00-\ud7a3]")
_HEADING = re.compile(r"^#{2,4}\s+(.+?)\s*$", re.MULTILINE)
_DAY_COUNT = re.compile(r"\b([2-7])\s*[- ]days?\b", re.IGNORECASE)
_NIGHT_COUNT = re.compile(r"([2-6])박")
_SECTION_LABEL = re.compile(
    r"\b(budget|cost|itinerary|breakdown|overview|introduction|summary|"
    r"tips?|guide|transport|transit|faq|conclusion|where to|top sights|"
    r"insider|suggested)\b",
    re.IGNORECASE,
)
_FOOD_HINT = re.compile(
    r"\b(market|ramen|food|restaurant|cafe|coffee|izakaya|noodle|pizza|bakery|street food)\b",
    re.IGNORECASE,
)
_GENERIC_EXACT = {
    "walk",
    "food",
    "sights",
    "tips",
    "intro",
    "overview",
    "itinerary",
    "budget",
    "transport",
    "transit",
}

_JAPAN_CITIES = {
    "tokyo",
    "osaka",
    "kyoto",
    "hiroshima",
    "nara",
    "fukuoka",
    "sapporo",
    "yokohama",
    "nagoya",
    "kobe",
    "okinawa",
    "kanazawa",
    "hakone",
    "kamakura",
    "nikko",
}
_EUROPE_CITIES = {
    "paris",
    "london",
    "rome",
    "barcelona",
    "prague",
    "amsterdam",
    "berlin",
    "vienna",
    "budapest",
    "lisbon",
    "madrid",
    "florence",
    "venice",
    "munich",
    "dublin",
    "athens",
    "copenhagen",
    "stockholm",
    "zurich",
    "brussels",
    "edinburgh",
    "milan",
    "porto",
    "krakow",
    "dubrovnik",
    "seville",
    "nice",
    "interlaken",
}
_FALLBACK_SIGHTS = {
    "osaka": ["Dotonbori", "Universal Studios Japan"],
    "kyoto": ["Fushimi Inari", "Arashiyama"],
    "tokyo": ["Shibuya Crossing", "Senso-ji"],
    "prague": ["Old Town Square", "Charles Bridge"],
    "taipei": ["Taipei 101", "Shilin Night Market"],
    "paris": ["the Louvre", "Eiffel Tower"],
    "rome": ["the Colosseum", "Trevi Fountain"],
    "london": ["the British Museum", "Borough Market"],
    "barcelona": ["Sagrada Familia", "Gothic Quarter"],
    "new york": ["Central Park", "the Met"],
    "seoul": ["Gyeongbokgung", "Bukchon"],
    "singapore": ["Gardens by the Bay", "Maxwell Food Centre"],
}
_BOILERPLATE = (
    "첫 방문 때 실제로 도움이",
    "actually helped on a first visit",
    "처음 가는 기준으로 관광지",
)
_STYLES = ("experience", "question", "tips")


def destination_from_guide_id(guide_id: str) -> str:
    """`osaka_guide.md` 같은 파일명에서 도시 표시 이름을 복원한다."""
    from app.services.magazine_matrix import parse_matrix_guide_id

    parsed = parse_matrix_guide_id(guide_id)
    if parsed is not None:
        return parsed.city
    stem = (guide_id or "").strip()
    if stem.endswith("_guide.md"):
        stem = stem[: -len("_guide.md")]
    elif stem.endswith(".md"):
        stem = stem[:-3]
    label = stem.replace("_", " ").strip()
    if not label:
        return ""
    return label.title()


def reddit_draft_needs_refresh(title: str, body: str) -> bool:
    """한글 정형문이나 비어 있는 Reddit 초안은 영문으로 다시 쓴다."""
    text = "{0}\n{1}".format(title or "", body or "")
    if not str(title or "").strip() or not str(body or "").strip():
        return True
    if _HANGUL.search(text):
        return True
    lowered = text.casefold()
    return any(phrase.casefold() in lowered for phrase in _BOILERPLATE)


def recommend_subreddit(destination: str) -> str:
    """일본은 r/JapanTravel·r/travel, 유럽은 r/travel·r/solotravel·r/Europe."""
    region = _region(_city_key(destination))
    if region == "japan":
        options = ("JapanTravel", "travel")
    elif region == "europe":
        options = ("travel", "solotravel", "Europe")
    else:
        options = ("travel", "solotravel")
    return options[_fold(_city_key(destination)) % len(options)]


def select_post_style(destination: str) -> str:
    """도시마다 experience / question / tips 중 하나를 고정한다."""
    return _STYLES[_fold("{0}:style".format(_city_key(destination))) % len(_STYLES)]


def build_reddit_draft(
    destination: str,
    attractions: Sequence[str] = (),
    food_spots: Sequence[str] = (),
    local_tip: str = "",
    currency: str = "",
    article_markdown: str = "",
) -> Dict[str, str]:
    """가이드에 나온 스팟을 넣어 100% 영문 Reddit 초안을 만든다."""
    place = _display_place(destination)
    key = _city_key(place)
    sights, foods = _collect_spots(place, key, attractions, food_spots, article_markdown)
    style = select_post_style(place)
    days = _day_count(article_markdown)
    subreddit = recommend_subreddit(place)
    tip = _english_sentence(local_tip)
    cost = _cost_sentence(currency)
    title, body = _render(style, place, days, sights, foods, tip, cost, _fold(key) % 2)
    tags = _tag_line(place, sights, foods, _region(key), subreddit)
    draft_body = "{0}\n\n{1}".format(body.strip(), tags)
    return {
        "subreddit": subreddit,
        "title": title,
        "body": draft_body,
        "style": style,
    }


def _city_key(destination: str) -> str:
    text = " ".join((destination or "").strip().casefold().split())
    if "," in text:
        text = text.split(",", 1)[0].strip()
    return text


def _display_place(destination: str) -> str:
    text = " ".join((destination or "").strip().split())
    if not text:
        return "this city"
    if text.islower():
        return text.title()
    return text


def _region(key: str) -> str:
    if key in _JAPAN_CITIES:
        return "japan"
    if key in _EUROPE_CITIES:
        return "europe"
    return "other"


def _fold(seed: str) -> int:
    value = 2166136261
    for char in seed:
        value ^= ord(char)
        value = (value * 16777619) & 0xFFFFFFFF
    return value


def _is_latin_letter(char: str) -> bool:
    if not char.isalpha():
        return False
    return unicodedata.name(char, "").startswith("LATIN")


def _is_latin_copy(text: str) -> bool:
    if not text or _HANGUL.search(text):
        return False
    letters = [char for char in text if char.isalpha()]
    if len(letters) < 2:
        return False
    return all(_is_latin_letter(char) for char in letters)


def _clean_spot(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "").replace("\n", " ")).strip()
    text = re.sub(r"^[#*_`\d\.\)\-\s]+", "", text).strip(" *_`")
    if len(text) < 3 or len(text) > 60:
        return ""
    if text.casefold() in _GENERIC_EXACT or _SECTION_LABEL.search(text):
        return ""
    if not _is_latin_copy(text):
        return ""
    return text


def _dedupe(items: Sequence[str]) -> List[str]:
    kept: List[str] = []
    for item in items:
        key = item.casefold()
        replaced = False
        next_kept: List[str] = []
        for previous in kept:
            prev_key = previous.casefold()
            if key == prev_key or key in prev_key:
                next_kept.append(previous)
                replaced = True
                continue
            if prev_key in key:
                next_kept.append(item)
                replaced = True
                continue
            next_kept.append(previous)
        kept = next_kept
        if not replaced:
            kept.append(item)
    unique: List[str] = []
    seen = set()
    for item in kept:
        marker = item.casefold()
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique


def _collect_spots(
    place: str,
    key: str,
    attractions: Sequence[str],
    food_spots: Sequence[str],
    article_markdown: str,
) -> Tuple[List[str], List[str]]:
    sights: List[str] = []
    foods: List[str] = []
    place_key = place.casefold()
    for raw in attractions:
        spot = _clean_spot(str(raw))
        if not spot or spot.casefold() == place_key:
            continue
        if _FOOD_HINT.search(spot):
            foods.append(spot)
        else:
            sights.append(spot)
    for raw in food_spots:
        spot = _clean_spot(str(raw))
        if spot and spot.casefold() != place_key:
            foods.append(spot)
    for match in _HEADING.finditer(article_markdown or ""):
        spot = _clean_spot(match.group(1))
        if not spot or spot.casefold() == place_key:
            continue
        if _FOOD_HINT.search(spot):
            foods.append(spot)
        else:
            sights.append(spot)
    sights = _dedupe(sights)
    foods = _dedupe(foods)
    if not sights and foods:
        sights = foods[:2]
        foods = foods[2:]
    if not sights:
        sights = list(_FALLBACK_SIGHTS.get(key, []))
    return sights[:3], foods[:2]


def _day_count(article_markdown: str) -> int:
    match = _DAY_COUNT.search(article_markdown or "")
    if match:
        return int(match.group(1))
    nights = _NIGHT_COUNT.search(article_markdown or "")
    if nights:
        return min(7, int(nights.group(1)) + 1)
    return 3


def _english_sentence(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned or not _is_latin_copy(cleaned):
        return ""
    if cleaned[-1] not in ".!?":
        cleaned = "{0}.".format(cleaned)
    return cleaned


def _cost_sentence(currency: str) -> str:
    token = (currency or "").strip()
    letters = [char for char in token if char.isalpha()]
    latin = all(_is_latin_letter(char) for char in letters)
    if not token or _HANGUL.search(token) or len(token) > 8 or not latin:
        return "Meal prices and tickets are listed on separate lines, so the daily total is easy to scan."
    return "Meal prices and tickets are listed separately in {0}.".format(token)


def _unique_exact(items: Sequence[str]) -> List[str]:
    seen = set()
    unique: List[str] = []
    for item in items:
        marker = item.casefold()
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique


def _join_and(items: Sequence[str]) -> str:
    names = [item for item in items if item]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return "{0} and {1}".format(names[0], names[1])
    return "{0}, and {1}".format(", ".join(names[:-1]), names[-1])


def _tag_line(
    place: str,
    sights: Sequence[str],
    foods: Sequence[str],
    region: str,
    subreddit: str,
) -> str:
    raw = [place]
    raw.extend(sights[:3])
    raw.extend(foods[:1])
    if region == "japan":
        raw.append("Japan")
    elif region == "europe":
        raw.append("Europe")
    raw.append("r/{0}".format(subreddit))
    tags = _unique_exact([item for item in raw if item])
    return "Tags: {0}".format(", ".join(tags))


def _render(
    style: str,
    place: str,
    days: int,
    sights: Sequence[str],
    foods: Sequence[str],
    tip: str,
    cost: str,
    variant: int,
) -> Tuple[str, str]:
    if style == "question":
        return _question_post(place, days, sights, foods, tip, cost, variant)
    if style == "tips":
        return _tips_post(place, sights, foods, tip, cost, variant)
    return _experience_post(place, days, sights, foods, tip, cost, variant)


def _experience_post(
    place: str,
    days: int,
    sights: Sequence[str],
    foods: Sequence[str],
    tip: str,
    cost: str,
    variant: int,
) -> Tuple[str, str]:
    spot_label = _join_and(sights[:2])
    if spot_label:
        title = "My {0}-day realistic budget breakdown for {1} ({2})".format(days, place, spot_label)
    else:
        title = "My {0}-day realistic budget breakdown for {1}".format(days, place)
    if variant:
        opening = "Here is the unpolished {0}-day spend for {1}, including the stops I would keep.".format(days, place)
    else:
        opening = "I kept a plain tally for {0} days in {1}: transit, tickets, and whatever I actually ate.".format(days, place)
    lines = [opening, _route_sentence(sights, foods, "experience")]
    if tip:
        lines.append(tip)
    lines.append(cost)
    if variant:
        lines.append("I left out the souvenir shops. The useful part was knowing which stops share a train.")
    else:
        lines.append("I left the padding out. The useful part was not crossing the city twice in one afternoon.")
    return title, "\n\n".join(lines)


def _question_post(
    place: str,
    days: int,
    sights: Sequence[str],
    foods: Sequence[str],
    tip: str,
    cost: str,
    variant: int,
) -> Tuple[str, str]:
    spot_label = _join_and(sights[:2])
    if spot_label:
        title = "Is {0} days enough for {1}? Here is how I set up my route around {2}".format(
            days, place, spot_label
        )
    else:
        title = "Is {0} days enough for {1}? Here is how I set up my route".format(days, place)
    if variant:
        opening = "I almost added an extra day in {0}. A {1}-day route was enough once the walking order was fixed.".format(
            place, days
        )
    else:
        opening = "Is {0} days enough for {1}? It was, after I stopped treating every pin as mandatory.".format(
            days, place
        )
    lines = [opening, _route_sentence(sights, foods, "question")]
    if tip:
        lines.append(tip)
    lines.append(cost)
    lines.append("If you anchored the trip on a different stop, I would like to hear what you cut.")
    return title, "\n\n".join(lines)


def _tips_post(
    place: str,
    sights: Sequence[str],
    foods: Sequence[str],
    tip: str,
    cost: str,
    variant: int,
) -> Tuple[str, str]:
    title = "Quick tips & transit guide for first-timers in {0}".format(place)
    if variant:
        intro = "Notes I would text a friend before a first trip to {0}:".format(place)
    else:
        intro = "A few things that kept a first pass through {0} from turning into a transfer marathon:".format(place)
    bullets: List[str] = []
    if sights:
        bullets.append("Give {0} the early slot, before the groups fill the street.".format(sights[0]))
    if len(sights) > 1:
        bullets.append("Pair {0} with that morning so the afternoon is one neighborhood, not two rides.".format(sights[1]))
    elif foods:
        bullets.append("Eat near {0} instead of booking a restaurant across town.".format(foods[0]))
    if foods and len(sights) > 1:
        bullets.append("For food, stay around {0}.".format(_join_and(foods)))
    if tip:
        bullets.append(tip)
    else:
        bullets.append("Load a transit card on arrival and tap through buses and trains instead of buying single tickets.")
    if len(sights) > 2:
        bullets.append("If you have energy left, {0} fits as a shorter third stop.".format(sights[2]))
    lines = [intro, "\n".join("- {0}".format(item) for item in bullets), cost]
    return title, "\n\n".join(lines)


def _route_sentence(sights: Sequence[str], foods: Sequence[str], style: str) -> str:
    sight_label = _join_and(sights[:3])
    food_label = _join_and(foods[:2])
    if style == "question":
        if sight_label and food_label:
            return "I ordered the walk as {0}, then ate around {1} without leaving that side of town.".format(
                sight_label, food_label
            )
        if sight_label:
            return "I ordered the walk as {0}, and skipped anything that needed a second cross-town ride.".format(
                sight_label
            )
        if food_label:
            return "I picked meals around {0} and kept the sights inside that same walk.".format(food_label)
        return "I kept each day inside one neighborhood and only transferred when the day changed."
    if sight_label and food_label:
        return "Most of the time went to {0}, with meals near {1} so dinner was not a separate ride.".format(
            sight_label, food_label
        )
    if sight_label:
        return "Most of the time went to {0}, in an order that stays on one side of the city.".format(sight_label)
    if food_label:
        return "I planned meals around {0} and kept the sightseeing on that same walk.".format(food_label)
    return "I kept each day inside one neighborhood and only transferred when the day changed."
