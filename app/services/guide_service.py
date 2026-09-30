"""가이드 응답 조립, 휴먼 리뷰 상태, 조회용 순수 로직 (LLM 의존성 없음)."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.agents.syndication_agent import run_syndication_agent
from app.schemas.guide_schema import (
    GenerateResponse,
    QAOutput,
    ResearchOutput,
    SyndicationOutput,
)
from app.services.magazine_matrix import parse_matrix_guide_id

# 프론트엔드 GET 요청 시 데이터를 유지하기 위한 메모리 DB
_GUIDE_STORE: Dict[str, Dict[str, Any]] = {}
_ROOT_DIR = Path(__file__).resolve().parents[2]
_OUTPUT_DIR = _ROOT_DIR / "output"
_GUIDES_DIR = _ROOT_DIR / "guides"

_MIN_APPROVED_SCORE = 75


def _seoul_timezone():
    try:
        return ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        return timezone.utc


_SEOUL_TZ = _seoul_timezone()


def format_seoul_stamp(moment: Optional[datetime] = None) -> str:
    """대시보드에 보여줄 분 단위 시각. Asia/Seoul 기준 YYYY-MM-DD HH:MM."""
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(_SEOUL_TZ).strftime("%Y-%m-%d %H:%M")


def city_label(guide_id: str) -> str:
    parsed = parse_matrix_guide_id(guide_id)
    if parsed is not None:
        return parsed.city
    stem = guide_id
    suffix = "_guide.md"
    if stem.endswith(suffix):
        stem = stem[: -len(suffix)]
    label = stem.replace("_", " ").strip().title()
    return label or guide_id


def build_guide_id(destination: str) -> str:
    return "{0}_guide.md".format(destination.strip().lower().replace(" ", "_"))


def evaluate_article(article_markdown: str) -> QAOutput:
    """마크다운 구조를 규칙 기반으로 점검한다(AdSense 최소 품질 게이트)."""
    violations: List[str] = []
    score = 100

    if "##" not in article_markdown:
        violations.append("H2 이상의 소제목이 없습니다.")
        score -= 15
    if "|" not in article_markdown:
        violations.append("비용 비교용 마크다운 표가 없습니다.")
        score -= 15
    if len(article_markdown) < 500:
        violations.append("본문 분량이 500자 미만입니다.")
        score -= 20

    score = max(0, min(100, score))
    return QAOutput(
        is_approved=score >= _MIN_APPROVED_SCORE,
        quality_score=score,
        violations=violations,
    )


def _is_h2(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("##") and not stripped.startswith("###")


def _image_lines(image: Dict[str, str]) -> List[str]:
    alt = (image.get("alt") or "travel").replace("]", "").replace("[", "")
    lines = ["![{0}]({1})".format(alt, image["url"])]
    photographer = (image.get("photographer") or "").strip()
    if not photographer:
        return lines
    page = (image.get("photographer_url") or "").strip()
    if page:
        lines.append("*Photo by [{0}]({1})*".format(photographer, page))
    else:
        lines.append("*Photo by {0}*".format(photographer))
    return lines


def _split_h2_sections(lines: List[str]):
    preamble: List[str] = []
    sections: List[List[str]] = []
    current: Optional[List[str]] = None
    for line in lines:
        if _is_h2(line):
            if current is not None:
                sections.append(current)
            current = [line]
            continue
        if current is None:
            preamble.append(line)
        else:
            current.append(line)
    if current is not None:
        sections.append(current)
    return preamble, sections


def inject_guide_images(markdown: str, images: List[Dict[str, str]]) -> str:
    """문서 맨 위에 썸네일을 넣고, 각 H2 섹션 하단에 이미지를 한 장씩 붙인다."""
    usable = [image for image in images if image.get("url")]
    if not usable or not markdown:
        return markdown

    thumbnail = usable[0]
    section_images = usable[1:] or usable
    preamble, sections = _split_h2_sections(markdown.splitlines())
    chunks: List[str] = []
    chunks.extend(_image_lines(thumbnail))
    chunks.append("")
    if any(line.strip() for line in preamble):
        chunks.extend(preamble)
        if preamble and preamble[-1].strip():
            chunks.append("")

    if not sections:
        return "\n".join(chunks).strip() + "\n"

    for index, section in enumerate(sections):
        chunks.extend(section)
        chunks.append("")
        chunks.extend(_image_lines(section_images[index % len(section_images)]))
        chunks.append("")
    return "\n".join(chunks).strip() + "\n"


def inject_images_below_h2(markdown: str, images: List[Dict[str, str]], limit: int = 2) -> str:
    """앞쪽 H2 바로 아래에 이미지 마크다운을 최대 limit장 넣는다."""
    return inject_guide_images(markdown, [image for image in images if image.get("url")][:limit])


def build_syndication(
    destination: str,
    research: Optional[ResearchOutput] = None,
    guide_id: str = "",
    target_language: str = "ko",
    article_markdown: str = "",
) -> SyndicationOutput:
    return run_syndication_agent(
        destination,
        research,
        guide_id or build_guide_id(destination),
        target_language=target_language,
        article_markdown=article_markdown,
    )


def build_generate_response(
    destination: str,
    article_markdown: str,
    research_model: str,
    writer_model: str,
    research: Optional[ResearchOutput] = None,
    guide_id: str = "",
    target_language: str = "ko",
) -> GenerateResponse:
    """생성 직후 가이드는 검수 전이다. is_approved는 승인 API에서만 True가 된다."""
    qa_result = evaluate_article(article_markdown).model_copy(update={"is_approved": False})
    return GenerateResponse(
        article_markdown=article_markdown,
        qa_result=qa_result,
        syndication=build_syndication(
            destination,
            research,
            guide_id,
            target_language,
            article_markdown=article_markdown,
        ),
        research_model=research_model,
        writer_model=writer_model,
    )


def save_guide(guide_id: str, response: GenerateResponse) -> None:
    _GUIDE_STORE[guide_id] = response.model_dump()


def _approvals_path() -> Path:
    return _OUTPUT_DIR / "approved_guides.json"


def load_approved_ids() -> List[str]:
    path = _approvals_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, str)]


def _write_approved_ids(guide_ids: List[str]) -> None:
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _approvals_path().write_text(
        json.dumps(guide_ids, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _guide_file_path(guide_id: str) -> Optional[Path]:
    name = Path(guide_id).name
    if name != guide_id:
        return None
    for directory in (_GUIDES_DIR, _OUTPUT_DIR):
        path = directory / name
        if path.is_file():
            return path
    return None


def read_guide_markdown(guide_id: str) -> str:
    """저장된 가이드 마크다운. 없으면 빈 문자열."""
    path = _guide_file_path(guide_id)
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _iter_guide_files() -> List[Path]:
    seen = set()
    found: List[Path] = []
    for directory in (_GUIDES_DIR, _OUTPUT_DIR):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*_guide.md")):
            if path.name in seen:
                continue
            seen.add(path.name)
            found.append(path)
    return found


def _published_on(guide_id: str) -> str:
    path = _guide_file_path(guide_id)
    if path is not None:
        moment = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    else:
        moment = datetime.now(timezone.utc)
    return moment.date().isoformat()


def _with_review_state(guide_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(payload)
    qa_result = dict(result.get("qa_result") or {})
    qa_result["is_approved"] = guide_id in load_approved_ids()
    result["qa_result"] = qa_result
    result["id"] = guide_id
    result["content"] = result.get("article_markdown", "")
    result["published_at"] = result.get("published_at") or _published_on(guide_id)
    return result


def _summary(guide_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": guide_id,
        "research_model": payload.get("research_model", "Unknown"),
        "writer_model": payload.get("writer_model", "Unknown"),
        "quality_score": payload.get("qa_result", {}).get("quality_score", 0),
    }


def _payload_from_file(guide_id: str) -> Optional[Dict[str, Any]]:
    path = _guide_file_path(guide_id)
    if path is None:
        return None
    article = path.read_text(encoding="utf-8")
    destination = city_label(guide_id)
    return build_generate_response(
        destination=destination,
        article_markdown=article,
        research_model="file",
        writer_model="file",
        guide_id=guide_id,
    ).model_dump()


def _guide_record(
    guide_id: str,
    qa_score: int,
    is_approved: bool,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    source = path if path is not None else _guide_file_path(guide_id)
    if source is not None:
        moment = datetime.fromtimestamp(source.stat().st_mtime, tz=timezone.utc)
    else:
        moment = datetime.now(timezone.utc)
    return {
        "filename": guide_id,
        "city": city_label(guide_id),
        "qa_score": int(qa_score),
        "created_at": format_seoul_stamp(moment),
        "is_approved": bool(is_approved),
    }


def list_guide_records() -> List[Dict[str, Any]]:
    """전체 가이드의 파일명, 도시, QA 점수, 생성 시각, 승인 여부. 최신순."""
    approved = set(load_approved_ids())
    records: List[Dict[str, Any]] = []
    seen = set()
    for guide_id, payload in _GUIDE_STORE.items():
        seen.add(guide_id)
        qa = payload.get("qa_result") or {}
        try:
            score = int(qa.get("quality_score") or 0)
        except (TypeError, ValueError):
            score = 0
        records.append(_guide_record(guide_id, score, guide_id in approved))
    for path in _iter_guide_files():
        if path.name in seen:
            continue
        try:
            article = path.read_text(encoding="utf-8")
        except OSError:
            continue
        score = evaluate_article(article).quality_score
        records.append(_guide_record(path.name, score, path.name in approved, path))
    records.sort(key=lambda item: (item["created_at"], item["filename"]), reverse=True)
    return records


def list_guides() -> List[Dict[str, Any]]:
    items = [_summary(guide_id, payload) for guide_id, payload in _GUIDE_STORE.items()]
    seen = {item["id"] for item in items}
    for path in _iter_guide_files():
        if path.name in seen:
            continue
        payload = _payload_from_file(path.name)
        if payload is not None:
            items.append(_summary(path.name, payload))
    return items


def get_guide(guide_id: str) -> Dict[str, Any]:
    """저장된 가이드를 반환하고, 없으면 파일 또는 플레이스홀더를 준다."""
    payload = _GUIDE_STORE.get(guide_id)
    if payload is None:
        payload = _payload_from_file(guide_id)
    if payload is not None:
        return _with_review_state(guide_id, payload)

    destination = city_label(guide_id)
    fallback_markdown = "## {0} 가이드\n\n데이터를 찾을 수 없습니다.".format(destination)
    return {
        "id": guide_id,
        "article_markdown": fallback_markdown,
        "content": fallback_markdown,
        "qa_result": {"is_approved": False, "quality_score": 0, "violations": ["생성된 데이터가 없습니다."]},
        "syndication": {
            "social_teasers": [],
            "platform_hashtags": [],
            "reddit": {"subreddit": "", "title": "", "body": ""},
            "quora": {"question": "", "answer": ""},
            "pinterest": {"board": "", "pin_title": "", "description": "", "image_alt": ""},
            "backlink": {"anchor_text": "", "target_path": "", "outreach_note": ""},
        },
        "research_model": "None",
        "writer_model": "None",
        "published_at": _published_on(guide_id),
    }


def mark_guide_approved(guide_id: str) -> Optional[Dict[str, Any]]:
    """검수가 끝난 가이드의 is_approved를 True로 저장한다. 없으면 None."""
    if Path(guide_id).name != guide_id:
        return None
    payload = _GUIDE_STORE.get(guide_id)
    if payload is None:
        payload = _payload_from_file(guide_id)
    if payload is None:
        return None

    approved_ids = load_approved_ids()
    if guide_id not in approved_ids:
        approved_ids.append(guide_id)
        _write_approved_ids(approved_ids)

    stored = dict(payload)
    qa_result = dict(stored.get("qa_result") or {})
    qa_result["is_approved"] = True
    stored["qa_result"] = qa_result
    stored.pop("id", None)
    stored.pop("content", None)
    _GUIDE_STORE[guide_id] = stored
    return _with_review_state(guide_id, stored)
