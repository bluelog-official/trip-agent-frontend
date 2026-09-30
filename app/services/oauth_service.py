"""구글, 애플, 카카오 OAuth와 사용자 세션. LLM 의존성 없음."""

import hashlib
import hmac
import json
import os
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from typing import Dict, Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.services.magazine_request_service import assign_guest_requests
from app.services.rewards_service import link_social_account, load_user


PROVIDERS = ("google", "apple", "kakao")
USER_TOKEN_TTL_SECONDS = 14 * 24 * 60 * 60
STATE_TTL_SECONDS = 10 * 60

_PROVIDER_NAMES = {
    "google": "Google",
    "apple": "Apple",
    "kakao": "Kakao",
}


class OAuthExchangeError(Exception):
    """제공자 토큰 교환이 실패했다."""


def _signing_key() -> bytes:
    secret = (
        os.getenv("OAUTH_TOKEN_SECRET")
        or os.getenv("ADMIN_TOKEN_SECRET")
        or "bluelog-user-session"
    )
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _b64encode(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return urlsafe_b64decode(padded.encode("ascii"))


def _sign(body: str) -> str:
    return hmac.new(_signing_key(), body.encode("ascii"), hashlib.sha256).hexdigest()


def _issue(payload: Dict[str, object]) -> str:
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return "{0}.{1}".format(body, _sign(body))


def _read(token: str) -> Optional[Dict[str, object]]:
    if not token or token.count(".") != 1:
        return None
    body, signature = token.split(".", 1)
    if not body or not signature or not hmac.compare_digest(_sign(body), signature):
        return None
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeError, BinasciiError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        if int(payload.get("exp") or 0) < int(time.time()):
            return None
    except (TypeError, ValueError):
        return None
    return payload


def provider_configured(provider: str) -> bool:
    if provider == "google":
        return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))
    if provider == "apple":
        return bool(os.getenv("APPLE_CLIENT_ID") and os.getenv("APPLE_CLIENT_SECRET"))
    if provider == "kakao":
        return bool(os.getenv("KAKAO_CLIENT_ID"))
    return False


def provider_catalog() -> list:
    return [
        {
            "id": provider,
            "name": _PROVIDER_NAMES[provider],
            "configured": provider_configured(provider),
        }
        for provider in PROVIDERS
    ]


def issue_oauth_state(provider: str, now: Optional[int] = None) -> str:
    issued_at = int(time.time() if now is None else now)
    return _issue({"kind": "state", "prv": provider, "n": secrets.token_hex(8), "exp": issued_at + STATE_TTL_SECONDS})


def read_oauth_state(token: str, provider: str) -> bool:
    payload = _read(token)
    if not payload or payload.get("kind") != "state":
        return False
    return payload.get("prv") == provider


def issue_user_token(user_id: int, email: str, provider: str, now: Optional[int] = None) -> str:
    issued_at = int(time.time() if now is None else now)
    return _issue(
        {
            "kind": "user",
            "uid": int(user_id),
            "sub": email,
            "prv": provider,
            "exp": issued_at + USER_TOKEN_TTL_SECONDS,
        }
    )


def read_user_token(token: str) -> Optional[Dict[str, object]]:
    payload = _read(token)
    if not payload or payload.get("kind") != "user":
        return None
    try:
        int(payload["uid"])
    except (KeyError, TypeError, ValueError):
        return None
    return payload


def bearer_token(authorization: str) -> str:
    if not authorization:
        return ""
    scheme, separator, token = authorization.strip().partition(" ")
    if separator != " " or scheme.lower() != "bearer":
        return ""
    token = token.strip()
    if not token or any(char.isspace() for char in token):
        return ""
    return token


def session_user(authorization: str) -> Optional[Dict[str, object]]:
    payload = read_user_token(bearer_token(authorization))
    if not payload:
        return None
    user = load_user(int(payload["uid"]))
    if not user:
        return None
    return user


def public_api_base(request_base: str) -> str:
    configured = os.getenv("OAUTH_PUBLIC_URL", "").strip().rstrip("/")
    if configured:
        return configured
    return (request_base or "").strip().rstrip("/")


def frontend_base() -> str:
    configured = os.getenv("FRONTEND_URL", "").strip() or os.getenv("SITE_URL", "").strip()
    return (configured or "https://bluelogtrip.com").rstrip("/")


def redirect_uri(provider: str, request_base: str) -> str:
    return "{0}/api/auth/callback/{1}".format(public_api_base(request_base), provider)


def authorize_url(provider: str, request_base: str) -> str:
    state = issue_oauth_state(provider)
    callback = redirect_uri(provider, request_base)
    if provider == "google":
        query = urlencode(
            {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "redirect_uri": callback,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
            }
        )
        return "https://accounts.google.com/o/oauth2/v2/auth?{0}".format(query)
    if provider == "apple":
        query = urlencode(
            {
                "client_id": os.getenv("APPLE_CLIENT_ID", ""),
                "redirect_uri": callback,
                "response_type": "code",
                "response_mode": "form_post",
                "scope": "name email",
                "state": state,
            }
        )
        return "https://appleid.apple.com/auth/authorize?{0}".format(query)
    query = urlencode(
        {
            "client_id": os.getenv("KAKAO_CLIENT_ID", ""),
            "redirect_uri": callback,
            "response_type": "code",
            "state": state,
        }
    )
    return "https://kauth.kakao.com/oauth/authorize?{0}".format(query)


def wallet_redirect(token: str) -> str:
    return "{0}/wallet#session={1}".format(frontend_base(), token)


def _post_form(url: str, data: Dict[str, str]) -> Dict[str, object]:
    body = urlencode(data).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
    except (URLError, TimeoutError, OSError) as exc:
        raise OAuthExchangeError("token exchange failed") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OAuthExchangeError("token exchange failed") from exc
    if not isinstance(parsed, dict):
        raise OAuthExchangeError("token exchange failed")
    return parsed


def _get_json(url: str, access_token: str) -> Dict[str, object]:
    request = Request(url, headers={"Authorization": "Bearer {0}".format(access_token)})
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
    except (URLError, TimeoutError, OSError) as exc:
        raise OAuthExchangeError("profile request failed") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OAuthExchangeError("profile request failed") from exc
    if not isinstance(parsed, dict):
        raise OAuthExchangeError("profile request failed")
    return parsed


def decode_jwt_payload(token: str) -> Dict[str, object]:
    parts = str(token or "").split(".")
    if len(parts) < 2:
        return {}
    try:
        payload = json.loads(_b64decode(parts[1]).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeError, BinasciiError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _apple_name(user_json: str) -> str:
    if not user_json:
        return ""
    try:
        parsed = json.loads(user_json)
    except json.JSONDecodeError:
        return ""
    name = parsed.get("name") if isinstance(parsed, dict) else ""
    if isinstance(name, dict):
        return "{0} {1}".format(name.get("firstName") or "", name.get("lastName") or "").strip()
    return str(name or "").strip()


def fetch_provider_profile(
    provider: str,
    code: str,
    redirect: str,
    user_json: str = "",
) -> Dict[str, str]:
    """인가 코드를 프로필 이메일과 subject로 바꾼다. 테스트는 이 함수를 대체한다."""
    if provider == "google":
        token = _post_form(
            "https://oauth2.googleapis.com/token",
            {
                "code": code,
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
            },
        )
        access = str(token.get("access_token") or "")
        if not access:
            raise OAuthExchangeError("token exchange failed")
        profile = _get_json("https://openidconnect.googleapis.com/v1/userinfo", access)
        return {
            "email": str(profile.get("email") or "").strip().lower(),
            "subject": str(profile.get("sub") or "").strip(),
            "name": str(profile.get("name") or "").strip(),
        }
    if provider == "apple":
        token = _post_form(
            "https://appleid.apple.com/auth/token",
            {
                "code": code,
                "client_id": os.getenv("APPLE_CLIENT_ID", ""),
                "client_secret": os.getenv("APPLE_CLIENT_SECRET", ""),
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
            },
        )
        claims = decode_jwt_payload(str(token.get("id_token") or ""))
        audience = str(claims.get("aud") or "")
        expected = os.getenv("APPLE_CLIENT_ID", "")
        if expected and audience and audience != expected:
            raise OAuthExchangeError("apple audience mismatch")
        return {
            "email": str(claims.get("email") or "").strip().lower(),
            "subject": str(claims.get("sub") or "").strip(),
            "name": _apple_name(user_json),
        }
    token = _post_form(
        "https://kauth.kakao.com/oauth/token",
        {
            "code": code,
            "client_id": os.getenv("KAKAO_CLIENT_ID", ""),
            "client_secret": os.getenv("KAKAO_CLIENT_SECRET", ""),
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
        },
    )
    access = str(token.get("access_token") or "")
    if not access:
        raise OAuthExchangeError("token exchange failed")
    profile = _get_json("https://kapi.kakao.com/v2/user/me", access)
    account = profile.get("kakao_account") if isinstance(profile.get("kakao_account"), dict) else {}
    properties = profile.get("properties") if isinstance(profile.get("properties"), dict) else {}
    profile_block = account.get("profile") if isinstance(account.get("profile"), dict) else {}
    name = str(profile_block.get("nickname") or properties.get("nickname") or "").strip()
    return {
        "email": str(account.get("email") or "").strip().lower(),
        "subject": str(profile.get("id") or "").strip(),
        "name": name,
    }


def complete_social_login(provider: str, email: str, subject: str, name: str = "") -> Dict[str, object]:
    """소셜 프로필을 사용자로 저장하고, 같은 게스트 이메일의 제보와 포인트를 이관한다."""
    account = link_social_account(email, provider, subject, name)
    moved_reports = assign_guest_requests(str(account["email"]), int(account["id"]))
    token = issue_user_token(int(account["id"]), str(account["email"]), provider)
    return {
        "user_id": int(account["id"]),
        "email": str(account["email"]),
        "name": str(account["display_name"] or ""),
        "auth_provider": str(account["auth_provider"]),
        "points_balance": int(account["points_balance"]),
        "migrated_reports": int(moved_reports),
        "migrated_point_logs": int(account["migrated_point_logs"]),
        "access_token": token,
    }


def public_session(user: Dict[str, object]) -> Dict[str, object]:
    return {
        "user_id": int(user["id"]),
        "email": str(user["email"]),
        "name": str(user.get("display_name") or ""),
        "auth_provider": str(user.get("auth_provider") or ""),
        "points_balance": int(user.get("points_balance") or 0),
        "migrated_reports": 0,
        "migrated_point_logs": 0,
    }
