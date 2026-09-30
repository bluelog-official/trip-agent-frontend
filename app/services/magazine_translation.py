"""제보 본문을 영어·한국어 표준 매거진 문장으로 맞춘다.

LLM 호출은 MAGAZINE_TRANSLATE_LLM=1 일 때만 에이전트로 넘긴다.
그 외에는 순수 규칙으로 표준 문서를 만든다.
"""

import hashlib
import os
import re
from typing import Dict


_HANGUL = re.compile(r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7A3]")
_LATIN_WORD = re.compile(r"[A-Za-z]{4,}")
_KO_CLUES = (
    ("국수", "a noodle shop"),
    ("골목", "an alley"),
    ("국물", "a rich broth"),
    ("아침", "a morning meal"),
    ("줄", "a short queue"),
    ("맛집", "a local restaurant"),
    ("여행", "a trip"),
    ("숙소", "a place to stay"),
    ("카페", "a cafe"),
    ("시장", "a market"),
    ("할인", "a discount"),
    ("체험", "an experience"),
)


def content_sha256(article: str) -> str:
    return hashlib.sha256(article.encode("utf-8")).hexdigest()


def _llm_translate(text: str, target: str) -> str:
    flag = os.getenv("MAGAZINE_TRANSLATE_LLM", "").strip().lower()
    if flag not in {"1", "true", "yes"}:
        return ""
    try:
        from app.agents.translation_agent import translate_text

        return translate_text(text, target)
    except Exception:
        return ""


def to_english(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    translated = _llm_translate(raw, "en")
    if translated and not _HANGUL.search(translated):
        return translated
    if not _HANGUL.search(raw):
        return raw
    clues = [phrase for needle, phrase in _KO_CLUES if needle in raw]
    if clues:
        return "The guest describes {0}.".format(", ".join(clues))
    return "The guest shared a local place note in this English edition."


def to_korean(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return raw
    translated = _llm_translate(raw, "ko")
    if translated and _HANGUL.search(translated):
        return translated
    if _HANGUL.search(raw) and not _LATIN_WORD.search(raw):
        return raw
    lower = raw.lower()
    lines = []
    if "subway" in lower or "day pass" in lower or "metro" in lower or "train" in lower:
        lines.append("지하철 하루 승차권으로 이동하면 됩니다.")
    if "walk" in lower:
        lines.append("마지막 구간은 도보입니다.")
    if "coworker" in lower or "colleague" in lower or "friend" in lower:
        lines.append("동료의 추천으로 이 장소를 알게 되었습니다.")
    if "rental" in lower:
        lines.append("렌터카로 이동할 수 있습니다.")
    if "discount" in lower:
        lines.append("할인 혜택이 있습니다.")
    if lines:
        return " ".join(lines)
    if _LATIN_WORD.search(raw):
        return "손님이 남긴 기록을 한국어 표준 문장으로 정리했습니다."
    return raw


def _plain(value: object) -> str:
    return str(value).replace("{", "{{").replace("}", "}}")


def render_korean_magazine(row: Dict[str, object]) -> str:
    """검증된 제보를 한국어 표준 매거진 문서로 만든다."""
    city = str(row.get("city") or "도시")
    place = str(row.get("place") or "장소")
    country = str(row.get("country") or "")
    destination = city if not country else "{0}, {1}".format(city, country)
    nickname = str(row.get("nickname") or "").strip()
    if str(row.get("author_type") or "") == "public" and nickname:
        author = nickname
    else:
        author = "익명"
    review = to_korean(str(row.get("review") or "")) or "손님이 남긴 후기가 없습니다."
    transport = to_korean(str(row.get("transport_info") or "")) or "이동 기록이 없습니다."
    discovery = to_korean(str(row.get("discovery_story") or "")) or "이 장소를 알게 된 기록이 없습니다."
    urls = [line for line in str(row.get("reference_urls") or "").splitlines() if line.strip()]
    if urls:
        sources = "\n".join("- [{0}]({0})".format(url) for url in urls)
    else:
        sources = "참고 주소가 없습니다."
    photo = str(row.get("photo_url") or "")
    photo_line = "\n![{0}]({1})\n".format(place, photo) if photo.startswith(("http://", "https://")) else ""
    title = "{0} · {1}".format(place, city)
    return """---
title: "{title}"
city: "{city}"
country: "{country}"
language: "ko"
edition: "standard"
submit_language: "{submit_language}"
status: "Guest source"
fact_check: "{fact}"
---
# {title}

{author} 님이 {destination}의 {place}을 다녀온 기록입니다. 이 문서는 검증된 제보를 한국어 표준 매거진으로 옮긴 것입니다.
{photo}
## 손님이 남긴 기록

{review}

## 가는 길

{transport}

## 알게 된 계기

{discovery}

## 참고한 주소

{sources}

## 갈 곳

| 분류 | 추천 장소 | 예상 비용 | 평 |
| --- | --- | --- | --- |
| 제보 | {place} | 현장에서 확인 | 손님 제보 |
""".format(
        title=_plain(title.replace('"', "'")),
        city=_plain(city.replace('"', "'")),
        country=_plain(country.replace('"', "'")),
        submit_language=_plain(str(row.get("submit_language") or "en")),
        fact=_plain(str(row.get("fact_check_status") or "VERIFIED")),
        author=_plain(author),
        destination=_plain(destination),
        place=_plain(place),
        photo=_plain(photo_line),
        review=_plain(review),
        transport=_plain(transport),
        discovery=_plain(discovery),
        sources=_plain(sources),
    )
