from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ProductInput(BaseModel):
    product_name: str = Field(min_length=2, max_length=180)
    amazon_url: str = ""
    destination_url: str
    image_url: str = ""
    features: str = ""
    audience: str = "creators and tech buyers"
    cluster: str = "Amazon Tech Finds"
    style: Literal[
        "apple_clean",
        "luxury_editorial",
        "viral_useful",
        "creator_setup",
        "warm_lifestyle",
    ] = "apple_clean"
    board_id: str = ""
    board_name: str = ""
    use_ai_background: bool = False

    @field_validator("destination_url")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Required field is blank.")
        return value.strip()

    @field_validator("board_id")
    @classmethod
    def clean_board_id(cls, value: str) -> str:
        return value.strip()


class PinCopy(BaseModel):
    headline: str = Field(description="2-6 short words for the image")
    bullets: list[str] = Field(description="Exactly two short benefit bullets")
    title: str = Field(description="Pinterest SEO title, max 100 characters")
    description: str = Field(description="Natural SEO description with affiliate disclosure")
    alt_text: str = Field(description="Accurate descriptive alt text")
    short_description: str = Field(description="One or two sentences")
    hashtags: list[str] = Field(description="10-15 targeted hashtags")
    keywords: list[str] = Field(description="3-8 target keywords")
    visual_prompt: str = Field(description="Prompt for a background only, no product and no text")

    @field_validator("bullets")
    @classmethod
    def exactly_two_bullets(cls, value: list[str]) -> list[str]:
        cleaned = [x.strip() for x in value if x.strip()]
        if len(cleaned) < 2:
            cleaned += ["Easy everyday upgrade"] * (2 - len(cleaned))
        return cleaned[:2]

    @field_validator("hashtags")
    @classmethod
    def clean_hashtags(cls, value: list[str]) -> list[str]:
        result = []
        for item in value:
            tag = item.strip().replace(" ", "")
            if not tag:
                continue
            if not tag.startswith("#"):
                tag = "#" + tag
            if tag.lower() not in {x.lower() for x in result}:
                result.append(tag)
        return result[:15]


class WorkflowResult(BaseModel):
    image_path: str
    metadata_path: str
    pin_id: str | None = None
    published: bool = False
    duplicate_key: str
    pin_copy: PinCopy
