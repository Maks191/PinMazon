from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CoreSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    pinmazon_data_dir: str = "data"
    amazon_tracking_id: str = ""
    amazon_marketplace_host: str = "www.amazon.com"
    brand_name: str = "SMART GEAR LAB"

    @property
    def data_dir(self) -> Path:
        path = Path(self.pinmazon_data_dir).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()

    @property
    def database_path(self) -> Path:
        return self.data_dir / "pinmazon.sqlite3"

    @property
    def assets_dir(self) -> Path:
        return self.data_dir / "assets"

    @property
    def product_assets_dir(self) -> Path:
        return self.assets_dir / "products"

    @property
    def creative_assets_dir(self) -> Path:
        return self.assets_dir / "creatives"

    @property
    def background_assets_dir(self) -> Path:
        return self.assets_dir / "backgrounds"

    @property
    def debug_dir(self) -> Path:
        return self.data_dir / "debug"

    @property
    def browser_profile_dir(self) -> Path:
        return self.data_dir / "browser_profiles" / "pinterest"

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.product_assets_dir,
            self.creative_assets_dir,
            self.background_assets_dir,
            self.debug_dir,
            self.browser_profile_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
