"""게스트 매거진 제보 HTTP 라우트."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.schemas.magazine_request_schema import (
    MagazineRequestCreate,
    MagazineRequestList,
    MagazineRequestRecord,
)
from app.services.auth_service import authorization_is_valid
from app.services.magazine_request_service import create_magazine_request, list_magazine_requests

router = APIRouter(tags=["magazine-requests"])


def require_admin(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization_is_valid(authorization or ""):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/api/magazine-requests", response_model=MagazineRequestRecord)
def post_magazine_request(body: MagazineRequestCreate) -> MagazineRequestRecord:
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
