"""포인트 적립 API. 발행과 상위 추천은 서비스가 직접 호출하고, 이 라우트는 같은 적립을 연다."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.schemas.rewards_schema import PointAccrualRequest, PointLogRecord, RewardsOverview
from app.services.auth_service import authorization_is_valid
from app.services.rewards_service import accrue_points, overview

router = APIRouter(tags=["rewards"])


def require_admin(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization_is_valid(authorization or ""):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/api/v1/rewards/overview", response_model=RewardsOverview)
def get_rewards_overview() -> RewardsOverview:
    return RewardsOverview.model_validate(overview())


@router.post(
    "/api/v1/rewards/accrue",
    response_model=PointLogRecord,
    dependencies=[Depends(require_admin)],
)
def post_accrue(body: PointAccrualRequest) -> PointLogRecord:
    record = accrue_points(body.email, body.reason, body.article_id, body.auth_provider)
    if record is None:
        raise HTTPException(status_code=400, detail="email and reason are required")
    return PointLogRecord.model_validate(record)
