from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


CreativeStatus = Literal[
    "draft",
    "generated",
    "needs_review",
    "approved",
    "ready",
    "rejected",
    "queued",
    "published",
    "failed",
    "winner",
    "rework",
]


class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    topic: str = Field(default="", max_length=180)
    target_count: int = Field(default=100, ge=1, le=100)
    pins_per_product: int = Field(default=3, ge=1, le=12)
    preferred_boards: list[str] = Field(default_factory=list)
    funnel: str = "consideration"
    audience: str = "Pinterest shoppers"
    copy_provider: str = "template"
    image_provider: str = "local_template"
    visual_templates: list[str] = Field(default_factory=lambda: ["apple_clean"])
    require_review: bool = True


class ProductCreate(BaseModel):
    source: str = "manual"
    source_url: str = ""
    canonical_url: str = ""
    asin: str | None = None
    product_name: str = Field(min_length=2, max_length=180)
    brand: str = ""
    category: str = ""
    audience: str = ""
    image_path: str = ""
    image_source_url: str = ""
    verified_facts: list[str] = Field(default_factory=list)
    affiliate_url: str = ""
    score: int = Field(default=0, ge=0, le=25)
    review_status: str = "needs_review"
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("verified_facts", "risk_flags", mode="before")
    @classmethod
    def normalize_string_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.replace("\n", ";").split(";") if part.strip()]
        return value


class CopyPackage(BaseModel):
    angle: str
    headline: str
    bullets: list[str]
    title: str
    description: str
    alt_text: str
    short_description: str
    hashtags: list[str]
    keywords: list[str]
    recommended_board: str
    funnel: str
    risk_flags: list[str] = Field(default_factory=list)
    visual_prompt: str = "Local template background only"


class CreativeDraft(BaseModel):
    campaign_id: int
    product_id: int
    slot_index: int
    angle: str
    visual_template: str
    headline: str
    bullets: list[str]
    title: str
    description: str
    alt_text: str
    hashtags: list[str]
    keywords: list[str]
    board: str
    destination_url: str
    image_path: str
    generation_prompt: str
    duplicate_hash: str
    quality_score: int = 0
    risk_flags: list[str] = Field(default_factory=list)
    status: CreativeStatus = "needs_review"
