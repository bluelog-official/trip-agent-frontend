"""도시별 발행 가이드 건수, 좌표, 기간 순위. LLM 의존성 없음."""

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.content_variation import display_city, normalize_city, slugify_city
from app.services.guide_service import list_guide_records, read_guide_markdown

TOP_CITY_LIMIT = 5
PERIOD_DAYS = {
    "1w": 7,
    "2w": 14,
    "1m": 30,
    "1y": 365,
    "all": None,
}
_PERIOD_ALIASES = {
    "1 week": "1w",
    "1week": "1w",
    "week": "1w",
    "2 weeks": "2w",
    "2weeks": "2w",
    "1 month": "1m",
    "1month": "1m",
    "month": "1m",
    "1 year": "1y",
    "1year": "1y",
    "year": "1y",
    "all time": "all",
    "alltime": "all",
}

# 카탈로그에 올라온 도시만 지구본에 올린다. 좌표가 없는 도시는 핀을 만들지 않는다.
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "amsterdam": (52.3676, 4.9041),
    "bali": (-8.4095, 115.1889),
    "bangkok": (13.7563, 100.5018),
    "barcelona": (41.3874, 2.1686),
    "beijing": (39.9042, 116.4074),
    "berlin": (52.52, 13.405),
    "buenos aires": (-34.6037, -58.3816),
    "busan": (35.1796, 129.0756),
    "chicago": (41.8781, -87.6298),
    "danang": (16.0544, 108.2022),
    "florence": (43.7696, 11.2558),
    "hanoi": (21.0278, 105.8342),
    "hong kong": (22.3193, 114.1694),
    "jakarta": (-6.2088, 106.8456),
    "jeju": (33.4996, 126.5312),
    "kyoto": (35.0116, 135.7681),
    "lisbon": (38.7223, -9.1393),
    "london": (51.5074, -0.1278),
    "los angeles": (34.0522, -118.2437),
    "madrid": (40.4168, -3.7038),
    "mexico": (19.4326, -99.1332),
    "mexico city": (19.4326, -99.1332),
    "miami": (25.7617, -80.1918),
    "milan": (45.4642, 9.19),
    "new york": (40.7128, -74.006),
    "osaka": (34.6937, 135.5023),
    "paris": (48.8566, 2.3522),
    "prague": (50.0755, 14.4378),
    "rio": (-22.9068, -43.1729),
    "rome": (41.9028, 12.4964),
    "san francisco": (37.7749, -122.4194),
    "sao paulo": (-23.5558, -46.6396),
    "seoul": (37.5665, 126.978),
    "shanghai": (31.2304, 121.4737),
    "singapore": (1.3521, 103.8198),
    "sydney": (-33.8688, 151.2093),
    "taipei": (25.033, 121.5654),
    "tokyo": (35.6762, 139.6503),
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "vienna": (48.2082, 16.3738),
}

_KO_CITY_NAMES = {
    "amsterdam": "암스테르담",
    "bali": "발리",
    "bangkok": "방콕",
    "barcelona": "바르셀로나",
    "beijing": "베이징",
    "berlin": "베를린",
    "buenos aires": "부에노스아이레스",
    "busan": "부산",
    "chicago": "시카고",
    "danang": "다낭",
    "florence": "피렌체",
    "hanoi": "하노이",
    "hong kong": "홍콩",
    "jakarta": "자카르타",
    "jeju": "제주",
    "kyoto": "교토",
    "lisbon": "리스본",
    "london": "런던",
    "los angeles": "로스앤젤레스",
    "madrid": "마드리드",
    "mexico": "멕시코시티",
    "mexico city": "멕시코시티",
    "miami": "마이애미",
    "milan": "밀라노",
    "new york": "뉴욕",
    "osaka": "오사카",
    "paris": "파리",
    "prague": "프라하",
    "rio": "리우데자네이루",
    "rome": "로마",
    "san francisco": "샌프란시스코",
    "sao paulo": "상파울루",
    "seoul": "서울",
    "shanghai": "상하이",
    "singapore": "싱가포르",
    "sydney": "시드니",
    "taipei": "타이베이",
    "tokyo": "도쿄",
    "toronto": "토론토",
    "vancouver": "밴쿠버",
    "vienna": "빈",
}

_FRONTMATTER = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---", re.M)
_HASH_LINE = re.compile(r"^(?:#[A-Za-z][A-Za-z0-9]*)(?:\s+#[A-Za-z][A-Za-z0-9]*)+\s*$")


def _seoul_timezone():
    try:
        return ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        return timezone.utc


_SEOUL = _seoul_timezone()


def normalize_period(value: str) -> str:
    """필터 키. 알 수 없는 값이면 ValueError."""
    key = _PERIOD_ALIASES.get(str(value or "").strip().lower(), str(value or "").strip().lower())
    if key not in PERIOD_DAYS:
        raise ValueError(key or "period")
    return key


def _as_seoul(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=_SEOUL)
    return moment.astimezone(_SEOUL)


def _now(moment: Optional[datetime] = None) -> datetime:
    if moment is None:
        return datetime.now(_SEOUL)
    return _as_seoul(moment)


def _parse_time(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=_SEOUL)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _as_seoul(parsed)


def _frontmatter_block(markdown: str) -> str:
    match = _FRONTMATTER.search(markdown or "")
    return match.group(1) if match else ""


def _frontmatter_value(markdown: str, key: str) -> str:
    match = re.compile(r'^{0}:\s*"?([^"\n]+)"?\s*$'.format(re.escape(key)), re.M).search(
        _frontmatter_block(markdown)
    )
    return match.group(1).strip() if match else ""


def extract_hashtags(markdown: str) -> List[str]:
    """프론트매터 hashtags 또는 해시태그로만 된 줄을 읽는다."""
    source = _frontmatter_value(markdown, "hashtags")
    if not source:
        for line in reversed(str(markdown or "").splitlines()):
            stripped = line.strip()
            if _HASH_LINE.match(stripped):
                source = stripped
                break
    labels: List[str] = []
    for token in source.replace(",", " ").split():
        label = token.lstrip("#").strip()
        if label and label not in labels:
            labels.append(label)
    return labels


def _tags_for_record(record: Dict[str, Any]) -> List[str]:
    raw = record.get("hashtags")
    if isinstance(raw, list):
        labels: List[str] = []
        for item in raw:
            label = str(item or "").lstrip("#").strip()
            if label and label not in labels:
                labels.append(label)
        return labels
    if isinstance(raw, str) and raw.strip():
        text = raw if "#" in raw or "hashtags:" in raw else 'hashtags: "{0}"'.format(raw)
        return extract_hashtags(text)
    filename = str(record.get("filename") or "")
    if not filename:
        return []
    return extract_hashtags(read_guide_markdown(filename))


def _publication_moment(record: Dict[str, Any]) -> Optional[datetime]:
    """작성일은 프론트매터 date, 없으면 파일 시각. 테스트는 published_at을 넘긴다."""
    explicit = record.get("published_at") or record.get("updated_at")
    if explicit:
        return _parse_time(explicit)
    filename = str(record.get("filename") or "")
    if filename:
        dated = _parse_time(_frontmatter_value(read_guide_markdown(filename), "date"))
        if dated is not None:
            return dated
    return _parse_time(record.get("created_at"))


def _score(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _ko_name(key: str) -> str:
    if key in _KO_CITY_NAMES:
        return _KO_CITY_NAMES[key]
    return display_city(key, "ko")


def _in_window(moment: datetime, start: datetime, end: datetime) -> bool:
    return start < moment <= end


def _window_bounds(now: datetime, days: int) -> Tuple[datetime, datetime, datetime]:
    current_start = now - timedelta(days=days)
    previous_start = now - timedelta(days=days * 2)
    return previous_start, current_start, now


def _trend(current: int, previous: int) -> Tuple[Optional[int], bool]:
    if previous <= 0:
        return (None, current > 0)
    percent = int(round((current - previous) * 100 / previous))
    return (percent, False)


def _keywords(tag_lists: Sequence[Sequence[str]]) -> List[str]:
    counts: Counter = Counter()
    for tags in tag_lists:
        for tag in tags:
            if tag:
                counts[tag] += 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    return [label for label, _count in ranked[:2]]


def build_globe_map(
    period: str = "all",
    records: Optional[Sequence[Dict[str, Any]]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """기간 안의 발행 가이드를 도시별로 모아 좌표, 순위, 키워드, 추세를 붙인다.

    발행 건수는 그 기간에 작성된 가이드 수다. 순위는 건수, 품질 점수 평균, 도시명 순이다.
    추세는 같은 길이의 직전 기간과 비교한 증감률이다. 전체 기간은 최근 30일을 직전 30일과 비교한다.
    """
    key = normalize_period(period)
    days = PERIOD_DAYS[key]
    trend_days = 30 if days is None else days
    current_time = _now(now)
    previous_start, trend_start, trend_end = _window_bounds(current_time, trend_days)
    source = list(records) if records is not None else list_guide_records()

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in source:
        city_key = normalize_city(str(record.get("city") or ""))
        if city_key not in CITY_COORDINATES:
            continue
        grouped.setdefault(city_key, []).append(
            {
                "moment": _publication_moment(record),
                "score": _score(record.get("qa_score")),
                "tags": _tags_for_record(record),
            }
        )

    drafts: List[Dict[str, Any]] = []
    for city_key, items in grouped.items():
        if days is None:
            selected = items
        else:
            selected = [
                item
                for item in items
                if item["moment"] is not None and _in_window(item["moment"], trend_start, trend_end)
            ]
        if not selected:
            continue
        moments = [item["moment"] for item in items if item["moment"] is not None]
        selected_moments = [item["moment"] for item in selected if item["moment"] is not None]
        latest = max(selected_moments) if selected_moments else None
        scores = [item["score"] for item in selected]
        mean_score = int(round(sum(scores) / len(scores))) if scores else 0
        previous_count = sum(
            1 for moment in moments if _in_window(moment, previous_start, trend_start)
        )
        published_count = len(selected)
        if days is None:
            trend_current = sum(1 for moment in moments if _in_window(moment, trend_start, trend_end))
        else:
            trend_current = published_count
        trending_percent, trending_new = _trend(trend_current, previous_count)
        lat, lng = CITY_COORDINATES[city_key]
        drafts.append(
            {
                "city_key": city_key,
                "city": display_city(city_key, "en"),
                "city_ko": _ko_name(city_key),
                "slug": slugify_city(city_key),
                "lat": lat,
                "lng": lng,
                "published_count": published_count,
                "quality_score": mean_score,
                "score_sum": sum(scores),
                "trending_percent": trending_percent,
                "trending_new": trending_new,
                "keywords": _keywords([item["tags"] for item in selected]),
                "latest_at": latest.date().isoformat() if latest else "",
                "latest_ts": latest.timestamp() if latest else 0,
            }
        )

    drafts.sort(key=lambda item: (-item["published_count"], -item["score_sum"], item["city_key"]))
    stamps = [item["latest_ts"] for item in drafts if item["latest_ts"]]
    oldest = min(stamps) if stamps else 0
    newest = max(stamps) if stamps else 0
    span = newest - oldest
    cities: List[Dict[str, Any]] = []
    for index, item in enumerate(drafts, start=1):
        if not item["latest_ts"] or span <= 0:
            recency = 1.0
        else:
            recency = round((item["latest_ts"] - oldest) / span, 3)
        cities.append(
            {
                "city": item["city"],
                "city_ko": item["city_ko"],
                "slug": item["slug"],
                "lat": item["lat"],
                "lng": item["lng"],
                "published_count": item["published_count"],
                "rank": index,
                "is_top": index <= TOP_CITY_LIMIT,
                "quality_score": item["quality_score"],
                "trending_percent": item["trending_percent"],
                "trending_new": item["trending_new"],
                "keywords": item["keywords"],
                "latest_at": item["latest_at"],
                "recency": recency,
            }
        )
    return {"period": key, "cities": cities}
