from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import requests
from PIL import Image

from pinmazon.links import build_affiliate_url, extract_asin, has_affiliate_tag

from pinmazon_core.repositories import Repository
from pinmazon_core.schemas import ProductCreate
from pinmazon_core.settings import CoreSettings


MAX_IMAGE_BYTES = 12 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}

ALIASES = {
    "product": "product_name",
    "product name": "product_name",
    "product url": "source_url",
    "amazon url": "source_url",
    "affiliate url": "affiliate_url",
    "image url": "image_source_url",
    "local image": "local_image",
    "verified facts": "verified_facts",
    "destination url": "affiliate_url",
}


class ProductImporter:
    def __init__(self, repository: Repository, settings: CoreSettings):
        self.repository = repository
        self.settings = settings
        self.settings.ensure_directories()

    def save_uploaded_image(self, filename: str, content: bytes) -> Path:
        if not content or len(content) > MAX_IMAGE_BYTES:
            raise ValueError("Product image must be between 1 byte and 12 MB.")
        suffix = Path(filename).suffix.lower() or ".png"
        digest = hashlib.sha256(content).hexdigest()[:16]
        destination = self.settings.product_assets_dir / f"{digest}{suffix}"
        destination.write_bytes(content)
        self._verify_image(destination)
        return destination

    def copy_local_image(self, source: str | Path) -> Path:
        source_path = Path(source).expanduser().resolve()
        if not source_path.is_file():
            raise ValueError(f"Local image not found: {source_path}")
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()[:16]
        destination = self.settings.product_assets_dir / f"{digest}{source_path.suffix.lower()}"
        if source_path != destination:
            shutil.copy2(source_path, destination)
        self._verify_image(destination)
        return destination

    def download_direct_image(self, url: str) -> Path:
        response = requests.get(
            url,
            timeout=30,
            stream=True,
            headers={"User-Agent": "PinMazon/1.0 direct-image-import"},
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError("Image URL must point directly to PNG, JPG, or WEBP; HTML is rejected.")
        expected_size = int(response.headers.get("Content-Length") or 0)
        if expected_size > MAX_IMAGE_BYTES:
            raise ValueError("Direct image is larger than 12 MB.")
        chunks = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            chunks.extend(chunk)
            if len(chunks) > MAX_IMAGE_BYTES:
                raise ValueError("Direct image is larger than 12 MB.")
        content = bytes(chunks)
        suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[content_type]
        return self.save_uploaded_image(f"download{suffix}", content)

    def import_row(self, row: dict, source: str = "import") -> int:
        normalized = {
            ALIASES.get(str(key).strip().lower(), str(key).strip().lower().replace(" ", "_")): value
            for key, value in row.items()
        }
        name = str(normalized.get("product_name") or "").strip()
        source_url = str(normalized.get("source_url") or "").strip()
        affiliate_url = str(normalized.get("affiliate_url") or "").strip()
        image_path = str(normalized.get("image_path") or "").strip()
        image_url = str(normalized.get("image_source_url") or "").strip()
        local_image = str(normalized.get("local_image") or "").strip()
        if local_image and not image_path:
            image_path = str(self.copy_local_image(local_image))
        elif image_url and not image_path:
            image_path = str(self.download_direct_image(image_url))

        if not affiliate_url and source_url and self.settings.amazon_tracking_id:
            affiliate_url = build_affiliate_url(
                source_url,
                self.settings.amazon_tracking_id,
                self.settings.amazon_marketplace_host,
            )

        risk_flags: list[str] = []
        if not image_path:
            risk_flags.append("MISSING_PRODUCT_IMAGE")
        if not affiliate_url:
            risk_flags.append("MISSING_DESTINATION")
        elif "amazon." in affiliate_url and not has_affiliate_tag(affiliate_url):
            risk_flags.append("MISSING_AFFILIATE_TAG")

        product = ProductCreate(
            source=source,
            source_url=source_url,
            canonical_url=source_url,
            asin=extract_asin(source_url),
            product_name=name,
            brand=str(normalized.get("brand") or "").strip(),
            category=str(normalized.get("category") or "").strip(),
            audience=str(normalized.get("audience") or "").strip(),
            image_path=image_path,
            image_source_url=image_url,
            verified_facts=normalized.get("verified_facts") or [],
            affiliate_url=affiliate_url,
            score=int(float(normalized.get("score") or 0)),
            review_status="needs_review",
            risk_flags=risk_flags,
        )
        return self.repository.upsert_product(product)

    def import_table(self, file: BinaryIO, filename: str) -> list[int]:
        suffix = Path(filename).suffix.lower()
        if suffix == ".csv":
            frame = pd.read_csv(file)
        elif suffix in {".xlsx", ".xlsm"}:
            frame = pd.read_excel(file, engine="openpyxl")
        else:
            raise ValueError("Use CSV or XLSX.")
        frame = frame.fillna("")
        return [self.import_row(row, source=suffix.lstrip(".")) for row in frame.to_dict("records")]

    @staticmethod
    def _verify_image(path: Path) -> None:
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception as exc:
            path.unlink(missing_ok=True)
            raise ValueError("The supplied file is not a valid image.") from exc
