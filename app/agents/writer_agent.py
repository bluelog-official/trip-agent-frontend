"""Writer Agent: AdSense 최적화 마크다운 아티클 작성 LLM 오케스트레이션."""

import asyncio
from typing import Optional, Tuple

from google.genai import types

from app.agents.utils import generate_with_fallback
from app.schemas.guide_schema import CityKeywordProfile, ResearchOutput
from app.agents.syndication_agent import is_english_language
from app.services.content_variation import finish_writer_article, writer_duration_block
from app.services.keyword_map import format_keyword_context, resolve_city_keywords
from app.services.magazine_matrix import prompt_block_for, resolve_matrix

SYSTEM_PROMPT = (
    "당신은 구글 애드센스 수익화에 최적화된 한국어 여행 블로그를 쓰는 전문 작가입니다. "
    "JSON이 아닌 순수 마크다운 본문만 반환하세요. "
    "Strictly generate 100% pure target language without mixing foreign phrases. "
    "본문, 제목, 표는 100% 한국어만 사용하고 영어 문장이나 외국어 괄호 설명을 섞지 마세요."
)
ENGLISH_SYSTEM_PROMPT = (
    "You write AdSense-ready English travel articles for a global audience. "
    "Return markdown only, with no JSON and no code fences. "
    "Strictly generate 100% pure target language without mixing foreign phrases. "
    "The article must be 100% English. Never insert Korean words, Hangul characters, "
    "or parenthetical Korean explanations."
)


def _english_keyword_block(profile: Optional[CityKeywordProfile]) -> str:
    if profile is None or not profile.primary_keyword:
        return ""
    return "\n".join(
        [
            "[Target keywords]",
            "- Primary Keyword: {0}".format(profile.primary_keyword),
            "- Long-tail Keywords: {0}".format(", ".join(profile.long_tail_keywords)),
            "- Local Food/Spot: {0}".format(", ".join(profile.local_food_spots)),
        ]
    )


def _build_english_writer_prompt(
    destination: str,
    research: ResearchOutput,
    profile: Optional[CityKeywordProfile] = None,
    duration: str = "",
    budget: str = "",
) -> str:
    keyword_block = _english_keyword_block(profile)
    keyword_section = "\n{0}\n".format(keyword_block) if keyword_block else ""
    matrix_block = prompt_block_for(destination, duration, budget, "en")
    duration_rule = matrix_block or writer_duration_block(destination, "en")
    keyword_rule = ""
    if keyword_block:
        keyword_rule = (
            "7. Express the Primary Keyword as one natural English H2. "
            "Spread the ideas behind the Long-tail Keywords through the body in English only. "
            "Prefer Local Food/Spot names in the meal table, written in English. "
            "Never copy Korean or other foreign keyword text into the article.\n"
        )
    return """
    You write AdSense-ready travel guides for a global audience.
    Turn the research below into a natural, expert markdown article.
    Return markdown only. Do not wrap the article in code fences or JSON.

    [Research]
    - Destination: {destination}
    - Attractions: {attractions}
    - Places to eat: {food_spots}
    - Currency: {currency}
    - SEO keywords: {keywords}
    - Local tip: {local_tip}
    {keyword_section}
    [Writing rules]
    1. Build the article with H2 (##) and H3 (###) headings.
    2. Skip greetings and filler introductions. Start with the guide itself.
    3. Include one markdown table for recommended meals and expected cost.
       Columns: Category | Recommended place | Expected cost | Local rating
    4. Put the local tip where a reader will actually see it.
    5. Write at least 1,500 characters in a natural expert English travel-blog voice.
    6. Output markdown only, with no code blocks and no JSON.
    {keyword_rule}8. Write the full article in natural English for global readers. Headings, table labels, and prose must be English. Translate any non-English research note or keyword into English, and do not keep the original foreign wording.
    9. Strictly generate 100% pure target language without mixing foreign phrases. Every heading, table label, and sentence must stay in English. Never insert Korean words, Hangul, or parenthetical Korean explanations such as "도쿄 여행 필수 라멘 투어".
    {duration_rule}
    """.format(
        destination=destination,
        attractions=", ".join(research.attractions),
        food_spots=", ".join(research.food_spots),
        currency=research.target_currency,
        keywords=", ".join(research.seo_keywords),
        local_tip=research.local_tip,
        keyword_section=keyword_section,
        keyword_rule=keyword_rule,
        duration_rule=duration_rule,
    ).strip()


def build_writer_prompt(
    destination: str,
    research: ResearchOutput,
    profile: Optional[CityKeywordProfile] = None,
    target_language: str = "ko",
    duration: str = "",
    budget: str = "",
) -> str:
    if is_english_language(target_language):
        return _build_english_writer_prompt(destination, research, profile, duration, budget)

    keyword_block = format_keyword_context(profile)
    keyword_section = ""
    keyword_rule = ""
    matrix_block = prompt_block_for(destination, duration, budget, "ko")
    duration_rule = matrix_block or writer_duration_block(destination, "ko")
    if keyword_block:
        keyword_section = "\n    {0}\n".format(keyword_block)
        keyword_rule = (
            "7. Primary Keyword를 H2 소제목 한 곳에 자연스럽게 넣고, "
            "Long-tail Keywords를 본문에 분산하세요. "
            "Local Food/Spot은 맛집 표에 우선 반영하세요.\n"
        )
    style_rule = "5. 어조는 전문가답게, 문체는 자연스러운 한국어 블로그 스타일로 1,500자 이상 작성하세요."
    return """
    당신은 구글 애드센스(AdSense) 수익화를 극대화하는 전문 여행 블로거입니다.
    앞서 Research Agent가 조사한 아래 데이터를 바탕으로, AI 저품질 감지를 우회할 수 있는
    매우 자연스럽고 전문적인(EEAT 충족) 마크다운 아티클을 작성하세요.

    [리서치 데이터]
    - 목적지: {destination}
    - 관광지: {attractions}
    - 맛집: {food_spots}
    - 통화 단위: {currency}
    - SEO 키워드: {keywords}
    - 로컬 팁: {local_tip}
    {keyword_section}
    [작성 규칙]
    1. H2(##), H3(###) 태그를 사용하여 구조화된 목차를 만드세요.
    2. 인사말이나 불필요한 서론은 제외하고 바로 본문으로 시작하세요.
    3. 본문 내에 '추천 맛집 및 예상 비용'을 반드시 마크다운 표(Table) 형태로 만드세요.
       - 표의 컬럼: [카테고리 | 추천 장소 | 예상 비용 | 별점 (현지인 기준)]
    4. 리서치 데이터에 있는 '로컬 팁'을 잘 보이는 곳에 강조하여 작성하세요.
    {style_rule}
    6. 코드 블록이나 JSON 없이 마크다운 본문만 출력하세요.
    {keyword_rule}8. Strictly generate 100% pure target language without mixing foreign phrases. 제목, 표, 본문은 100% 한국어로만 작성하고 영어 문장이나 외국어 괄호 설명을 넣지 마세요.
    {duration_rule}
    """.format(
        destination=destination,
        attractions=", ".join(research.attractions),
        food_spots=", ".join(research.food_spots),
        currency=research.target_currency,
        keywords=", ".join(research.seo_keywords),
        local_tip=research.local_tip,
        keyword_section=keyword_section,
        keyword_rule=keyword_rule,
        style_rule=style_rule,
        duration_rule=duration_rule,
    ).strip()


async def run_writer_agent(
    destination: str,
    research: ResearchOutput,
    profile: Optional[CityKeywordProfile] = None,
    target_language: str = "ko",
    duration: str = "",
    budget: str = "",
) -> Tuple[str, str]:
    """리서치 데이터를 마크다운 아티클로 변환하고 (본문, 사용 모델명)을 반환한다."""
    print("✍️ [Agent 2] {0} 마크다운 아티클 작성 시작...".format(destination))
    matrix = resolve_matrix(destination, duration, budget)

    config = types.GenerateContentConfig(temperature=0.8)

    if profile is None:
        profile = resolve_city_keywords(destination)

    system_prompt = ENGLISH_SYSTEM_PROMPT if is_english_language(target_language) else SYSTEM_PROMPT
    article_markdown, model_used = await generate_with_fallback(
        prompt=build_writer_prompt(destination, research, profile, target_language, duration, budget),
        system_prompt=system_prompt,
        config=config,
        expect_json=False,
    )

    if matrix is None:
        article_markdown = finish_writer_article(article_markdown.strip(), destination, target_language)
    else:
        article_markdown = article_markdown.strip()
    if not article_markdown.strip():
        raise RuntimeError("Writer Agent가 빈 아티클을 반환했습니다.")

    print("✅ [Agent 2] 아티클 작성 완료 ({0}자)".format(len(article_markdown)))
    print("=" * 50 + "\n")
    return article_markdown, model_used


if __name__ == "__main__":
    mock = ResearchOutput(
        attractions=["우메다 스카이빌딩", "오사카성", "도톤보리"],
        food_spots=["구로몬 시장", "다이키 스이산", "리쿠로 아저씨 치즈케이크"],
        seo_keywords=["오사카 3박4일 코스", "오사카 가성비 맛집"],
        target_currency="¥",
        local_tip="지하철 1일권 대신 엔조이 에코카드를 쓰면 주요 관광지 할인도 함께 받는다.",
    )
    markdown, used_model = asyncio.run(run_writer_agent("Osaka", mock))
    print("\n[단독 테스트 결과] 사용 모델: {0}".format(used_model))
    print(markdown[:400] + "...")
