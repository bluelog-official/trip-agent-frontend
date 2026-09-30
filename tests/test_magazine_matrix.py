"""기간 × 예산 파일명, 프롬프트, 오프라인 매거진."""

from datetime import date

import pytest

from app.services.guide_service import city_label, evaluate_article
from app.services.magazine_matrix import (
    EXAMPLE_MATRIX,
    build_matrix_article_prompt,
    parse_matrix_guide_id,
    prompt_block_for,
    render_offline_guide,
    resolve_matrix,
)
from app.services.reddit_draft_service import destination_from_guide_id
from scripts.magazine_matrix_generator import write_guide


def test_example_filenames():
    tokyo_day, tokyo_mid, tokyo_week = [resolve_matrix(*row) for row in EXAMPLE_MATRIX]
    assert tokyo_day.filename == "tokyo_1_days_50usd_guide.md"
    assert tokyo_mid.filename == "tokyo_3_days_200usd_guide.md"
    assert tokyo_week.filename == "tokyo_1_week_budget_guide.md"
    assert tokyo_day.budget_filter == "under_50"
    assert tokyo_mid.budget_filter == "per_200"
    assert tokyo_week.budget_key == "budget"
    assert tokyo_week.budget_filter == "under_50"


def test_city_label_keeps_the_city_and_leaves_legacy_files():
    assert city_label("tokyo_1_days_50usd_guide.md") == "Tokyo"
    assert city_label("new_york_3_days_200usd_guide.md") == "New York"
    assert city_label("tokyo_guide.md") == "Tokyo"
    assert city_label("tokyo_20261001_guide.md") == "Tokyo 20261001"
    assert destination_from_guide_id("tokyo_1_week_budget_guide.md") == "Tokyo"
    parsed = parse_matrix_guide_id("guides/new_york_1_week_luxury_guide.md")
    assert parsed.city == "New York"
    assert parsed.duration_key == "1_week"
    assert parsed.budget_key == "luxury"


def test_duration_and_budget_must_be_a_pair():
    assert resolve_matrix("Tokyo") is None
    with pytest.raises(ValueError):
        resolve_matrix("Tokyo", "1_days", "")
    with pytest.raises(ValueError):
        resolve_matrix("Tokyo", "fortnight", "luxury")


def test_prompt_carries_route_meals_and_o2o():
    spec = resolve_matrix("Tokyo", "1 day", "under $50/day")
    prompt = build_matrix_article_prompt(spec)
    assert "1 Day" in prompt
    assert "Under $50/day" in prompt
    assert "Offline restaurants" in prompt
    assert "O2O district" in prompt
    assert "Asakusa" in prompt

    korean = prompt_block_for("Tokyo", "3_days", "200usd", "ko")
    assert "3 Days" in korean
    assert "$200/day" in korean
    assert "O2O" in korean

    english = prompt_block_for("Tokyo", "1_week", "budget", "en")
    assert "[Duration x budget]" in english
    assert "1 Week" in english
    assert "offline" in english.casefold()
    assert prompt_block_for("Tokyo") == ""


def test_offline_guide_meets_the_quality_gate(tmp_path):
    path = write_guide("Tokyo", "1_days", "50usd", tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path.name == "tokyo_1_days_50usd_guide.md"
    assert 'duration_key: "1_days"' in text
    assert 'budget_key: "50usd"' in text
    assert 'city: "Tokyo"' in text
    assert "## O2O District" in text
    assert "| Category | Recommended Location | Estimated Cost | Rating |" in text
    score = evaluate_article(text)
    assert score.quality_score >= 75
    assert not score.violations

    week = render_offline_guide(resolve_matrix("Osaka", "1_week", "luxury"), today=date(2026, 10, 1))
    assert 'budget_key: "luxury"' in week
    assert "Day 7" in week
    assert "Osaka" in week
