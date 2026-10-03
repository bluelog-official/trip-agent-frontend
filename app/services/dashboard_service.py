"""관리자 대시보드 집계. LLM을 호출하지 않는다."""

from typing import Any, Dict

from app.services.guide_service import approve_all_pending_guides, list_guide_records
from app.services.marketing_service import list_marketing_alerts
from app.services.scheduler_service import read_daily_batch_status

_AGENT_MODULES = (
    ("research_agent", "app.agents.research_agent"),
    ("writer_agent", "app.agents.writer_agent"),
    ("qa_agent", "app.services.guide_service"),
    ("syndication_agent", "app.agents.syndication_agent"),
)


def agent_health() -> Dict[str, str]:
    """파이프라인 모듈을 불러올 수 있으면 OK, 아니면 ERROR."""
    health: Dict[str, str] = {}
    for name, module_name in _AGENT_MODULES:
        try:
            __import__(module_name)
        except Exception:  # noqa: BLE001 - 헬스체크는 원인과 무관하게 실패만 표시한다
            health[name] = "ERROR"
        else:
            health[name] = "OK"
    return health


def build_dashboard_stats() -> Dict[str, Any]:
    """대기 가이드를 승인한 뒤 발행본과 검수 대기 수를 나눈다."""
    approve_all_pending_guides()
    guides = list_guide_records()
    approved_count = sum(1 for guide in guides if guide.get("is_approved"))
    pending_count = sum(1 for guide in guides if not guide.get("is_approved"))
    return {
        "total_guides_count": len(guides),
        "approved_count": approved_count,
        "pending_count": pending_count,
        "daily_batch_status": read_daily_batch_status(),
        "agent_health": agent_health(),
        "recent_guides": guides[:10],
        "marketing_alerts": list_marketing_alerts(limit=20),
    }
