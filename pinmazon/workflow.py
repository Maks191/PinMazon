from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import requests
from PIL import Image

from .ai_background import generate_background
from .compliance import ComplianceError, validate_copy, validate_destination
from .copywriter import generate_pin_copy
from .history import already_exists, append_history, duplicate_key
from .pinterest import PinterestClient
from .renderer import render_pin
from .schemas import PinCopy, ProductInput, WorkflowResult
from .settings import Settings


def _slug(text: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return clean[:60] or uuid.uuid4().hex[:10]


def _save_product_image(
    *,
    upload_bytes: bytes | None,
    image_url: str,
    output_path: Path,
) -> Path:
    if upload_bytes:
        output_path.write_bytes(upload_bytes)
    elif image_url:
        response = requests.get(image_url, timeout=45, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        output_path.write_bytes(response.content)
    else:
        raise ValueError(
            "Product image is required. Upload an image or paste a direct image URL. "
            "The MVP intentionally does not scrape Amazon product pages."
        )

    with Image.open(output_path) as image:
        image.verify()
    return output_path


def run_pin_job(
    *,
    product: ProductInput,
    product_image_bytes: bytes | None,
    settings: Settings,
    publish_now: bool,
    force_duplicate: bool = False,
    pin_copy: PinCopy | None = None,
) -> WorkflowResult:
    validate_destination(product.destination_url, settings)
    if publish_now and not product.board_id:
        raise ValueError("Pinterest board ID is required for publishing.")
    copy = validate_copy(pin_copy or generate_pin_copy(product, settings))

    key = duplicate_key(
        product.product_name,
        product.destination_url,
        product.board_id,
        copy.headline,
    )
    if publish_now and already_exists(settings.history_path, key) and not force_duplicate:
        raise ComplianceError(
            "This product/headline/board combination already exists in history. "
            "Enable force duplicate only when this is intentional."
        )

    slug = _slug(product.product_name)
    job_dir = settings.output_path / f"{slug}-{uuid.uuid4().hex[:8]}"
    job_dir.mkdir(parents=True, exist_ok=True)

    suffix = ".png"
    image_source = job_dir / f"source{suffix}"
    _save_product_image(
        upload_bytes=product_image_bytes,
        image_url=product.image_url,
        output_path=image_source,
    )

    background_path = None
    if product.use_ai_background:
        background_path = generate_background(
            copy.visual_prompt,
            settings,
            job_dir / "background.png",
        )

    pin_path = render_pin(
        image_source,
        copy,
        product.style,
        settings,
        job_dir / "pin.png",
        background_path,
    )

    metadata = {
        "product": product.model_dump(),
        "copy": copy.model_dump(),
        "image_path": str(pin_path),
        "duplicate_key": key,
        "published": False,
        "pin_id": None,
    }

    pin_id = None
    if publish_now:
        pin_id = PinterestClient(settings).create_pin(
            board_id=product.board_id,
            image_path=pin_path,
            copy=copy,
            destination_url=product.destination_url,
            ai_modified=product.use_ai_background,
        )
        metadata["published"] = True
        metadata["pin_id"] = pin_id

    metadata_path = job_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    append_history(settings.history_path, metadata)

    return WorkflowResult(
        image_path=str(pin_path),
        metadata_path=str(metadata_path),
        pin_id=pin_id,
        published=publish_now,
        duplicate_key=key,
        pin_copy=copy,
    )
