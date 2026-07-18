from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from pinmazon.compliance import ComplianceError, validate_copy
from pinmazon.links import has_affiliate_tag
from pinmazon.schemas import PinCopy

from pinmazon_core.repositories import Repository


CRITICAL_RISKS = {
    "MISSING_PRODUCT_IMAGE",
    "MISSING_DESTINATION",
    "MISSING_AFFILIATE_TAG",
    "AI_PRODUCT_NOT_REVIEWED",
}


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    errors: list[str]


def evaluate_creative(creative: dict) -> QualityGateResult:
    errors: list[str] = []
    image_path = Path(str(creative.get("image_path") or ""))
    if not image_path.is_file():
        errors.append("Missing generated image")
    else:
        try:
            with Image.open(image_path) as image:
                if image.size != (1000, 1500):
                    errors.append("Image must be 1000x1500")
        except Exception:
            errors.append("Generated image is invalid")

    if not str(creative.get("board") or "").strip():
        errors.append("Board is required")
    if not str(creative.get("alt_text") or "").strip():
        errors.append("Alt text is required")

    headline_words = str(creative.get("headline") or "").split()
    if not 2 <= len(headline_words) <= 6:
        errors.append("Headline must contain 2-6 words")
    bullets = list(creative.get("bullets") or [])
    if len(bullets) != 2 or any(not 2 <= len(str(item).split()) <= 6 for item in bullets):
        errors.append("Exactly two bullets with 2-6 words each are required")
    if len(str(creative.get("title") or "")) > 100:
        errors.append("Title exceeds 100 characters")
    description = str(creative.get("description") or "")
    if len(description) > 500:
        errors.append("Description exceeds 500 characters")
    if "affiliate links may earn commission." not in description.lower():
        errors.append("Affiliate disclosure is required")

    destination = str(creative.get("destination_url") or "")
    if not destination:
        errors.append("Destination URL is required")
    elif ("amazon." in destination or "amzn.to" in destination) and not has_affiliate_tag(destination):
        errors.append("Amazon destination is missing a tracking tag")

    copy = PinCopy(
        headline=str(creative.get("headline") or ""),
        bullets=list(creative.get("bullets") or []),
        title=str(creative.get("title") or ""),
        description=description,
        alt_text=str(creative.get("alt_text") or ""),
        short_description=str(creative.get("short_description") or creative.get("title") or "")[:75],
        hashtags=list(creative.get("hashtags") or []),
        keywords=list(creative.get("keywords") or []),
        visual_prompt="Local template background only",
    )
    try:
        validate_copy(copy)
    except ComplianceError as exc:
        errors.append(str(exc))

    risks = set(creative.get("risk_flags") or [])
    critical = sorted(risks & CRITICAL_RISKS)
    if critical:
        errors.append("Critical risk flags: " + ", ".join(critical))
    if str(creative.get("status")) not in {"approved", "ready"}:
        errors.append("Creative must be approved before ready")
    return QualityGateResult(passed=not errors, errors=errors)


def move_creatives_to_ready(repository: Repository, creative_ids: list[int]) -> dict[int, list[str]]:
    failures: dict[int, list[str]] = {}
    passed: list[int] = []
    for creative_id in creative_ids:
        creative = repository.get_creative(creative_id)
        if not creative:
            failures[creative_id] = ["Creative not found"]
            continue
        result = evaluate_creative(creative)
        if result.passed:
            passed.append(creative_id)
        else:
            failures[creative_id] = result.errors
    repository.set_creative_status(passed, "ready")
    return failures
