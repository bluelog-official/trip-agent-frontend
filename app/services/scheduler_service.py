"""매일 도시 하나를 골라 가이드를 만들고 sitemap을 갱신한다."""

import asyncio
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse
from xml.sax.saxutils import escape

import requests
from dotenv import load_dotenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.agents.marketing_agent import run_marketing_pipeline
from app.agents.research_agent import run_research_agent
from app.agents.writer_agent import run_writer_agent
from app.schemas.guide_schema import GenerateResponse
from app.services.guide_service import (
    _MIN_APPROVED_SCORE,
    build_generate_response,
    build_guide_id,
    format_seoul_stamp,
    inject_guide_images,
    load_approved_ids,
    mark_guide_approved,
    save_guide,
)
from app.services.keyword_map import resolve_city_keywords
from app.services.magazine_matrix import attach_matrix_frontmatter, resolve_matrix
from app.services.pexels_service import build_image_queries, fetch_guide_images

TARGET_CITIES = [
    "New York",
    "Los Angeles",
    "Toronto",
    "Paris",
    "London",
    "Rome",
    "Barcelona",
    "Tokyo",
    "Singapore",
    "Seoul",
]

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "output"
GUIDES_DIR = ROOT_DIR / "guides"
SITEMAP_PATH = OUTPUT_DIR / "sitemap.xml"
PUBLIC_SITEMAP_PATHS = ("/about", "/contact", "/privacy", "/terms", "/events")
K_CULTURE_SITEMAP_PATHS = (
    "/k-culture",
    "/k-culture/k-food",
    "/k-culture/k-beauty",
    "/k-culture/k-pop",
    "/k-culture/k-trend",
)
STATE_PATH = OUTPUT_DIR / "scheduler_state.json"
GOOGLE_SITEMAP_PING = "http://www.google.com/ping"
_SCRIPT_TAG = re.compile(
    r"<script\b[^>]*/>|<script\b[^>]*>.*?</script>",
    re.IGNORECASE | re.DOTALL,
)
_API_HOSTS = {"127.0.0.1", "0.0.0.0", "::1"}
JOB_ID = "daily_guide_generation"

_scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
_run_lock = asyncio.Lock()
_marketing_guard = threading.Lock()
_marketing_threads: List[threading.Thread] = []
_last_run: Optional[Dict[str, Any]] = None
_batch_running = False
_batch_city = ""
_BATCH_STATUSES = ("SUCCESS", "RUNNING", "FAILED")


def _read_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {"index": 0}
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"index": 0}
    if not isinstance(payload, dict):
        return {"index": 0}
    return payload


def _write_state(index: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"index": index % len(TARGET_CITIES)}, ensure_ascii=False),
        encoding="utf-8",
    )


def _city_guide_exists(destination: str) -> bool:
    return (OUTPUT_DIR / build_guide_id(destination)).is_file()


def select_pending_city() -> Optional[str]:
    """순환 큐에서 아직 가이드 파일이 없는 다음 도시를 고른다."""
    start = int(_read_state().get("index", 0)) % len(TARGET_CITIES)
    for offset in range(len(TARGET_CITIES)):
        city = TARGET_CITIES[(start + offset) % len(TARGET_CITIES)]
        if not _city_guide_exists(city):
            return city
    return None


def peek_next_city() -> str:
    pending = select_pending_city()
    if pending:
        return pending
    index = int(_read_state().get("index", 0)) % len(TARGET_CITIES)
    return TARGET_CITIES[index]


def _advance_past(destination: str) -> None:
    index = TARGET_CITIES.index(destination)
    _write_state((index + 1) % len(TARGET_CITIES))


async def generate_city_guide(
    destination: str,
    keyword: str = "",
    target_language: str = "ko",
    duration: str = "",
    budget: str = "",
) -> GenerateResponse:
    matrix = resolve_matrix(destination, duration, budget)
    profile = resolve_city_keywords(destination, keyword)
    focus_keyword = profile.primary_keyword if profile else keyword
    duration_key = matrix.duration_key if matrix is not None else ""
    budget_key = matrix.budget_key if matrix is not None else ""
    research_data, research_model = await run_research_agent(
        destination, focus_keyword, profile, duration_key, budget_key
    )
    article_markdown, writer_model = await run_writer_agent(
        destination,
        research_data,
        profile,
        target_language=target_language,
        duration=duration_key,
        budget=budget_key,
    )
    section_count = sum(
        1
        for line in article_markdown.splitlines()
        if line.strip().startswith("##") and not line.strip().startswith("###")
    )
    image_limit = min(6, max(section_count + 1, 2))
    queries = build_image_queries(
        destination,
        attractions=research_data.attractions,
        food_spots=research_data.food_spots,
        limit=image_limit,
    )
    images = await fetch_guide_images(destination, queries=queries)
    article_markdown = inject_guide_images(article_markdown, images)
    if matrix is not None:
        article_markdown = attach_matrix_frontmatter(article_markdown, matrix)
        guide_id = matrix.filename
    else:
        guide_id = build_guide_id(destination)
    response = build_generate_response(
        destination=destination,
        article_markdown=article_markdown,
        research_model=research_model,
        writer_model=writer_model,
        research=research_data,
        guide_id=guide_id,
        target_language=target_language,
    )
    save_guide(guide_id, response)
    return response


def save_guide_file(guide_id: str, response: GenerateResponse) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / guide_id
    path.write_text(response.article_markdown, encoding="utf-8")
    return path


def _accept_site_url(raw: str, allow_localhost: bool) -> str:
    """공개 사이트 origin만 남긴다. API 바인드 주소는 sitemap에 넣지 않는다."""
    value = (raw or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = "https://{0}".format(value)
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if not host or not parsed.scheme:
        return ""
    if host in _API_HOSTS or parsed.port == 8000:
        return ""
    if host == "localhost" and not allow_localhost:
        return ""
    return "{0}://{1}".format(parsed.scheme, parsed.netloc).rstrip("/")


def resolve_site_base_url(candidate: str = "") -> str:
    """SITE_URL, VITE_SITE_URL, 그리고 브라우저 origin 순으로 공개 도메인을 고른다."""
    load_dotenv()
    for raw in (os.getenv("SITE_URL", ""), os.getenv("VITE_SITE_URL", ""), candidate):
        cleaned = _accept_site_url(raw, allow_localhost=False)
        if cleaned:
            return cleaned
    return _accept_site_url(candidate, allow_localhost=True)


def strip_script_tags(document: str) -> str:
    """sitemap 응답에 HTML script 태그가 섞여 들어가지 않게 제거한다."""
    return _SCRIPT_TAG.sub("", document or "")


def _sitemap_sources() -> List[Path]:
    """guides 마크다운을 실시간으로 읽고, 승인된 output 가이드만 더한다."""
    found: Dict[str, Path] = {}
    if GUIDES_DIR.is_dir():
        for path in sorted(GUIDES_DIR.glob("*.md")):
            if path.is_file():
                found[path.name] = path
    approved = set(load_approved_ids())
    if OUTPUT_DIR.is_dir():
        for path in sorted(OUTPUT_DIR.glob("*_guide.md")):
            if path.name in approved and path.name not in found:
                found[path.name] = path
    return [found[name] for name in sorted(found)]


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _active_partner_paths() -> List[Dict[str, str]]:
    """승인된 제휴 상점의 공개 경로와 lastmod."""
    try:
        from app.models import rewards as reward_store
        from app.services.rewards_service import db_path

        database = db_path()
        if not database.is_file():
            return []
        conn = reward_store.connect(database)
        try:
            rows = reward_store.fetch_partners(conn, active_only=True)
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 - 상점 DB가 없어도 sitemap은 가이드를 담는다
        return []
    paths: List[Dict[str, str]] = []
    for row in rows:
        try:
            partner_id = int(row.get("id") or 0)
        except (TypeError, ValueError):
            continue
        if partner_id <= 0:
            continue
        lastmod = str(row.get("created_at") or "")[:10]
        paths.append(
            {
                "path": "/partners/{0}".format(partner_id),
                "lastmod": lastmod if len(lastmod) == 10 else _today(),
            }
        )
    return paths


def _sitemap_url(loc: str, changefreq: str, priority: str, lastmod: str = "") -> str:
    """Sitemap protocol url 항목을 줄 단위 태그로 만든다."""
    lines = [
        "  <url>",
        "    <loc>{0}</loc>".format(escape(loc)),
    ]
    if lastmod:
        lines.append("    <lastmod>{0}</lastmod>".format(escape(lastmod)))
    lines.extend(
        [
            "    <changefreq>{0}</changefreq>".format(escape(changefreq)),
            "    <priority>{0}</priority>".format(escape(priority)),
            "  </url>",
        ]
    )
    return "\n".join(lines)


def refresh_sitemap(base_url: str = "") -> Path:
    """guides 디렉터리의 마크다운을 표준 Sitemap XML urlset으로 다시 쓴다."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    site_url = resolve_site_base_url(base_url)
    today = _today()
    home = "{0}/".format(site_url) if site_url else "/"
    entries = [_sitemap_url(home, changefreq="daily", priority="1.0", lastmod=today)]
    for public_path in PUBLIC_SITEMAP_PATHS:
        loc = "{0}{1}".format(site_url, public_path) if site_url else public_path
        entries.append(_sitemap_url(loc, changefreq="monthly", priority="0.4", lastmod=today))
    for public_path in K_CULTURE_SITEMAP_PATHS:
        loc = "{0}{1}".format(site_url, public_path) if site_url else public_path
        priority = "0.9" if public_path == "/k-culture" else "0.7"
        entries.append(_sitemap_url(loc, changefreq="weekly", priority=priority, lastmod=today))
    for path in _sitemap_sources():
        lastmod = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).date().isoformat()
        loc = "{0}/guide/{1}".format(site_url, path.name) if site_url else "/guide/{0}".format(path.name)
        entries.append(_sitemap_url(loc, changefreq="weekly", priority="0.8", lastmod=lastmod))
    for partner in _active_partner_paths():
        loc = "{0}{1}".format(site_url, partner["path"]) if site_url else partner["path"]
        entries.append(
            _sitemap_url(loc, changefreq="weekly", priority="0.6", lastmod=partner["lastmod"])
        )
    document = strip_script_tags(
        (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            "{0}\n"
            "</urlset>\n"
        ).format("\n".join(entries))
    )
    SITEMAP_PATH.write_text(document, encoding="utf-8")
    return SITEMAP_PATH


def read_sitemap(site_url: str = "") -> str:
    """요청마다 guides 디렉터리를 다시 읽어 순수 XML을 돌려준다."""
    path = refresh_sitemap(site_url)
    return strip_script_tags(path.read_text(encoding="utf-8"))


def sitemap_public_url(base_url: str = "") -> str:
    site_url = resolve_site_base_url(base_url)
    if not site_url:
        return "/sitemap.xml"
    return "{0}/sitemap.xml".format(site_url.rstrip("/"))


def _request_google_ping(sitemap_url: str) -> requests.Response:
    return requests.get(
        "{0}?sitemap={1}".format(GOOGLE_SITEMAP_PING, quote(sitemap_url, safe="")),
        timeout=10,
    )


async def ping_google_sitemap(sitemap_url: str) -> Dict[str, Any]:
    """sitemap 갱신 이후 구글에 새 sitemap 주소를 비동기로 알린다."""
    ping_url = "{0}?sitemap={1}".format(GOOGLE_SITEMAP_PING, quote(sitemap_url, safe=""))
    try:
        response = await asyncio.to_thread(_request_google_ping, sitemap_url)
        result = {
            "ok": response.status_code < 400,
            "status_code": response.status_code,
            "ping_url": ping_url,
            "sitemap_url": sitemap_url,
        }
        print("🔔 [SEO Ping] Google {0}: {1}".format(response.status_code, ping_url))
        return result
    except Exception as exc:  # noqa: BLE001 - ping 실패가 가이드 저장을 되돌리면 안 된다
        print("⚠️ [SEO Ping] Google sitemap ping 실패: {0}".format(exc))
        return {
            "ok": False,
            "status_code": None,
            "ping_url": ping_url,
            "sitemap_url": sitemap_url,
            "error": str(exc),
        }


async def publish_approved_guide(guide_id: str) -> Dict[str, Any]:
    """사람이 승인한 뒤에만 가이드 파일을 게시하고 sitemap과 Google ping을 보낸다."""
    payload = mark_guide_approved(guide_id)
    if payload is None:
        raise LookupError(guide_id)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_path = OUTPUT_DIR / guide_id
    file_path.write_text(payload.get("article_markdown") or "", encoding="utf-8")
    sitemap_path = refresh_sitemap()
    seo_ping = await ping_google_sitemap(sitemap_public_url())
    try:
        from app.services.rewards_service import award_published_guide

        award_published_guide(guide_id)
    except Exception as exc:  # noqa: BLE001 - 포인트 실패가 발행을 되돌리면 안 된다
        print("⚠️ [Rewards] 발행 포인트 적립 실패: {0}".format(exc))
    published = dict(payload)
    published["status"] = "approved"
    published["file_path"] = str(file_path)
    published["sitemap_path"] = str(sitemap_path)
    published["seo_ping"] = seo_ping
    return published


def _run_marketing_quietly(guide_data: Dict[str, Any]) -> None:
    """채널 실패가 자동 발행 결과를 되돌리지 않게 삼킨다."""
    try:
        run_marketing_pipeline(guide_data)
    except Exception as exc:  # noqa: BLE001 - 홍보 실패는 발행 상태와 분리한다
        print("⚠️ [Marketing] 자동 발행 파이프라인 실패: {0}".format(exc))


def schedule_marketing_pipeline(guide_data: Dict[str, Any]) -> None:
    """QA 자동 승인 직후 홍보 파이프라인을 백그라운드 스레드에서 시작한다."""
    worker = threading.Thread(
        target=_run_marketing_quietly,
        args=(guide_data,),
        name="marketing-pipeline",
        daemon=True,
    )
    with _marketing_guard:
        _marketing_threads.append(worker)
    worker.start()
    print("📣 [Marketing] 자동 발행 홍보 파이프라인 시작: {0}".format(guide_data.get("id")))


def join_marketing_pipelines(timeout: float = 30.0) -> None:
    """시작된 홍보 스레드가 초안을 남길 때까지 기다린다."""
    with _marketing_guard:
        workers = list(_marketing_threads)
    for worker in workers:
        if worker.is_alive():
            worker.join(timeout)
    with _marketing_guard:
        _marketing_threads[:] = [worker for worker in _marketing_threads if worker.is_alive()]


async def run_daily_auto_generation() -> Dict[str, Any]:
    """아직 없는 도시 가이드를 만들고, QA 75점 이상이면 승인 후 sitemap을 갱신한다."""
    global _last_run, _batch_running, _batch_city
    async with _run_lock:
        destination = select_pending_city()
        city = destination or peek_next_city()
        previous = _read_batch_file()
        _batch_running = True
        _batch_city = city
        _write_batch_status(
            "RUNNING",
            city,
            str(previous.get("last_run") or "") or format_seoul_stamp(),
        )
        try:
            result = await _execute_daily_auto_generation(destination)
        except Exception:
            _write_batch_status("FAILED", city, format_seoul_stamp())
            raise
        else:
            finished_city = str(result.get("destination") or city)
            _write_batch_status("SUCCESS", finished_city, format_seoul_stamp())
            return result
        finally:
            _batch_running = False
            _batch_city = ""
            await asyncio.to_thread(join_marketing_pipelines)


async def _execute_daily_auto_generation(destination: Optional[str]) -> Dict[str, Any]:
    global _last_run
    if destination is None:
        _last_run = {
            "status": "skipped",
            "published": False,
            "destination": None,
            "reason": "모든 대상 도시의 가이드가 이미 있습니다.",
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        print("🗓️ [Scheduler] 생성할 신규 도시가 없습니다.")
        return dict(_last_run)

    print("🗓️ [Scheduler] {0} 자동 생성 시작".format(destination))
    response = await generate_city_guide(destination)
    guide_id = build_guide_id(destination)
    save_guide(guide_id, response)
    file_path = save_guide_file(guide_id, response)
    qa_result = response.qa_result.model_dump()
    seo_ping = None
    published = False
    if response.qa_result.quality_score >= _MIN_APPROVED_SCORE:
        published_payload = await publish_approved_guide(guide_id)
        published = True
        qa_result = published_payload["qa_result"]
        seo_ping = published_payload.get("seo_ping")
        file_path = Path(published_payload.get("file_path") or file_path)
        schedule_marketing_pipeline(published_payload)
    _advance_past(destination)
    _last_run = {
        "status": "ok",
        "published": published,
        "destination": destination,
        "guide_id": guide_id,
        "file_path": str(file_path),
        "qa_result": qa_result,
        "syndication": response.syndication.model_dump(),
        "research_model": response.research_model,
        "writer_model": response.writer_model,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    if seo_ping is not None:
        _last_run["seo_ping"] = seo_ping
    if published:
        print("🗓️ [Scheduler] {0} 자동 승인 및 sitemap 갱신: {1}".format(destination, file_path))
    else:
        print("🗓️ [Scheduler] {0} QA 미달로 검수 대기 저장: {1}".format(destination, file_path))
    return dict(_last_run)


def start_scheduler() -> None:
    if _scheduler.running:
        return
    _scheduler.add_job(
        run_daily_auto_generation,
        CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),
        id=JOB_ID,
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()


def shutdown_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)


def batch_status_path() -> Path:
    return OUTPUT_DIR / "batch_status.json"


def _read_batch_file() -> Dict[str, Any]:
    path = batch_status_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _write_batch_status(status: str, target_city: str, last_run: str) -> None:
    path = batch_status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "last_run": last_run,
                "status": status,
                "target_city": target_city,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def read_daily_batch_status() -> Dict[str, str]:
    """대시보드용 배치 상태. 프로세스가 죽은 RUNNING 기록은 FAILED로 본다."""
    global _batch_running, _batch_city
    stored = _read_batch_file()
    target = str(stored.get("target_city") or "").strip() or peek_next_city()
    last_run = str(stored.get("last_run") or "")
    if _batch_running:
        return {
            "last_run": last_run or format_seoul_stamp(),
            "status": "RUNNING",
            "target_city": _batch_city or target,
        }
    status = str(stored.get("status") or "SUCCESS")
    if status == "RUNNING":
        status = "FAILED"
    if status not in _BATCH_STATUSES:
        status = "SUCCESS"
    return {
        "last_run": last_run,
        "status": status,
        "target_city": target,
    }


def scheduler_status() -> Dict[str, Any]:
    if not _scheduler.running:
        start_scheduler()
    job = _scheduler.get_job(JOB_ID)
    next_run = None
    if job is not None and job.next_run_time is not None:
        next_run = job.next_run_time.isoformat()
    return {
        "running": _scheduler.running,
        "job_id": JOB_ID,
        "next_run_time": next_run,
        "next_city": peek_next_city(),
        "target_cities": list(TARGET_CITIES),
        "last_run": _last_run,
    }
