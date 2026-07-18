from __future__ import annotations

from pathlib import Path

from pinmazon.renderer import render_pin
from pinmazon.schemas import PinCopy
from pinmazon.settings import Settings as LegacySettings


class LocalTemplateProvider:
    name = "local_template"

    def __init__(self, brand_name: str):
        self.settings = LegacySettings(_env_file=None, brand_name=brand_name)

    def create(
        self,
        *,
        product_image: Path,
        pin_copy: PinCopy,
        visual_template: str,
        output_path: Path,
    ) -> Path:
        if not product_image.is_file():
            raise ValueError(f"Product image not found: {product_image}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return render_pin(
            product_image,
            pin_copy,
            visual_template,
            self.settings,
            output_path,
        )
