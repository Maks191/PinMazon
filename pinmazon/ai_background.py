from __future__ import annotations

import base64
from pathlib import Path

from openai import OpenAI
from PIL import Image

from .settings import Settings


def generate_background(prompt: str, settings: Settings, output_path: Path) -> Path:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")
    client = OpenAI(api_key=settings.openai_api_key)
    result = client.images.generate(
        model=settings.openai_image_model,
        prompt=(
            prompt
            + "\nVertical premium commercial background, 2:3 portrait, lots of negative space. "
              "No product, no device, no packaging, no logo, no text, no letters, no watermark."
        ),
        size="1024x1536",
        quality=settings.openai_image_quality,
    )
    raw = base64.b64decode(result.data[0].b64_json)
    temp_path = output_path.with_suffix(".raw.png")
    temp_path.write_bytes(raw)

    with Image.open(temp_path) as image:
        image = image.convert("RGB")
        image = image.resize((1000, 1500), Image.Resampling.LANCZOS)
        image.save(output_path, "PNG", optimize=True)
    temp_path.unlink(missing_ok=True)
    return output_path
