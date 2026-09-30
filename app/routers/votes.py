"""게시글 추천 HTTP 라우트. 집계는 vote_service에 둔다."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.vote_schema import VoteCreate, VoteStatusList
from app.services.vote_service import cast_vote, vote_statuses

router = APIRouter(tags=["votes"])


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/api/votes")
def post_vote(body: VoteCreate, request: Request) -> JSONResponse:
    """같은 IP는 글마다 한 번만 추천할 수 있다. 중복이면 409."""
    result = cast_vote(body.article_id, client_ip(request))
    status = 201 if result["created"] else 409
    if not result["created"]:
        result = dict(result)
        result["detail"] = "Already voted from this IP"
    return JSONResponse(status_code=status, content=result)


@router.get("/api/votes", response_model=VoteStatusList)
def get_votes(
    request: Request,
    article_id: str = "",
    article_ids: str = "",
) -> VoteStatusList:
    ids = []
    if article_id.strip():
        ids.append(article_id.strip())
    ids.extend(part.strip() for part in article_ids.split(",") if part.strip())
    payload = vote_statuses(ids, client_ip(request))
    return VoteStatusList.model_validate({"votes": payload})
