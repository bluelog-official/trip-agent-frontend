"""게스트 매거진 제보 계약. 상태는 서버가 PENDING_REVIEW로 고정한다."""

import re
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_REVIEW_MIN = 50


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

    @field_validator(
        "nickname",
        "email",
        "country",
        "city",
        "place",
        "review",
        "photo_url",
        "photo_data",
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
        return self


class GuideSource(BaseModel):
    """1-click 가이드 생성에 넘길 원천 필드."""

    request_id: int
    destination: str
    keyword: str
    country: str
    city: str
    author_label: str
    review: str
    photo_url: str = ""
    ready_for_one_click: bool = True


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
    status: Literal["PENDING_REVIEW"] = "PENDING_REVIEW"
    created_at: str
    guide_source: GuideSource


class MagazineRequestList(BaseModel):
    requests: List[MagazineRequestRecord] = Field(default_factory=list)
