"""제휴 입점 신청 계약. 신규 행은 PENDING_APPROVAL 이다."""

import re
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


PartnerCategory = Literal["K-Food", "K-Beauty", "Stay", "Experience", "Tour"]
PartnerStatus = Literal["PENDING_APPROVAL", "APPROVED", "PLANNED"]
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_SPLIT = re.compile(r"[\s,]+")


def _split_urls(value: str) -> str:
    parts = [part for part in _URL_SPLIT.split((value or "").strip()) if part]
    for url in parts:
        if not url.startswith(("http://", "https://")) and not url.startswith("magazine-uploads/"):
            raise ValueError("catalog image must be an http or https url")
    return "\n".join(parts)


class PartnerApply(BaseModel):
    store_name: str
    category: PartnerCategory
    address: str
    contact_email: str
    phone: str = ""
    store_description: str
    catalog_images: str = ""
    catalog_data: str = ""
    offered_benefit: str

    @field_validator(
        "store_name",
        "address",
        "contact_email",
        "phone",
        "store_description",
        "catalog_images",
        "catalog_data",
        "offered_benefit",
        mode="before",
    )
    @classmethod
    def _strip(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("contact_email")
    @classmethod
    def _email(cls, value: str) -> str:
        if not _EMAIL.match(value):
            raise ValueError("contact email is invalid")
        return value.lower()

    @field_validator("store_name")
    @classmethod
    def _name(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("store name is required")
        return value

    @field_validator("address")
    @classmethod
    def _address(cls, value: str) -> str:
        if len(value) < 4:
            raise ValueError("address is required")
        return value

    @field_validator("store_description")
    @classmethod
    def _description(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("store description is too short")
        return value

    @field_validator("offered_benefit")
    @classmethod
    def _benefit(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("offered benefit is required")
        return value

    @field_validator("catalog_images")
    @classmethod
    def _images(cls, value: str) -> str:
        return _split_urls(value)


class PartnerApplication(BaseModel):
    id: int
    store_name: str
    category: str = ""
    address: str = ""
    contact_email: str = ""
    phone: str = ""
    store_description: str = ""
    catalog_images: str = ""
    offered_benefit: str = ""
    city: str = ""
    status: str = "PENDING_APPROVAL"
    is_active: bool = False
    voucher_points: int = 50
    guide_id: str = ""
    discount_rate: float = 0
    created_at: str = ""


class PartnerApplicationList(BaseModel):
    partners: List[PartnerApplication] = Field(default_factory=list)


class PartnerApproval(BaseModel):
    partner: PartnerApplication
    guide_id: str
    article_markdown: str
