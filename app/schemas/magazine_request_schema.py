"""게스트 매거진 제보 계약. 접수 상태는 PENDING_REVIEW, 팩트체크는 PENDING으로 시작한다."""

import re
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_REVIEW_MIN = 50
_URL_SPLIT = re.compile(r"[\s,]+")

FactCheckStatus = Literal["PENDING", "VERIFIED", "REJECTED"]
RequestStatus = Literal["PENDING_REVIEW", "PUBLISHED"]

_SUBMIT_LANGUAGES = {
    "en": "en",
    "english": "en",
    "ko": "ko",
    "kr": "ko",
    "korean": "ko",
    "ja": "ja",
    "jp": "ja",
    "japanese": "ja",
    "zh-cn": "zh-CN",
    "zh-hans": "zh-CN",
    "zh": "zh-CN",
    "zh-tw": "zh-TW",
    "zh-hant": "zh-TW",
    "vi": "vi",
    "vietnamese": "vi",
    "th": "th",
    "thai": "th",
    "es": "es",
    "spanish": "es",
    "fr": "fr",
    "french": "fr",
}


def normalize_submit_language(value: str) -> str:
    raw = (value or "").strip()
    mapped = _SUBMIT_LANGUAGES.get(raw.lower())
    if mapped:
        return mapped
    return "en"


def normalize_reference_urls(value: str) -> str:
    """공백·쉼표로 나뉜 http(s) 주소를 줄바꿈으로 맞춘다."""
    parts = [part for part in _URL_SPLIT.split((value or "").strip()) if part]
    for url in parts:
        if not url.startswith(("http://", "https://")):
            raise ValueError("reference url must be http or https")
    return "\n".join(parts)


class MagazineRequestCreate(BaseModel):
    author_type: Literal["anonymous", "public"]
    nickname: str = ""
    email: str = ""
    country: str
    city: str
    place: str
    review: str
    photo_url: str = ""
    photo_data: str = ""
    transport_info: str = ""
    discovery_story: str = ""
    reference_urls: str = ""
    submit_language: str = "en"

    @field_validator("submit_language", mode="before")
    @classmethod
    def _language(cls, value: object) -> str:
        return normalize_submit_language("" if value is None else str(value))

    @field_validator(
        "nickname",
        "email",
        "country",
        "city",
        "place",
        "review",
        "photo_url",
        "photo_data",
        "transport_info",
        "discovery_story",
        "reference_urls",
        mode="before",
    )
    @classmethod
    def _strip(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @model_validator(mode="after")
    def _check_submission(self) -> "MagazineRequestCreate":
        if self.author_type == "public" and not self.nickname:
            raise ValueError("public name requires a nickname")
        if not self.country or not self.city or not self.place:
            raise ValueError("country, city, and place are required")
        if len(self.review) < _REVIEW_MIN:
            raise ValueError("review must be at least 50 characters")
        if self.email and not _EMAIL.match(self.email):
            raise ValueError("email is invalid")
        if self.photo_url and not self.photo_url.startswith(("http://", "https://")):
            raise ValueError("photo url must be http or https")
        self.reference_urls = normalize_reference_urls(self.reference_urls)
        return self


class GuideSource(BaseModel):
    """1-click 가이드 생성에 넘길 원천 필드. VERIFIED 이고 아직 초안이 없을 때만 준비된다."""

    request_id: int
    destination: str
    keyword: str
    country: str
    city: str
    author_label: str
    review: str
    photo_url: str = ""
    transport_info: str = ""
    discovery_story: str = ""
    reference_urls: str = ""
    submit_language: str = "en"
    fact_check_status: FactCheckStatus = "PENDING"
    ready_for_one_click: bool = False


class MagazineRequestRecord(BaseModel):
    id: int
    author_type: Literal["anonymous", "public"]
    nickname: str = ""
    email: str = ""
    country: str
    city: str
    place: str
    review: str
    photo_url: str = ""
    transport_info: str = ""
    discovery_story: str = ""
    reference_urls: str = ""
    status: RequestStatus = "PENDING_REVIEW"
    fact_check_status: FactCheckStatus = "PENDING"
    verification_note: str = ""
    published_guide_id: str = ""
    submit_language: str = "en"
    english_sha256: str = ""
    korean_guide_id: str = ""
    created_at: str
    guide_source: GuideSource


class MagazineRequestList(BaseModel):
    requests: List[MagazineRequestRecord] = Field(default_factory=list)


class FactCheckUpdate(BaseModel):
    fact_check_status: FactCheckStatus
    verification_note: str = ""

    @field_validator("verification_note", mode="before")
    @classmethod
    def _strip_note(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()


class GuestPublishResult(BaseModel):
    request_id: int
    guide_id: str
    fact_check_status: FactCheckStatus
    article_markdown: str
    korean_guide_id: str = ""
    english_sha256: str = ""
