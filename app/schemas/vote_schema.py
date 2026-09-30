"""게시글 추천(Vote) 계약. 같은 IP는 글마다 한 표다."""

from typing import List

from pydantic import BaseModel, Field, field_validator


class VoteCreate(BaseModel):
    article_id: str = Field(min_length=1, max_length=180, description="가이드 또는 게시글 id")

    @field_validator("article_id")
    @classmethod
    def strip_article_id(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("article_id is required")
        return text


class VoteResult(BaseModel):
    article_id: str
    vote_count: int = Field(ge=0)
    voted: bool
    created: bool = Field(description="이번 요청으로 새 표가 저장되면 True")


class VoteStatus(BaseModel):
    article_id: str
    vote_count: int = Field(ge=0)
    voted: bool = Field(description="요청한 IP가 이미 추천했으면 True")


class VoteStatusList(BaseModel):
    votes: List[VoteStatus] = Field(default_factory=list)
