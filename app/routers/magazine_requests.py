"""게스트 매거진 제보 HTTP 라우트."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.limiter import limiter

from app.schemas.magazine_request_schema import (
    FactCheckUpdate,
    GuestPublishResult,
    MagazineRequestCreate,
    MagazineRequestList,
    MagazineRequestRecord,
)
from app.services.auth_service import authorization_is_valid
from app.services.magazine_request_service import (
    create_magazine_request,
    list_magazine_requests,
    publish_verified_request,
    set_fact_check,
)

router = APIRouter(tags=["magazine-requests"])


def require_admin(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization_is_valid(authorization or ""):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/api/magazine-requests", response_model=MagazineRequestRecord)
@limiter.limit("5/minute")
def post_magazine_request(request: Request, body: MagazineRequestCreate) -> MagazineRequestRecord:
    try:
        record = create_magazine_request(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MagazineRequestRecord.model_validate(record)


@router.get(
    "/api/v1/admin/magazine-requests",
    response_model=MagazineRequestList,
    dependencies=[Depends(require_admin)],
)
def get_admin_magazine_requests() -> MagazineRequestList:
    return MagazineRequestList.model_validate({"requests": list_magazine_requests()})


@router.patch(
    "/api/v1/admin/magazine-requests/{request_id}/fact-check",
    response_model=MagazineRequestRecord,
    dependencies=[Depends(require_admin)],
)
def patch_fact_check(request_id: int, body: FactCheckUpdate) -> MagazineRequestRecord:
    try:
        record = set_fact_check(request_id, body.fact_check_status, body.verification_note)
    except LookupError:
        raise HTTPException(status_code=404, detail="magazine request was not found")
    return MagazineRequestRecord.model_validate(record)


@router.post(
    "/api/v1/admin/magazine-requests/{request_id}/publish",
    response_model=GuestPublishResult,
    dependencies=[Depends(require_admin)],
)
def post_publish_verified(request_id: int) -> GuestPublishResult:
    try:
        record = publish_verified_request(request_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="magazine request was not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GuestPublishResult(
        request_id=request_id,
        guide_id=str(record["guide_id"]),
        fact_check_status=record["fact_check_status"],
        article_markdown=str(record["article_markdown"]),
        korean_guide_id=str(record.get("korean_guide_id") or ""),
        english_sha256=str(record.get("english_sha256") or ""),
    )
