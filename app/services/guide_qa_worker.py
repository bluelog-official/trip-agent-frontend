"""가이드 QA 점수와 95% 이상 유사 쌍을 guides.db에 기록한다.

승인 상태, 공개 여부, 리다이렉트 칼럼은 읽지도 쓰지도 않는다.
"""

import os
import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from app.models.guides import apply_migration, connect, db_path
from app.services.qa_engine import score_article
from app.services.similarity_worker import SIMILARITY_THRESHOLD, pairwise_similarity


_ROOT = Path(__file__).resolve().parents[2]
_CITY_LINE = re.compile(r'(?im)^city:\s*"?([^"\n]+?)"?\s*$')
_FRONT_BLOCK = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---")
_populate_lock = threading.Lock()
_worker_started = False
_worker_guard = threading.Lock()


@dataclass(frozen=True)
class GuideText:
    slug: str
    city: str
    markdown: str


def iter_guide_files() -> List[Path]:
    """guides/를 먼저 보고, 거기에 없는 파일만 output/에서 가져온다."""
    seen = set()
    found: List[Path] = []
    for directory in (_ROOT / "guides", _ROOT / "output"):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*_guide.md")):
            if path.name in seen:
                continue
            seen.add(path.name)
            found.append(path)
    return found


def city_of(markdown: str, slug: str) -> str:
    match = _FRONT_BLOCK.match(markdown or "")
    if match:
        city = _CITY_LINE.search(match.group(1))
        if city:
            value = city.group(1).strip()
            if value:
                return value
    stem = slug[: -len("_guide.md")] if slug.endswith("_guide.md") else slug
    label = stem.replace("_", " ").strip().title()
    return label or slug


def load_live_articles() -> List[GuideText]:
    articles: List[GuideText] = []
    for path in iter_guide_files():
        try:
            markdown = path.read_text(encoding="utf-8")
        except OSError:
            continue
        articles.append(GuideText(slug=path.name, city=city_of(markdown, path.name), markdown=markdown))
    return articles


def _column_names(conn: sqlite3.Connection, table: str) -> List[str]:
    return [str(row[1]) for row in conn.execute("PRAGMA table_info({0})".format(table))]


def ensure_catalog_columns(conn: sqlite3.Connection) -> None:
    """slug와 city만 보강한다. 상태·공개·리다이렉트 칼럼은 만들지 않는다."""
    existing = set(_column_names(conn, "guides"))
    if "slug" not in existing:
        conn.execute("ALTER TABLE guides ADD COLUMN slug TEXT")
    if "city" not in existing:
        conn.execute("ALTER TABLE guides ADD COLUMN city TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS guides_slug_idx ON guides(slug)")


def _upsert_score(conn: sqlite3.Connection, article: GuideText) -> int:
    result = score_article(article.markdown)
    row = conn.execute("SELECT id FROM guides WHERE slug = ?", (article.slug,)).fetchone()
    values = (
        article.city,
        int(result.qa_score),
        result.rating_grade,
        float(result.star_rating),
        result.qa_reason,
    )
    if row is not None:
        conn.execute(
            """
            UPDATE guides
            SET city = ?, qa_score = ?, rating_grade = ?, star_rating = ?, qa_reason = ?
            WHERE id = ?
            """,
            values + (int(row["id"]),),
        )
        return int(row["id"])
    cursor = conn.execute(
        """
        INSERT INTO guides (slug, city, qa_score, rating_grade, star_rating, qa_reason)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (article.slug,) + values,
    )
    return int(cursor.lastrowid)


def _replace_similarities(
    conn: sqlite3.Connection,
    slug_to_id: Dict[str, int],
    articles: Sequence[GuideText],
) -> int:
    scanned = [slug_to_id[article.slug] for article in articles if article.slug in slug_to_id]
    if scanned:
        marks = ", ".join("?" for _item in scanned)
        conn.execute(
            "DELETE FROM guide_similarities WHERE source_guide_id IN ({0}) AND target_guide_id IN ({0})".format(
                marks
            ),
            tuple(scanned + scanned),
        )
    pairs = pairwise_similarity(
        [(article.slug, article.markdown) for article in articles],
        threshold=SIMILARITY_THRESHOLD,
    )
    stored = 0
    for pair in pairs:
        source_id = slug_to_id.get(pair.source_key)
        target_id = slug_to_id.get(pair.target_key)
        if source_id is None or target_id is None or source_id == target_id:
            continue
        if source_id > target_id:
            source_id, target_id = target_id, source_id
        conn.execute(
            """
            INSERT INTO guide_similarities (source_guide_id, target_guide_id, similarity_score)
            VALUES (?, ?, ?)
            """,
            (source_id, target_id, float(pair.similarity_score)),
        )
        stored += 1
    return stored


def populate_connection(conn: sqlite3.Connection, articles: Sequence[GuideText]) -> Dict[str, int]:
    """QA 칼럼과 95% 이상 유사 쌍만 갱신한다. 다른 칼럼은 유지한다."""
    apply_migration(conn)
    ensure_catalog_columns(conn)
    unique: List[GuideText] = []
    seen = set()
    for article in articles:
        if article.slug in seen:
            continue
        seen.add(article.slug)
        unique.append(article)
    conn.execute("BEGIN IMMEDIATE")
    try:
        slug_to_id: Dict[str, int] = {}
        for article in unique:
            slug_to_id[article.slug] = _upsert_score(conn, article)
        stored = _replace_similarities(conn, slug_to_id, unique)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"guides": len(unique), "similarities": stored}


def populate_from_files(path: Optional[Path] = None) -> Dict[str, int]:
    """파일로 있는 가이드를 한 번 읽어 DB에 점수를 채운다."""
    with _populate_lock:
        articles = load_live_articles()
        conn = connect(path or db_path())
        try:
            summary = populate_connection(conn, articles)
        finally:
            conn.close()
    summary["files"] = len(articles)
    return summary


def start_guide_qa_worker() -> None:
    """서버 기동을 막지 않도록 점수 계산을 백그라운드에서 한 번 실행한다."""
    if os.getenv("GUIDE_QA_WORKER", "1").strip().lower() in ("0", "false", "off", "no"):
        return
    global _worker_started
    with _worker_guard:
        if _worker_started:
            return
        _worker_started = True

    def _run() -> None:
        try:
            summary = populate_from_files()
            print(
                "✅ [QA] 가이드 {0}건 점수 기록, 95% 이상 유사 쌍 {1}건".format(
                    summary["guides"],
                    summary["similarities"],
                )
            )
        except Exception as exc:
            print("⚠️ [QA] 점수 작업 실패: {0}".format(exc))

    threading.Thread(target=_run, name="guide-qa-worker", daemon=True).start()
