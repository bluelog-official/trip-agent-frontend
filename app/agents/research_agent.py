"""Research Agent: 목적지 데이터 수집 LLM 오케스트레이션."""

import asyncio
from typing import Optional, Tuple

from google.genai import types

from app.agents.utils import generate_with_fallback
from app.schemas.guide_schema import CityKeywordProfile, ResearchOutput
from app.services.json_sanitizer import missing_research_fields, normalize_research_json
from app.services.keyword_map import format_keyword_context, resolve_city_keywords
from app.services.magazine_matrix import prompt_block_for

SYSTEM_PROMPT = (
    "당신은 정확한 JSON 데이터를 반환하는 전문 여행 데이터 분석가입니다. "
    "마크다운 기호나 설명 문장 없이 순수 JSON 객체만 반환하세요. "
    'JSON 키는 정확히 "attractions", "food_spots", "seo_keywords", '
    '"target_currency", "local_tip" 다섯 개를 사용하세요.'
)


def build_research_prompt(
    destination: str,
    keyword: str = "",
    profile: Optional[CityKeywordProfile] = None,
    duration: str = "",
    budget: str = "",
) -> str:
    keyword_context = "({0} 중심)".format(keyword) if keyword else ""
    keyword_block = format_keyword_context(profile)
    keyword_rule = ""
    if keyword_block:
        keyword_rule = (
            "아래 도시 타겟 키워드를 그대로 반영하세요. "
            "seo_keywords에는 Long-tail Keywords를 포함하고, "
            "food_spots와 attractions에는 Local Food/Spot을 우선 넣으세요.\n"
            "{0}\n"
        ).format(keyword_block)
    matrix_block = prompt_block_for(destination, duration, budget, "ko")
    matrix_rule = "{0}\n".format(matrix_block) if matrix_block else ""
    return """
    당신은 글로벌 여행 전문가이자 데이터 분석가입니다.
    목적지: {destination} {keyword_context}
    {keyword_rule}
    {matrix_rule}
    이 지역의 최신 여행 정보, 가성비 맛집, SEO 키워드를 분석하여 아래 JSON 스키마로 반환하세요.

    {{
      "attractions": ["필수 관광지 3곳"],
      "food_spots": ["가성비 및 로컬 맛집 3곳"],
      "seo_keywords": ["SEO 롱테일 키워드 5개"],
      "target_currency": "통화 기호 (예: $, ¥, ₩)",
      "local_tip": "관광객은 잘 모르는 현지인만의 꿀팁 1가지"
    }}

    반드시 마크다운 백틱(```json) 없이 순수 JSON 객체만 반환하세요.
    """.format(
        destination=destination,
        keyword_context=keyword_context,
        keyword_rule=keyword_rule,
        matrix_rule=matrix_rule,
    ).strip()


async def run_research_agent(
    destination: str,
    keyword: str = "",
    profile: Optional[CityKeywordProfile] = None,
    duration: str = "",
    budget: str = "",
) -> Tuple[ResearchOutput, str]:
    """목적지 리서치를 수행하고 (검증된 데이터, 사용 모델명)을 반환한다."""
    print("\n" + "=" * 50)
    print("🚀 [Agent 1] {0} 리서치 작업 시작...".format(destination))

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ResearchOutput,
        temperature=0.7,
    )

    if profile is None:
        profile = resolve_city_keywords(destination, keyword)
    focus_keyword = profile.primary_keyword if profile else keyword

    raw_text, model_used = await generate_with_fallback(
        prompt=build_research_prompt(destination, focus_keyword, profile, duration, budget),
        system_prompt=SYSTEM_PROMPT,
        config=config,
        expect_json=True,
    )

    # 백업 모델이 백틱을 감싸거나 키 이름을 바꿔 보내도 여기서 계약 구조로 정렬된다.
    normalized_json = normalize_research_json(raw_text)

    empty_fields = missing_research_fields(normalized_json)
    if empty_fields:
        print("⚠️ [Agent 1] 값이 비어 있는 필드: {0}".format(", ".join(empty_fields)))

    research_data = ResearchOutput.model_validate_json(normalized_json)
    print("✅ [Agent 1] 리서치 데이터 정제 및 파싱 완료")
    return research_data, model_used


if __name__ == "__main__":
    data, model = asyncio.run(run_research_agent("Osaka"))
    print("\n[단독 테스트 결과] 사용 모델: {0}".format(model))
    print("- 관광지: {0}".format(data.attractions))
    print("- 맛집: {0}".format(data.food_spots))
    print("- SEO 키워드: {0}".format(data.seo_keywords))
    print("- 통화: {0}".format(data.target_currency))
    print("- 로컬 팁: {0}".format(data.local_tip))
