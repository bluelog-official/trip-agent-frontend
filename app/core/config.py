"""프로덕션 시크릿이 비었거나 기본값이면 프로세스를 바로 종료한다."""

import os
import sys

from dotenv import load_dotenv

REQUIRED_SECRETS = ("VOUCHER_SECRET", "OAUTH_TOKEN_SECRET")
_MIN_SECRET_LENGTH = 32
_INSECURE_FRAGMENTS = (
    "your_super_secret",
    "changeme",
    "change-me",
    "change_me",
    "placeholder",
    "replace-me",
    "replace_me",
    "bluelog-voucher",
    "bluelog-user-session",
    "test-secret",
    "test-voucher",
    "test_secret",
    "test_voucher",
    "example-secret",
    "dummy",
    "sample-secret",
    "password",
    "secret",
    "default",
)


def running_under_pytest() -> bool:
    return "pytest" in sys.modules or bool(os.getenv("PYTEST_CURRENT_TEST"))


def secret_is_insecure(value: str) -> bool:
    """빈 값, 짧은 값, 테스트·플레이스홀더 문자열은 프로덕션 시크릿으로 받지 않는다."""
    token = (value or "").strip()
    if len(token) < _MIN_SECRET_LENGTH:
        return True
    lowered = token.lower()
    if lowered in {"test", "secret", "password", "changeme", "default", "admin"}:
        return True
    return any(fragment in lowered for fragment in _INSECURE_FRAGMENTS)


def enforce_production_secrets(force: bool = False) -> None:
    """VOUCHER_SECRET과 OAUTH_TOKEN_SECRET이 안전하지 않으면 SystemExit."""
    load_dotenv()
    if not force and running_under_pytest():
        return
    unsafe = [
        name for name in REQUIRED_SECRETS if secret_is_insecure(os.getenv(name, ""))
    ]
    if unsafe:
        raise SystemExit(
            "Refusing to start. {0} must be a non-default production secret.".format(
                ", ".join(unsafe)
            )
        )
