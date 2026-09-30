"""IP 기준 요청 제한. 테스트 수집 중에는 꺼 두고, 서버 기동 시에는 켠다."""

import sys

from fastapi import Request
from slowapi import Limiter

def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


limiter = Limiter(
    key_func=client_ip,
    enabled="pytest" not in sys.modules,
    headers_enabled=False,
    storage_uri="memory://",
)
