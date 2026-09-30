"""게시글 추천 집계. LLM 의존성 없음. 같은 IP는 글마다 한 표만 남긴다."""

import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models import votes as vote_store
from app.services.globe_service import PERIOD_DAYS, normalize_period

_ROOT_DIR = Path(__file__).resolve().parents[2]
_LOCK = threading.Lock()
_MAX_IDS = 100


def _seoul_timezone():
    try:
        return ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        return timezone.utc


def _now(moment: Optional[datetime] = None) -> datetime:
    zone = _seoul_timezone()
    if moment is None:
        return datetime.now(zone)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=zone)
    return moment.astimezone(zone)


def _stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def db_path() -> Path:
    override = os.getenv("VOTES_DB_PATH", "").strip()
    if override:
        return Path(override)
    return _ROOT_DIR / "output" / "votes.db"


def normalize_article_id(value: str) -> str:
    article_id = str(value or "").strip()
    if not article_id or len(article_id) > 180:
        raise ValueError("article_id")
    return article_id


def normalize_ip(value: str) -> str:
    ip_address = str(value or "").strip()
    if not ip_address:
        return "unknown"
    return ip_address[:80]


def _in_top_ranks(conn, article_id: str, limit: int = 5) -> bool:
    """추천 수가 많은 글 limit개 안에 있으면 True."""
    rows = conn.execute(
        """
        SELECT article_id
        FROM votes
        GROUP BY article_id
        ORDER BY COUNT(*) DESC, article_id ASC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    return article_id in {str(row["article_id"]) for row in rows}


def cast_vote(article_id: str, ip_address: str, created_at: Optional[datetime] = None) -> Dict[str, object]:
    """한 IP가 한 글에 추천을 한 번 저장한다. 이미 있으면 created는 False."""
    article = normalize_article_id(article_id)
    ip_value = normalize_ip(ip_address)
    stamp = _stamp(_now(created_at))
    with _LOCK:
        conn = vote_store.connect(db_path())
        try:
            created = vote_store.insert_vote(conn, article, ip_value, stamp)
            vote_count = vote_store.count_for_article(conn, article)
            ranked = _in_top_ranks(conn, article) if created else False
        finally:
            conn.close()
    if ranked:
        try:
            from app.services.rewards_service import award_top_rank

            award_top_rank(article)
        except Exception as exc:  # noqa: BLE001 - 추천 저장은 포인트 실패와 분리한다
            print("⚠️ [Rewards] 상위 추천 포인트 적립 실패: {0}".format(exc))
    return {
        "article_id": article,
        "vote_count": vote_count,
        "voted": True,
        "created": created,
    }


def vote_statuses(article_ids: Sequence[str], ip_address: str) -> List[Dict[str, object]]:
    """현재 IP 기준으로 글별 추천 수와 투표 여부."""
    cleaned: List[str] = []
    for raw in article_ids:
        article_id = str(raw or "").strip()
        if not article_id or article_id in cleaned:
            continue
        if len(article_id) > 180:
            continue
        cleaned.append(article_id)
        if len(cleaned) >= _MAX_IDS:
            break
    ip_value = normalize_ip(ip_address)
    with _LOCK:
        conn = vote_store.connect(db_path())
        try:
            return vote_store.status_for_articles(conn, cleaned, ip_value)
        finally:
            conn.close()


def counts_for_period(period: str, now: Optional[datetime] = None) -> Dict[str, int]:
    """기간 안에 들어온 추천을 글 id별로 센다. all이면 전체다."""
    key = normalize_period(period)
    days = PERIOD_DAYS[key]
    current = _now(now)
    start = None
    end = None
    if days is not None:
        start = _stamp(current - timedelta(days=days))
        end = _stamp(current)
    with _LOCK:
        conn = vote_store.connect(db_path())
        try:
            return vote_store.counts_between(conn, start, end)
        finally:
            conn.close()
