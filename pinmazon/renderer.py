from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .schemas import PinCopy
from .settings import Settings


CANVAS = (1000, 1500)
WARM_WHITE = (236, 232, 222)
SOFT_GREY = (173, 178, 185)
GRAPHITE = (19, 21, 24)
DEEP_BLACK = (9, 10, 12)
MUTED_BLUE = (74, 93, 116)
CHAMPAGNE = (184, 159, 112)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates += [
            "C:/Windows/Fonts/seguisb.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates += [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _gradient(style: str) -> Image.Image:
    top, bottom = {
        "apple_clean": ((32, 35, 40), (11, 12, 14)),
        "luxury_editorial": ((44, 38, 34), (12, 11, 11)),
        "viral_useful": ((32, 42, 52), (11, 14, 18)),
        "creator_setup": ((25, 31, 38), (8, 10, 13)),
        "warm_lifestyle": ((70, 58, 48), (24, 20, 18)),
    }.get(style, ((32, 35, 40), (11, 12, 14)))

    strip = Image.new("RGB", (1, CANVAS[1]))
    px = strip.load()
    for y in range(CANVAS[1]):
        t = y / (CANVAS[1] - 1)
        row = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        px[0, y] = row
    return strip.resize(CANVAS)


def _remove_near_white(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    data = []
    pixels = (
        rgba.get_flattened_data()
        if hasattr(rgba, "get_flattened_data")
        else rgba.getdata()
    )
    for r, g, b, a in pixels:
        distance = ((255-r)**2 + (255-g)**2 + (255-b)**2) ** 0.5
        if distance < 18:
            alpha = 0
        elif distance < 75:
            alpha = int(255 * (distance - 18) / 57)
        else:
            alpha = a
        data.append((r, g, b, alpha))
    rgba.putdata(data)
    return rgba


def _fit_product(image: Image.Image, max_box=(760, 760)) -> Image.Image:
    image = _remove_near_white(image)
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    image.thumbnail(max_box, Image.Resampling.LANCZOS)
    return image


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], []
    for word in words:
        test = " ".join(current + [word])
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_text_block(draw: ImageDraw.ImageDraw, copy: PinCopy, brand_name: str) -> None:
    x = 82
    y = 75
    brand_font = _font(23, bold=True)
    headline_font = _font(76, bold=False)
    bullet_font = _font(29, bold=False)

    draw.text((x, y), brand_name, font=brand_font, fill=SOFT_GREY)
    y += 78

    for line in _wrap_text(draw, copy.headline, headline_font, 820)[:3]:
        draw.text((x, y), line, font=headline_font, fill=WARM_WHITE)
        y += 90

    y += 28
    for bullet in copy.bullets[:2]:
        draw.ellipse((x, y + 13, x + 8, y + 21), fill=CHAMPAGNE)
        draw.text((x + 26, y), bullet, font=bullet_font, fill=SOFT_GREY)
        y += 48


def render_pin(
    product_image_path: Path,
    copy: PinCopy,
    style: str,
    settings: Settings,
    output_path: Path,
    background_path: Path | None = None,
) -> Path:
    if background_path:
        background = Image.open(background_path).convert("RGB").resize(CANVAS)
        # Darken slightly for readable typography.
        veil = Image.new("RGBA", CANVAS, (0, 0, 0, 78))
        canvas = Image.alpha_composite(background.convert("RGBA"), veil)
    else:
        canvas = _gradient(style).convert("RGBA")

    draw = ImageDraw.Draw(canvas)
    _draw_text_block(draw, copy, settings.brand_name)

    with Image.open(product_image_path) as source:
        product = _fit_product(source)

    # Soft shadow.
    shadow = Image.new("RGBA", product.size, (0, 0, 0, 0))
    alpha = product.getchannel("A").filter(ImageFilter.GaussianBlur(22))
    shadow.putalpha(alpha)
    shadow_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))

    px = (CANVAS[0] - product.width) // 2 + 55
    py = 665 + max(0, (730 - product.height) // 2)
    shadow_layer.alpha_composite(shadow, (px + 16, py + 24))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(10))
    canvas = Image.alpha_composite(canvas, shadow_layer)

    canvas.alpha_composite(product, (px, py))

    # Bottom micro-label.
    draw = ImageDraw.Draw(canvas)
    footer_font = _font(20, bold=False)
    draw.text((82, 1432), copy.short_description[:75], font=footer_font, fill=(130, 133, 138))

    canvas.convert("RGB").save(output_path, "PNG", optimize=True)
    return output_path
