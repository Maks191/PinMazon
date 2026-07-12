from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from pinmazon.schemas import PinCopy, ProductInput
from pinmazon.settings import Settings
from pinmazon.workflow import run_pin_job


def _product(board_id: str = "") -> ProductInput:
    return ProductInput(
        product_name="Test Camera Grip",
        destination_url="https://www.amazon.com/dp/B012345678?tag=test-tag-20",
        features="Verified ergonomic grip",
        board_id=board_id,
    )


def _copy() -> PinCopy:
    return PinCopy(
        headline="Steadier Handheld Shots",
        bullets=["Comfortable camera handling", "Cleaner movement control"],
        title="Camera Grip for Creator Setups",
        description="A practical camera grip for creator setups. Affiliate links may earn commission.",
        alt_text="A black camera grip on a dark background",
        short_description="A practical camera grip for creator setups.",
        hashtags=["#CameraGear", "#CreatorSetup"],
        keywords=["camera grip", "creator setup"],
        visual_prompt="Dark studio background with soft light",
    )


def _image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (400, 400), "white").save(buffer, "PNG")
    return buffer.getvalue()


def _settings(tmp_path) -> Settings:
    return Settings(
        amazon_tracking_id="test-tag-20",
        output_dir=str(tmp_path / "output"),
        history_file=str(tmp_path / "history.jsonl"),
    )


def test_generate_only_does_not_require_pinterest_board(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("pinmazon.workflow.generate_pin_copy", lambda product, settings: _copy())

    result = run_pin_job(
        product=_product(),
        product_image_bytes=_image_bytes(),
        settings=_settings(tmp_path),
        publish_now=False,
    )

    assert result.published is False
    with Image.open(result.image_path) as image:
        assert image.size == (1000, 1500)


def test_publish_requires_board_before_openai_call(monkeypatch, tmp_path) -> None:
    called = False

    def fake_generate(product, settings):
        nonlocal called
        called = True
        return _copy()

    monkeypatch.setattr("pinmazon.workflow.generate_pin_copy", fake_generate)

    with pytest.raises(ValueError, match="Pinterest board ID is required"):
        run_pin_job(
            product=_product(),
            product_image_bytes=_image_bytes(),
            settings=_settings(tmp_path),
            publish_now=True,
        )

    assert called is False


def test_publish_calls_pinterest_client_with_copy(monkeypatch, tmp_path) -> None:
    captured = {}

    class FakePinterestClient:
        def __init__(self, settings):
            pass

        def create_pin(self, **kwargs):
            captured.update(kwargs)
            return "pin-123"

    monkeypatch.setattr("pinmazon.workflow.generate_pin_copy", lambda product, settings: _copy())
    monkeypatch.setattr("pinmazon.workflow.PinterestClient", FakePinterestClient)

    result = run_pin_job(
        product=_product(board_id="board-123"),
        product_image_bytes=_image_bytes(),
        settings=_settings(tmp_path),
        publish_now=True,
    )

    assert result.published is True
    assert result.pin_id == "pin-123"
    assert captured["board_id"] == "board-123"
    assert captured["copy"].title == "Camera Grip for Creator Setups"
