"""가이드 본문의 글자 수와 구조로 QA 점수, 등급, 별점, 사유를 계산한다.

LLM을 호출하지 않는다. 게시 상태나 공개 여부는 다루지 않는다.
"""

import re
from dataclasses import dataclass
from typing import Tuple


_FRONTMATTER = re.compile(r"^---\r?\n[\s\S]*?\r?\n---\r?\n?")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_URL = re.compile(r"https?://\S+")
_PHOTO_CREDIT = re.compile(r"(?im)^\*Photo by[^\n]*$")
_WHITESPACE = re.compile(r"\s+")
_H2 = re.compile(r"(?m)^## ")
_TABLE = re.compile(r"(?m)^\s*\|[^\n]*-{3,}")
_TIME_HEADING = re.compile(
    r"(?im)^#{2,3}[ \t]+.*(?:"
    r"\bdays?\b|"
    r"\b(?:morning|afternoon|evening|night)\b|"
    r"\d+\s*일\s*차|"
    r"오전|오후|아침|저녁|밤"
    r")"
)
_CLOCK = re.compile(r"\b\d{1,2}:\d{2}\b")
_DAY_PART = re.compile(r"(?i)\b(?:morning|afternoon|evening|night)\b|(?:오전|오후|아침|저녁|밤)")
_TIP_HEADING = re.compile(r"(?im)^#{2,3}[ \t]+.*(?:local tip|소회|후기|reflection)\b")
_EVALUATION = re.compile(
    r"(?i)\b(?:worth it|i felt|i found|i would|skip|do not|don't|recommend|remember|honestly|better)\b|"
    r"(느꼈|마음에|추천|체감|좋았|아쉬|솔직|기억에|소회)"
)

# 글자 수 구간이 기본점이다. 구조 가산은 최대 30점이라 1500자 이상만 100점에 닿는다.
_LENGTH_POINTS = (
    (1500, 70, "1500자 이상"),
    (1200, 64, "1200자 이상"),
    (1000, 52, "1000자 이상"),
    (700, 40, "700자 이상"),
    (400, 28, "400자 이상"),
    (0, 10, "400자 미만"),
)

# 100점은 S/5.00, 60점 미만은 REISSUE/0.00. 그 사이 등급은 점수 하한으로 고정한다.
_GRADE_FLOORS = (
    (100, "S", 5.00),
    (97, "A+", 4.75),
    (94, "A0", 4.50),
    (91, "A-", 4.25),
    (88, "B+", 4.00),
    (85, "B0", 3.70),
    (82, "B-", 3.40),
    (79, "C+", 3.10),
    (76, "C0", 2.80),
    (73, "C-", 2.50),
    (70, "D+", 2.10),
    (65, "D0", 1.60),
    (60, "D-", 1.00),
    (0, "REISSUE", 0.00),
)


@dataclass(frozen=True)
class QAScore:
    qa_score: int
    rating_grade: str
    star_rating: float
    qa_reason: str
    content_length: int


def article_body(markdown: str) -> str:
    """프론트매터, 이미지, URL, 사진 크레딧을 뺀 본문."""
    text = _FRONTMATTER.sub("", markdown or "", count=1)
    text = _IMAGE.sub(" ", text)
    text = _URL.sub(" ", text)
    text = _PHOTO_CREDIT.sub(" ", text)
    return text


def content_length(markdown: str) -> int:
    """본문 글자 수. 공백은 세지 않는다."""
    return len(_WHITESPACE.sub("", article_body(markdown)))


def length_band(count: int) -> Tuple[int, str]:
    """글자 수에 해당하는 기본점과 구간 이름."""
    for floor, points, label in _LENGTH_POINTS:
        if count >= floor:
            return points, label
    return 10, "400자 미만"


def grade_for_score(score: int) -> Tuple[str, float]:
    """점수에 대응하는 등급과 별점."""
    bounded = max(0, min(100, int(score)))
    for floor, grade, star in _GRADE_FLOORS:
        if bounded >= floor:
            return grade, star
    return "REISSUE", 0.00


def _timeline_points(body: str) -> int:
    headings = len(_TIME_HEADING.findall(body))
    clock_hits = len(_CLOCK.findall(body))
    if headings >= 2 or clock_hits >= 2:
        return 12
    if headings >= 1 or clock_hits >= 1 or _DAY_PART.search(body):
        return 6
    return 0


def _reflection_points(body: str) -> int:
    has_heading = _TIP_HEADING.search(body) is not None
    has_voice = _EVALUATION.search(body) is not None
    if has_heading and has_voice:
        return 12
    if has_heading or has_voice:
        return 6
    return 0


def _outline_points(body: str) -> int:
    headings = len(_H2.findall(body))
    has_table = _TABLE.search(body) is not None
    if headings >= 3 and has_table:
        return 6
    if headings >= 2 or has_table:
        return 3
    return 0


def _reason(count: int, band: str, timeline: int, reflection: int, outline: int, score: int, grade: str, star: float) -> str:
    if timeline == 12:
        timeline_note = "시간 순서 타임라인이 분명합니다."
    elif timeline == 6:
        timeline_note = "시간 순서 단서가 약합니다."
    else:
        timeline_note = "시간 순서 타임라인이 없습니다."
    if reflection == 12:
        reflection_note = "주관적 소회가 있습니다."
    elif reflection == 6:
        reflection_note = "주관적 소회가 약합니다."
    else:
        reflection_note = "주관적 소회가 없습니다."
    if outline == 6:
        outline_note = "소제목과 비용 표가 있습니다."
    elif outline == 3:
        outline_note = "소제목 또는 표가 일부만 있습니다."
    else:
        outline_note = "소제목과 표가 부족합니다."
    if score < 60:
        grade_note = "60점 미만이라 등급은 REISSUE이고 별점은 0.00입니다."
    else:
        grade_note = "등급 {0}, 별점 {1:.2f}.".format(grade, star)
    return " ".join(
        (
            "글자 수 {0}자 ({1}).".format(count, band),
            timeline_note,
            reflection_note,
            outline_note,
            grade_note,
        )
    )


def score_article(markdown: str) -> QAScore:
    """본문 글자 수와 타임라인, 소회, 소제목/표로 0~100점을 매긴다."""
    body = article_body(markdown)
    count = len(_WHITESPACE.sub("", body))
    base, band = length_band(count)
    timeline = _timeline_points(body)
    reflection = _reflection_points(body)
    outline = _outline_points(body)
    score = max(0, min(100, base + timeline + reflection + outline))
    grade, star = grade_for_score(score)
    if score < 60:
        grade = "REISSUE"
        star = 0.00
    return QAScore(
        qa_score=score,
        rating_grade=grade,
        star_rating=star,
        qa_reason=_reason(count, band, timeline, reflection, outline, score, grade, star),
        content_length=count,
    )
