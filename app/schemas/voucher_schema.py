"""포인트 바우처 계약. 코드는 8자이고 QR은 그 코드의 서명 토큰을 담는다."""

from typing import List

from pydantic import BaseModel, Field, field_validator


class VoucherClaim(BaseModel):
    merchant_id: int


class VoucherCard(BaseModel):
    id: int
    merchant_id: int
    merchant_name: str = ""
    offered_benefit: str = ""
    voucher_code: str
    qr_token: str = ""
    qr_svg: str = ""
    points_cost: int
    status: str
    points_balance: int = 0
    created_at: str = ""


class VoucherList(BaseModel):
    vouchers: List[VoucherCard] = Field(default_factory=list)


class VoucherVerifyRequest(BaseModel):
    voucher_code: str = ""
    qr_token: str = ""
    consume: bool = False

    @field_validator("voucher_code", "qr_token", mode="before")
    @classmethod
    def _strip(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()


class VoucherVerifyResult(BaseModel):
    valid: bool
    status: str = ""
    store_name: str = ""
    offered_benefit: str = ""
    voucher_code: str = ""
