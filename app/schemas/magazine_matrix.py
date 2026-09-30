"""기간 × 예산 매거진 파일명과 프롬프트에 쓰는 계약."""

from typing import List, Optional

from pydantic import BaseModel, Field


DURATION_KEYS = ("1_days", "3_days", "1_week")
BUDGET_KEYS = ("50usd", "100usd", "200usd", "budget", "luxury")


class MagazineMatrix(BaseModel):
    """`{city}_{duration}_{budget}_guide.md` 한 편에 붙는 메타데이터."""

    city: str
    city_slug: str
    duration_key: str
    duration_label: str
    budget_key: str
    budget_label: str
    budget_filter: str = Field(description="목록 필터 칩 id. under_50, per_100, per_200, luxury")
    filename: str
    tier: str
    daily_cap_usd: Optional[int] = None
    title: str
    title_form: str
    hashtags: List[str] = Field(default_factory=list)
    day_headings: List[str] = Field(default_factory=list)
