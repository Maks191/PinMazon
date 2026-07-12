from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app import app
from pinmazon.schemas import PinCopy


client = TestClient(app)


def _image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (480, 480), "white").save(buffer, "PNG")
    return buffer.getvalue()


def _copy() -> PinCopy:
    return PinCopy(
        headline="Cleaner Creator Setup",
        bullets=["Simple desk organization", "Ready for daily work"],
        title="Useful Desk Accessory for Creator Setups",
        description="A practical desk accessory for creators. Affiliate links may earn commission.",
        alt_text="A desk accessory on a dark background",
        short_description="A practical addition to a creator desk.",
        hashtags=["#CreatorSetup", "#DeskAccessories"],
        keywords=["creator setup", "desk accessory"],
        visual_prompt="Dark premium desk background with soft studio light",
    )


def test_cloud_pages_and_health() -> None:
    assert client.get("/").status_code == 200
    assert "OpenAI API key" in client.get("/").text
    assert client.get("/privacy").status_code == 200
    assert client.get("/api/health").json() == {
        "status": "ok",
        "mode": "generate_only",
    }


def test_cloud_generate_only_uses_request_key_without_publishing(monkeypatch) -> None:
    monkeypatch.setattr("pinmazon.workflow.generate_pin_copy", lambda product, settings: _copy())

    response = client.post(
        "/api/generate",
        data={
            "openai_api_key": "test-request-key-not-a-real-secret-123",
            "amazon_tracking_id": "pinmazon-test-20",
            "product_name": "Test Desk Accessory",
            "amazon_url": "https://www.amazon.com/dp/B012345678",
            "features": "Verified compact shape",
            "style": "apple_clean",
        },
        files={"product_image": ("product.png", _image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["published"] is False
    assert payload["image_base64"]
    assert payload["destination_url"].endswith("?tag=pinmazon-test-20")
    assert "openai_api_key" not in str(payload).lower()


def test_cloud_rejects_short_key_before_generation() -> None:
    response = client.post(
        "/api/generate",
        data={
            "openai_api_key": "short",
            "amazon_tracking_id": "pinmazon-test-20",
            "product_name": "Test Desk Accessory",
            "amazon_url": "https://www.amazon.com/dp/B012345678",
        },
        files={"product_image": ("product.png", _image_bytes(), "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Enter a valid OpenAI API key."
