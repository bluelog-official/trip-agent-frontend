"""제휴 입점 신청과 어드민 승인."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.limiter import limiter

from app.schemas.partner_schema import PartnerApply, PartnerApplication, PartnerApplicationList, PartnerApproval
from app.services.auth_service import authorization_is_valid
from app.services.partner_service import apply_partner, approve_partner, list_partner_applications

router = APIRouter(tags=["partners"])


def require_admin(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization_is_valid(authorization or ""):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/api/partners", response_model=PartnerApplication)
@limiter.limit("5/minute")
def post_partner(request: Request, body: PartnerApply) -> PartnerApplication:
    try:
        record = apply_partner(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PartnerApplication.model_validate(record)


@router.get(
    "/api/v1/admin/partners",
    response_model=PartnerApplicationList,
    dependencies=[Depends(require_admin)],
)
def get_admin_partners() -> PartnerApplicationList:
    return PartnerApplicationList.model_validate({"partners": list_partner_applications()})


@router.post(
    "/api/v1/admin/partners/{partner_id}/approve",
    response_model=PartnerApproval,
    dependencies=[Depends(require_admin)],
)
def post_approve_partner(partner_id: int) -> PartnerApproval:
    try:
        record = approve_partner(partner_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="partner was not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PartnerApproval(
        partner=PartnerApplication.model_validate(record),
        guide_id=str(record.get("guide_id") or ""),
        article_markdown=str(record.get("article_markdown") or ""),
    )
