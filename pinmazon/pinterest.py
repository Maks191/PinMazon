from __future__ import annotations

import base64
from pathlib import Path

import requests

from .schemas import PinCopy
from .settings import Settings
from .token_store import PinterestTokenStore


class PinterestClient:
    base_url = "https://api.pinterest.com/v5"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.tokens = PinterestTokenStore(settings)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.tokens.get_access_token()}",
            "Content-Type": "application/json",
        }

    def list_boards(self) -> list[dict]:
        response = requests.get(
            f"{self.base_url}/boards",
            headers=self._headers(),
            params={"page_size": 100},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("items", [])

    def create_pin(
        self,
        *,
        board_id: str,
        image_path: Path,
        copy: PinCopy,
        destination_url: str,
        ai_modified: bool,
    ) -> str:
        image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "board_id": board_id,
            "media_source": {
                "source_type": "image_base64",
                "content_type": "image/png",
                "data": image_data,
            },
            "title": copy.title,
            "description": copy.description,
            "alt_text": copy.alt_text,
            "link": destination_url,
        }
        if ai_modified:
            payload["ai_disclosures"] = {"values": ["AI_MODIFIED"]}

        response = requests.post(
            f"{self.base_url}/pins",
            headers=self._headers(),
            json=payload,
            timeout=90,
        )
        if not response.ok:
            raise RuntimeError(
                f"Pinterest API error {response.status_code}: {response.text[:1200]}"
            )
        return response.json()["id"]
