"""로그인 사용자의 포인트 지갑."""

from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException

from app.routers.oauth import require_user
from app.schemas.oauth_schema import SavedGuideRequest, WalletView
from app.services.wallet_service import remove_saved_guide, save_guide, wallet_for_user

router = APIRouter(tags=["wallet"])


@router.get("/api/v1/wallet", response_model=WalletView)
def get_wallet(authorization: Optional[str] = Header(default=None)) -> WalletView:
    user = require_user(authorization)
    return WalletView.model_validate(wallet_for_user(user))


@router.post("/api/v1/wallet/saved", response_model=List[str])
def post_saved_guide(
    body: SavedGuideRequest,
    authorization: Optional[str] = Header(default=None),
) -> List[str]:
    user = require_user(authorization)
    try:
        return save_guide(int(user["id"]), body.guide_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="guide_id is invalid") from exc


@router.delete("/api/v1/wallet/saved/{guide_id}", response_model=List[str])
def delete_saved_guide(
    guide_id: str,
    authorization: Optional[str] = Header(default=None),
) -> List[str]:
    user = require_user(authorization)
    return remove_saved_guide(int(user["id"]), guide_id)
