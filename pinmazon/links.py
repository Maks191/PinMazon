from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


ASIN_RE = re.compile(r"(?:/dp/|/gp/product/|/product/)([A-Z0-9]{10})(?:[/?]|$)", re.I)


def extract_asin(url: str) -> str | None:
    match = ASIN_RE.search(url or "")
    return match.group(1).upper() if match else None


def build_affiliate_url(url: str, tracking_id: str, marketplace_host: str = "www.amazon.com") -> str:
    url = (url or "").strip()
    if not url:
        return ""

    host = urlparse(url).netloc.lower()
    if host == "amzn.to":
        return url

    asin = extract_asin(url)
    if asin and tracking_id:
        return f"https://{marketplace_host}/dp/{asin}?tag={tracking_id}"

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    if tracking_id:
        query["tag"] = [tracking_id]
    flat = [(k, v) for k, values in query.items() for v in values]
    return urlunparse(parsed._replace(query=urlencode(flat)))


def has_affiliate_tag(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() == "amzn.to":
        return True
    return bool(parse_qs(parsed.query).get("tag"))
