from __future__ import annotations

import re
from urllib.parse import urlparse

from .links import has_affiliate_tag
from .schemas import PinCopy
from .settings import Settings


FORBIDDEN_CLAIM_PATTERNS = [
    re.compile(r"\$\s?\d"),
    re.compile(r"\b\d{1,3}%\s*off\b", re.I),
    re.compile(r"\b\d(?:\.\d)?\s*(?:stars?|★)\b", re.I),
    re.compile(r"\b\d[\d,]*\s+reviews?\b", re.I),
]
AGGRESSIVE_CTA = re.compile(r"\b(buy now|order now|must buy)\b", re.I)


class ComplianceError(ValueError):
    pass


def validate_destination(url: str, settings: Settings) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ComplianceError("Destination URL must be a valid http(s) URL.")

    host = parsed.netloc.lower()
    allowed = any(host == d or host.endswith("." + d) for d in settings.allowed_domains)
    if not allowed:
        raise ComplianceError(
            f"Destination domain '{host}' is not in ALLOWED_DESTINATION_DOMAINS."
        )

    if "amazon." in host or host == "amzn.to":
        if not settings.allow_untagged_amazon_links and not has_affiliate_tag(url):
            raise ComplianceError(
                "Amazon link does not contain a tracking tag. Paste a SiteStripe/Special Link "
                "or configure AMAZON_TRACKING_ID."
            )


def validate_copy(copy: PinCopy) -> PinCopy:
    if len(copy.title) > 100:
        copy.title = copy.title[:97].rstrip() + "..."
    if len(copy.description) > 500:
        copy.description = copy.description[:497].rstrip() + "..."
    if len(copy.alt_text) > 500:
        copy.alt_text = copy.alt_text[:500].rstrip()

    disclosure = "Affiliate links may earn commission."
    if disclosure.lower() not in copy.description.lower():
        max_body = 500 - len(disclosure) - 2
        body = copy.description.rstrip(" .")[:max_body].rstrip()
        copy.description = f"{body}. {disclosure}".strip()
    copy.description = copy.description[:500]

    combined = " ".join([copy.headline, *copy.bullets, copy.title, copy.description])
    for pattern in FORBIDDEN_CLAIM_PATTERNS:
        if pattern.search(combined):
            raise ComplianceError(
                "Generated copy contains price, discount, rating, or review claims. "
                "Regenerate without volatile claims."
            )
    if AGGRESSIVE_CTA.search(combined):
        raise ComplianceError("Generated copy contains an aggressive CTA.")

    copy.headline = " ".join(copy.headline.split()[:7])
    copy.bullets = [" ".join(x.split()[:7]) for x in copy.bullets[:2]]
    return copy
