from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_text_model: str = "gpt-5.6-luna"
    openai_image_model: str = "gpt-image-2"
    openai_image_quality: str = "low"

    pinterest_app_id: str = ""
    pinterest_app_secret: str = ""
    pinterest_redirect_uri: str = "http://localhost:8787/callback"
    pinterest_token_file: str = "data/pinterest_token.json"
    pinterest_default_board_id: str = ""

    amazon_tracking_id: str = ""
    amazon_marketplace_host: str = "www.amazon.com"

    brand_name: str = "SMART GEAR LAB"
    default_publish_mode: str = "generate_only"
    allow_untagged_amazon_links: bool = False
    allowed_destination_domains: str = "amazon.com,www.amazon.com,amzn.to"
    history_file: str = "data/history.jsonl"
    output_dir: str = "output"

    @property
    def allowed_domains(self) -> set[str]:
        return {x.strip().lower() for x in self.allowed_destination_domains.split(",") if x.strip()}

    @property
    def output_path(self) -> Path:
        path = Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def token_path(self) -> Path:
        path = Path(self.pinterest_token_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def history_path(self) -> Path:
        path = Path(self.history_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
