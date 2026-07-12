from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from .settings import Settings


class PinterestTokenStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path: Path = settings.token_path

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, token: dict) -> None:
        token = dict(token)
        token.setdefault("created_at", int(time.time()))
        if "expires_in" in token:
            token["expires_at"] = int(time.time()) + int(token["expires_in"]) - 300
        self.path.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_access_token(self) -> str:
        token = self.load()
        if token.get("access_token") and token.get("expires_at", 0) > time.time():
            return token["access_token"]

        refresh_token = token.get("refresh_token")
        if not refresh_token:
            raise RuntimeError(
                "Pinterest token is missing or expired. Run: python scripts/pinterest_oauth.py"
            )
        if not self.settings.pinterest_app_id or not self.settings.pinterest_app_secret:
            raise RuntimeError("PINTEREST_APP_ID / PINTEREST_APP_SECRET are missing.")

        response = requests.post(
            "https://api.pinterest.com/v5/oauth/token",
            auth=(self.settings.pinterest_app_id, self.settings.pinterest_app_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": "boards:read,pins:read,pins:write",
            },
            timeout=30,
        )
        response.raise_for_status()
        new_token = response.json()
        self.save(new_token)
        return new_token["access_token"]
