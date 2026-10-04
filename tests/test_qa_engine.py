"""QA 등급은 글자 수 구간과 구조 가산으로 결정된다. 100점은 S, 60점 미만은 REISSUE."""

from app.services.qa_engine import content_length, grade_for_score, length_band, score_article


def _pad(text: str, count: int) -> str:
    current = content_length(text)
    if current > count:
        raise AssertionError("structure is already {0} chars".format(current))
    return text + ("가" * (count - current))


def _full(count: int) -> str:
    body = "\n".join(
        (
            "## Day 1: Market",
            "Walk the lane before 9:00 and again at 11:00.",
            "## Day 2: River",
            "## Local Tip",
            "The earlier gate is worth it.",
            "| Category | Cost |",
            "| --- | --- |",
            "| soup | 10 |",
        )
    )
    return _pad(body, count)


def test_grade_ends_at_s_and_reissue():
    assert grade_for_score(100) == ("S", 5.00)
    assert grade_for_score(97) == ("A+", 4.75)
    assert grade_for_score(94) == ("A0", 4.50)
    assert grade_for_score(91) == ("A-", 4.25)
    assert grade_for_score(88) == ("B+", 4.00)
    assert grade_for_score(85) == ("B0", 3.70)
    assert grade_for_score(82) == ("B-", 3.40)
    assert grade_for_score(79) == ("C+", 3.10)
    assert grade_for_score(76) == ("C0", 2.80)
    assert grade_for_score(73) == ("C-", 2.50)
    assert grade_for_score(70) == ("D+", 2.10)
    assert grade_for_score(65) == ("D0", 1.60)
    assert grade_for_score(60) == ("D-", 1.00)
    assert grade_for_score(59) == ("REISSUE", 0.00)


def test_length_bands_follow_the_character_floors():
    assert length_band(1499) == (64, "1200자 이상")
    assert length_band(1500) == (70, "1500자 이상")
    assert length_band(1199) == (52, "1000자 이상")
    assert length_band(1200) == (64, "1200자 이상")
    assert length_band(999) == (40, "700자 이상")
    assert length_band(1000) == (52, "1000자 이상")
    assert length_band(699) == (28, "400자 이상")
    assert length_band(700) == (40, "700자 이상")
    assert length_band(399) == (10, "400자 미만")
    assert length_band(400) == (28, "400자 이상")


def test_full_structure_maps_each_length_band_to_a_grade():
    perfect = score_article(_full(1500))
    assert perfect.content_length == 1500
    assert perfect.qa_score == 100
    assert perfect.rating_grade == "S"
    assert perfect.star_rating == 5.00
    assert "1500자 이상" in perfect.qa_reason

    long = score_article(_full(1200))
    assert long.qa_score == 94
    assert long.rating_grade == "A0"
    assert long.star_rating == 4.50

    mid = score_article(_full(1000))
    assert mid.qa_score == 82
    assert mid.rating_grade == "B-"
    assert mid.star_rating == 3.40

    short = score_article(_full(700))
    assert short.qa_score == 70
    assert short.rating_grade == "D+"
    assert short.star_rating == 2.10

    thin = score_article(_full(400))
    assert thin.qa_score == 58
    assert thin.rating_grade == "REISSUE"
    assert thin.star_rating == 0.00
    assert "REISSUE" in thin.qa_reason

    below = score_article(_full(399))
    assert below.qa_score == 40
    assert below.rating_grade == "REISSUE"
    assert below.star_rating == 0.00


def test_length_alone_on_a_long_article_stays_at_d_plus():
    padded = _pad("장소 이름만 적힌 문장.", 1500)
    result = score_article(padded)
    assert result.content_length == 1500
    assert result.qa_score == 70
    assert result.rating_grade == "D+"
    assert "시간 순서 타임라인이 없습니다." in result.qa_reason
    assert "주관적 소회가 없습니다." in result.qa_reason


def test_partial_structure_reaches_a_plus():
    body = "\n".join(
        (
            "## Notes",
            "### Day 1: Market",
            "### Day 2: River",
            "Arrive before 9:00 and return at 18:00.",
            "## Local Tip",
            "The side gate is worth it.",
        )
    )
    result = score_article(_pad(body, 1500))
    assert result.qa_score == 97
    assert result.rating_grade == "A+"
    assert result.star_rating == 4.75
