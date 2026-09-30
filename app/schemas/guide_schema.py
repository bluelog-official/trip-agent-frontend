"""가이드 생성 파이프라인의 에이전트 간 데이터 교환 계약(DTO)."""

from typing import List

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    destination: str = Field(description="가이드를 생성할 여행 목적지")
    keyword: str = Field(default="", description="선택적 집중 키워드")
    target_language: str = Field(default="ko", description="작성 언어. en 또는 English면 영문 신디케이션")
    duration: str = Field(default="", description="체류 기간. 1_days, 3_days, 1_week. budget과 함께 쓸 때만 적용")
    budget: str = Field(default="", description="하루 예산. 50usd, 100usd, 200usd, budget, luxury")


class CityKeywordProfile(BaseModel):
    """도시 하나에 고정된 타겟 키워드. 가이드 생성 프롬프트에 그대로 주입한다."""

    primary_keyword: str = Field(description="도시 대표 검색 키워드")
    long_tail_keywords: List[str] = Field(description="롱테일 SEO 키워드")
    local_food_spots: List[str] = Field(description="현지 음식 또는 스팟")


class ResearchOutput(BaseModel):
    """Gemini 구조화 출력 스키마이자 Research 단계의 최종 계약.

    필드는 모두 필수다. 백업 LLM의 느슨한 응답은 검증 전에
    `app.services.json_sanitizer`가 이 키 구조로 맞춰준다.
    """

    attractions: List[str] = Field(description="필수 관광지 3곳")
    food_spots: List[str] = Field(description="가성비 및 로컬 맛집 3곳")
    seo_keywords: List[str] = Field(description="SEO에 유리한 롱테일 키워드 5개")
    target_currency: str = Field(description="해당 지역의 통화 기호 (예: $, ¥, ₩)")
    local_tip: str = Field(description="관광객은 잘 모르는 현지인만의 꿀팁 1가지")


class QAOutput(BaseModel):
    is_approved: bool
    quality_score: int
    violations: List[str] = Field(default_factory=list)


class RedditSyndication(BaseModel):
    subreddit: str = Field(description="도시 권역에 맞춘 해외 서브레딧 이름")
    title: str = Field(description="영문 Reddit 게시 제목")
    body: str = Field(description="스팟이 들어간 영문 본문")


class QuoraSyndication(BaseModel):
    question: str = Field(description="답변할 질문")
    answer: str = Field(description="가이드로 이어지는 답변")


class PinterestSyndication(BaseModel):
    board: str = Field(description="보드 이름")
    pin_title: str = Field(description="핀 제목")
    description: str = Field(description="핀 설명")
    image_alt: str = Field(description="핀 이미지 대체 텍스트")


class BacklinkSyndication(BaseModel):
    anchor_text: str = Field(description="링크에 쓸 앵커 텍스트")
    target_path: str = Field(description="가이드 상대 경로")
    outreach_note: str = Field(description="협업 제안용 한 문단")


class SyndicationOutput(BaseModel):
    social_teasers: List[str] = Field(default_factory=list)
    platform_hashtags: List[str] = Field(default_factory=list)
    reddit: RedditSyndication
    quora: QuoraSyndication
    pinterest: PinterestSyndication
    backlink: BacklinkSyndication


class GenerateResponse(BaseModel):
    article_markdown: str
    qa_result: QAOutput
    syndication: SyndicationOutput
    research_model: str = Field(description="Research Agent가 실제로 사용한 모델명")
    writer_model: str = Field(description="Writer Agent가 실제로 사용한 모델명")
