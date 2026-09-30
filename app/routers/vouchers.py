"""포인트 바우처 발행과 매장 검증."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.routers.oauth import require_user
from app.schemas.voucher_schema import VoucherCard, VoucherClaim, VoucherList, VoucherVerifyRequest, VoucherVerifyResult
from app.services.voucher_service import claim_voucher, list_vouchers, verify_voucher

router = APIRouter(tags=["vouchers"])


@router.get("/api/vouchers", response_model=VoucherList)
def get_vouchers(authorization: Optional[str] = Header(default=None)) -> VoucherList:
    user = require_user(authorization)
    return VoucherList.model_validate({"vouchers": list_vouchers(int(user["id"]))})


@router.post("/api/vouchers/claim", response_model=VoucherCard)
def post_claim(
    body: VoucherClaim,
    authorization: Optional[str] = Header(default=None),
) -> VoucherCard:
    user = require_user(authorization)
    try:
        record = claim_voucher(int(user["id"]), int(body.merchant_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="partner shop was not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return VoucherCard.model_validate(record)


@router.post("/api/vouchers/verify", response_model=VoucherVerifyResult)
def post_verify(body: VoucherVerifyRequest) -> VoucherVerifyResult:
    if not body.voucher_code:
        raise HTTPException(status_code=400, detail="voucher code is required")
    return VoucherVerifyResult.model_validate(
        verify_voucher(body.voucher_code, body.qr_token, body.consume)
    )
