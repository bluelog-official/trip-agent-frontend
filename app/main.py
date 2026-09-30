"""FastAPI 컨트롤러: 라우팅과 HTTP 예외 처리만 담당한다."""

import hashlib
import os
import secrets
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import enforce_production_secrets
from app.core.limiter import limiter

from app.agents.marketing_agent import run_marketing_pipeline
from app.routers.magazine_requests import router as magazine_router
from app.routers.oauth import router as oauth_router
from app.routers.partners import router as partners_router
from app.routers.rewards import router as rewards_router
from app.routers.vouchers import router as vouchers_router
from app.routers.stats import router as stats_router
from app.routers.votes import router as vote_router
from app.routers.wallet import router as wallet_router
from app.schemas.auth_schema import AdminLoginRequest, AdminLoginResponse
from app.schemas.dashboard_schema import DashboardStats
from app.schemas.globe_schema import GlobeMapResponse
from app.schemas.guide_schema import GenerateRequest, GenerateResponse
from app.services.auth_service import admin_password, authenticate_admin, authorization_is_valid
from app.services.dashboard_service import build_dashboard_stats
from app.services.globe_service import build_globe_map
from app.services.vote_service import counts_for_period
from app.services.marketing_service import dismiss_marketing_alert
from app.services.guide_service import get_guide, list_guides
from app.services.opengraph_service import render_opengraph_html
from app.services.scheduler_service import (
    generate_city_guide,
    publish_approved_guide,
    read_sitemap,
    run_daily_auto_generation,
    scheduler_status,
    shutdown_scheduler,
    start_scheduler,
)
from app.services.seo_files import ads_txt_body, robots_txt_body

load_dotenv()
enforce_production_secrets()

DEFAULT_SITE_URL = "https://bluelogtrip.com"
SITE_URL = os.getenv("SITE_URL", DEFAULT_SITE_URL).strip().rstrip("/") or DEFAULT_SITE_URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()


def _origin(value: str) -> str:
    raw = (value or "").strip().rstrip("/")
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://{0}".format(raw)
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return "{0}://{1}".format(parsed.scheme, parsed.netloc)


def _cors_allow_origins(site_url: str, frontend_url: str = "") -> List[str]:
    """로컬 개발, FRONTEND_URL, SITE_URL, bluelogtrip.com만 허용한다."""
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        _origin(frontend_url),
        _origin(site_url),
        _origin(DEFAULT_SITE_URL),
        "https://bluelogtrip.com",
        "https://www.bluelogtrip.com",
    ]
    for candidate in (_origin(frontend_url), _origin(site_url), _origin(DEFAULT_SITE_URL)):
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
        if not host or host in ("localhost", "127.0.0.1"):
            continue
        if host.startswith("www."):
            origins.append("{0}://{1}".format(parsed.scheme, host[4:]))
        else:
            origins.append("{0}://www.{1}".format(parsed.scheme, host))
    unique: List[str] = []
    for origin in origins:
        if origin and origin != "*" and origin not in unique:
            unique.append(origin)
    return unique


class SecurityHeadersMiddleware:
    """클릭재킹, MIME 스니핑, 리퍼러, 기능 정책, HSTS를 모든 HTTP 응답에 붙인다."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Frame-Options"] = "DENY"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="BlueLog AdSense Engine - AI Agents", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(stats_router)
app.include_router(magazine_router)
app.include_router(vote_router)
app.include_router(rewards_router)
app.include_router(oauth_router)
app.include_router(wallet_router)
app.include_router(partners_router)
app.include_router(vouchers_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(SITE_URL, FRONTEND_URL),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)


def _passwords_match(provided: str, expected: str) -> bool:
    """같은 길이의 SHA-256 다이제스트를 상수 시간에 비교한다."""
    left = hashlib.sha256((provided or "").encode("utf-8")).digest()
    right = hashlib.sha256((expected or "").encode("utf-8")).digest()
    return secrets.compare_digest(left, right)


def _configured_admin_password() -> str:
    configured = os.getenv("ADMIN_PASSWORD")
    if configured:
        return configured
    return admin_password()


def require_admin(authorization: Optional[str] = Header(default=None)) -> None:
    """Authorization: Bearer 토큰이 없거나 유효하지 않으면 401을 반환한다."""
    if not authorization_is_valid(authorization or ""):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post("/api/v1/admin/login", response_model=AdminLoginResponse)
async def admin_login(body: AdminLoginRequest) -> AdminLoginResponse:
    expected_password = _configured_admin_password()
    password_ok = _passwords_match(body.password, expected_password)
    token = authenticate_admin(body.username, body.password)
    if not password_ok or not token:
        raise HTTPException(status_code=401, detail="잘못된 관리자 정보입니다")
    return AdminLoginResponse(access_token=token)


@app.get(
    "/api/v1/admin/dashboard-stats",
    response_model=DashboardStats,
    dependencies=[Depends(require_admin)],
)
async def get_dashboard_stats() -> DashboardStats:
    return DashboardStats.model_validate(build_dashboard_stats())


@app.delete(
    "/api/v1/admin/marketing-alerts/{alert_id}",
    dependencies=[Depends(require_admin)],
)
async def dismiss_marketing_alert_route(alert_id: int) -> Dict[str, Any]:
    """확인한 Reddit 초안을 대시보드 목록에서 제거한다."""
    if not dismiss_marketing_alert(alert_id):
        raise HTTPException(status_code=404, detail="마케팅 알림을 찾을 수 없습니다.")
    return {"ok": True, "id": alert_id}


@app.post(
    "/api/v1/generate-guide",
    response_model=GenerateResponse,
    dependencies=[Depends(require_admin)],
)
async def generate_guide(req: GenerateRequest) -> GenerateResponse:
    try:
        return await generate_city_guide(
            req.destination,
            req.keyword,
            req.target_language,
            duration=req.duration,
            budget=req.budget,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - 에이전트 실패를 HTTP 오류로 변환
        print("❌ [오류] 가이드 생성 실패: {0}".format(exc))
        raise HTTPException(status_code=500, detail="가이드 생성 중 오류 발생: {0}".format(exc))


@app.post("/api/v1/cron/trigger", dependencies=[Depends(require_admin)])
async def trigger_daily_generation() -> Dict[str, Any]:
    try:
        return await run_daily_auto_generation()
    except Exception as exc:  # noqa: BLE001 - 스케줄 실행 실패를 HTTP 오류로 변환
        print("❌ [오류] 자동 생성 실패: {0}".format(exc))
        raise HTTPException(status_code=500, detail="자동 생성 중 오류 발생: {0}".format(exc))


@app.get("/api/v1/cron/status")
async def get_cron_status() -> Dict[str, Any]:
    return scheduler_status()


@app.get("/ads.txt", include_in_schema=False)
@app.get("/api/ads.txt", include_in_schema=False)
async def get_ads_txt() -> Response:
    return Response(
        content=ads_txt_body(),
        media_type="text/plain",
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/robots.txt", include_in_schema=False)
@app.get("/api/robots.txt", include_in_schema=False)
async def get_robots_txt() -> Response:
    return Response(
        content=robots_txt_body(SITE_URL),
        media_type="text/plain",
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/api/v1/opengraph", include_in_schema=False)
async def get_opengraph(
    path: str = Query(default="/"),
    site: str = Query(default=""),
) -> Response:
    html = render_opengraph_html(path, site or SITE_URL)
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "public, max-age=300",
            "X-Robots-Tag": "noindex",
        },
    )


@app.get("/sitemap.xml", include_in_schema=False)
@app.get("/api/v1/sitemap.xml")
async def get_sitemap(request: Request) -> Response:
    site_url = request.headers.get("x-site-url", "").strip() or SITE_URL
    xml = read_sitemap(site_url)
    return Response(
        content=xml,
        media_type="application/xml",
        headers={
            "Content-Type": "application/xml; charset=utf-8",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        },
    )


@app.get("/api/v1/globe/cities", response_model=GlobeMapResponse)
async def get_globe_cities(period: str = Query(default="all")) -> GlobeMapResponse:
    """기간 안에 작성된 가이드의 도시 좌표, 건수, 순위, 키워드. 순위는 IP 추천 수가 먼저다."""
    try:
        payload = build_globe_map(period, vote_counts=counts_for_period(period))
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown globe period")
    return GlobeMapResponse.model_validate(payload)


@app.get("/api/v1/guides")
async def get_guides_list() -> List[Dict[str, Any]]:
    return list_guides()


@app.get("/api/v1/guides/{guide_id}")
async def get_guide_detail(guide_id: str) -> Dict[str, Any]:
    return get_guide(guide_id)


@app.post("/api/v1/guides/{guide_id}/approve", dependencies=[Depends(require_admin)])
async def approve_guide(guide_id: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    try:
        published = await publish_approved_guide(guide_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="가이드를 찾을 수 없습니다.")
    except Exception as exc:  # noqa: BLE001 - 게시 실패를 HTTP 오류로 변환
        print("❌ [오류] 가이드 승인 실패: {0}".format(exc))
        raise HTTPException(status_code=500, detail="가이드 승인 중 오류 발생: {0}".format(exc))
    background_tasks.add_task(run_marketing_pipeline, published)
    return published


@app.get("/guides")
async def get_guides_list_root() -> List[Dict[str, Any]]:
    return list_guides()


@app.get("/guides/{guide_id}")
async def get_guide_detail_root(guide_id: str) -> Dict[str, Any]:
    return get_guide(guide_id)
