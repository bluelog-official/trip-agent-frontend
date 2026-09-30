"""메인 지구본에 올릴 도시별 발행 가이드 계약."""

from typing import List, Optional

from pydantic import BaseModel, Field


class GlobeCityPoint(BaseModel):
    """발행된 가이드가 있는 도시 한 곳."""

    city: str = Field(description="영문 도시명")
    city_ko: str = Field(description="한글 도시명")
    slug: str = Field(description="도시 가이드 목록 경로에 쓰는 슬러그")
    lat: float = Field(description="위도")
    lng: float = Field(description="경도")
    published_count: int = Field(ge=0, description="선택 기간에 발행된 가이드 수")
    rank: int = Field(ge=1, description="기간 내 IP 추천 수, 발행 건수, 품질 점수 기준 순위. 1이 가장 높음")
    vote_count: int = Field(default=0, ge=0, description="선택 기간에 이 도시 가이드가 받은 IP 추천 수")
    article_id: str = Field(default="", description="호버 카드에서 추천하는 대표 가이드 id")
    country: str = Field(default="", description="국가명")
    flag: str = Field(default="", description="국가 깃발 이모지")
    thumbnail: str = Field(default="", description="대표 썸네일 이미지 주소")
    is_top: bool = Field(description="상위 5개 도시이면 True")
    quality_score: int = Field(ge=0, le=100, description="선택 기간 가이드의 품질 점수 평균")
    trending_percent: Optional[int] = Field(default=None, description="직전 동일 기간 대비 증감률")
    trending_new: bool = Field(default=False, description="직전 기간 건수가 0이고 이번 기간에 발행이 있으면 True")
    keywords: List[str] = Field(default_factory=list, description="가이드 해시태그 중 빈도 상위 2개")
    latest_at: str = Field(default="", description="가장 최근 가이드 작성일 YYYY-MM-DD")
    recency: float = Field(ge=0, le=1, description="선택 결과 안에서의 최신도. 1이 가장 최근")


class GlobeMapResponse(BaseModel):
    period: str
    cities: List[GlobeCityPoint] = Field(default_factory=list)
