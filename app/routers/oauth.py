"""소셜 로그인. NextAuth가 쓰는 /api/auth 경로를 FastAPI에서 연다."""

from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.core.limiter import limiter

from app.schemas.oauth_schema import AuthProviderList, OAuthStart, UserSession
from app.services.oauth_service import (
    OAuthExchangeError,
    authorize_url,
    complete_social_login,
    fetch_provider_profile,
    frontend_base,
    provider_catalog,
    provider_configured,
    public_session,
    read_oauth_state,
    redirect_uri,
    session_user,
    wallet_redirect,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def require_user(authorization: Optional[str] = Header(default=None)) -> dict:
    user = session_user(authorization or "")
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _request_base(request: Request) -> str:
    configured = request.base_url
    return str(configured).rstrip("/")


@router.get("/providers", response_model=AuthProviderList)
def get_providers() -> AuthProviderList:
    return AuthProviderList.model_validate({"providers": provider_catalog()})


@router.get("/session", response_model=UserSession)
def get_session(authorization: Optional[str] = Header(default=None)) -> UserSession:
    user = require_user(authorization)
    return UserSession.model_validate(public_session(user))


@router.get("/signin/{provider}", response_model=OAuthStart)
@limiter.limit("10/minute")
def start_signin(provider: str, request: Request) -> OAuthStart:
    if provider not in ("google", "apple", "kakao"):
        raise HTTPException(status_code=404, detail="unknown provider")
    if not provider_configured(provider):
        raise HTTPException(status_code=503, detail="provider is not configured")
    return OAuthStart(provider=provider, authorize_url=authorize_url(provider, _request_base(request)))


@router.api_route("/callback/{provider}", methods=["GET", "POST"])
async def oauth_callback(provider: str, request: Request) -> RedirectResponse:
    if provider not in ("google", "apple", "kakao"):
        raise HTTPException(status_code=404, detail="unknown provider")
    if request.method == "POST":
        form = await request.form()
        code = str(form.get("code") or "")
        state = str(form.get("state") or "")
        user_json = str(form.get("user") or "")
    else:
        code = str(request.query_params.get("code") or "")
        state = str(request.query_params.get("state") or "")
        user_json = ""
    if not code or not read_oauth_state(state, provider):
        raise HTTPException(status_code=400, detail="invalid oauth state")
    try:
        profile = fetch_provider_profile(
            provider,
            code,
            redirect_uri(provider, _request_base(request)),
            user_json,
        )
        session = complete_social_login(
            provider,
            str(profile.get("email") or ""),
            str(profile.get("subject") or ""),
            str(profile.get("name") or ""),
        )
    except OAuthExchangeError as exc:
        raise HTTPException(status_code=502, detail="provider sign-in failed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="profile did not include an email") from exc
    target = wallet_redirect(str(session["access_token"]))
    allowed = urlparse(frontend_base())
    landed = urlparse(target)
    if landed.scheme != allowed.scheme or landed.netloc != allowed.netloc:
        raise HTTPException(status_code=500, detail="redirect target was rejected")
    return RedirectResponse(target, status_code=303)
