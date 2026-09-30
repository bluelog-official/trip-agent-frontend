"""소셜 로그인 세션과 포인트 지갑 계약."""

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.voucher_schema import VoucherCard


SocialProvider = Literal["google", "apple", "kakao"]
PublishState = Literal["PENDING", "VERIFIED", "PUBLISHED", "REJECTED"]


class AuthProviderInfo(BaseModel):
    id: SocialProvider
    name: str
    configured: bool


class AuthProviderList(BaseModel):
    providers: List[AuthProviderInfo]


class OAuthStart(BaseModel):
    provider: SocialProvider
    authorize_url: str


class UserSession(BaseModel):
    user_id: int
    email: str
    name: str = ""
    auth_provider: str
    points_balance: int = 0
    migrated_reports: int = 0
    migrated_point_logs: int = 0


class WalletLog(BaseModel):
    id: int
    amount: int
    reason: str
    article_id: str = ""
    created_at: str


class WalletReport(BaseModel):
    id: int
    place: str
    city: str
    guest_email: str = ""
    publish_state: PublishState
    fact_check_status: str
    status: str
    published_guide_id: str = ""
    xrpl_tx_hash: str = ""
    xrpl_url: str = ""
    content_sha256: str = ""


class WalletView(BaseModel):
    user_id: int
    email: str
    name: str = ""
    auth_provider: str
    points_balance: int
    logs: List[WalletLog] = Field(default_factory=list)
    reports: List[WalletReport] = Field(default_factory=list)
    saved_guides: List[str] = Field(default_factory=list)
    vouchers: List[VoucherCard] = Field(default_factory=list)


class SavedGuideRequest(BaseModel):
    guide_id: str

    @field_validator("guide_id", mode="before")
    @classmethod
    def _strip(cls, value: object) -> str:
        return str(value or "").strip()
