"""포인트 적립과 제휴 상점 계약. 소셜 로그인 사용자는 이후 auth_provider로 연결한다."""

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


PointReason = Literal["MAGAZINE_PUBLISHED", "UGC_TOP_RANK_BONUS"]


class PointAccrualRequest(BaseModel):
    email: str
    reason: PointReason
    article_id: str = ""
    auth_provider: str = "email"

    @field_validator("email", "article_id", "auth_provider", mode="before")
    @classmethod
    def _strip(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()


class PointLogRecord(BaseModel):
    id: int
    user_id: int
    email: str
    amount: int
    reason: str
    article_id: str = ""
    created_at: str
    created: bool = True


class PartnerMerchantRecord(BaseModel):
    id: int
    name: str
    city: str
    discount_rate: float
    status: str


class RewardsOverview(BaseModel):
    publish_points: int
    top_rank_points: int
    top_rank_limit: int
    auth_providers: List[str] = Field(default_factory=lambda: ["google", "apple"])
    partners: List[PartnerMerchantRecord] = Field(default_factory=list)
