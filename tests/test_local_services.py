from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from pinmazon.links import has_affiliate_tag
from pinmazon.schemas import PinCopy
from pinmazon_core.batch import ANGLES, generate_batch
from pinmazon_core.compliance import evaluate_creative, move_creatives_to_ready
from pinmazon_core.db import Database
from pinmazon_core.image_providers import LocalTemplateProvider
from pinmazon_core.product_sources import ProductImporter
from pinmazon_core.repositories import Repository
from pinmazon_core.schemas import CampaignCreate
from pinmazon_core.settings import CoreSettings


def image_bytes(color: str = "grey") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (420, 420), color).save(buffer, "PNG")
    return buffer.getvalue()


def resources(tmp_path):
    settings = CoreSettings(
        pinmazon_data_dir=str(tmp_path / "data"),
        amazon_tracking_id="test-tag-20",
    )
    database = Database(settings)
    repository = Repository(database)
    importer = ProductImporter(repository, settings)
    return settings, database, repository, importer


def approved_product(repository, importer, index: int = 1) -> int:
    path = importer.save_uploaded_image(f"product-{index}.png", image_bytes())
    product_id = importer.import_row(
        {
            "Product": f"Verified Desk Product {index}",
            "Product URL": f"https://www.amazon.com/dp/B0123456{index:02d}",
            "Image Path": str(path),
            "Category": "Desk accessories",
            "Verified Facts": "Real product photo supplied",
            "Score": 20,
        }
    )
    repository.set_product_status([product_id], "approved")
    return product_id


def test_migration_creates_shared_tables_and_folders(tmp_path) -> None:
    settings, database, _, _ = resources(tmp_path)
    assert {"products", "campaigns", "creatives", "publish_jobs", "analytics"}.issubset(
        database.table_names()
    )
    assert settings.database_path.exists()
    assert settings.product_assets_dir.is_dir()
    assert settings.browser_profile_dir.is_dir()


def test_import_builds_tagged_affiliate_link_without_scraping(tmp_path) -> None:
    _, _, repository, importer = resources(tmp_path)
    product_id = approved_product(repository, importer)
    product = next(row for row in repository.list_products() if row["id"] == product_id)
    assert product["asin"] == "B012345601"
    assert has_affiliate_tag(product["affiliate_url"])
    assert product["image_path"]


def test_batch_creates_exactly_100_and_resumes_without_duplicates(monkeypatch, tmp_path) -> None:
    settings, _, repository, importer = resources(tmp_path)
    product_ids = [approved_product(repository, importer, index) for index in range(1, 5)]
    campaign_id = repository.create_campaign(
        CampaignCreate(
            name="Exact 100 test",
            topic="Desk setup gadgets",
            target_count=100,
            preferred_boards=["Desk Setup", "Amazon Finds"],
            visual_templates=["apple_clean", "creator_setup"],
        )
    )

    def fast_create(self, *, product_image, pin_copy, visual_template, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1000, 1500), "black").save(output_path, "PNG")
        return output_path

    monkeypatch.setattr(LocalTemplateProvider, "create", fast_create)
    assert generate_batch(
        repository=repository,
        settings=settings,
        campaign_id=campaign_id,
        product_ids=product_ids,
    ) == 100
    assert repository.creative_count(campaign_id) == 100
    assert generate_batch(
        repository=repository,
        settings=settings,
        campaign_id=campaign_id,
        product_ids=product_ids,
    ) == 0

    creatives = repository.list_creatives(campaign_id=campaign_id)
    assert len({row["duplicate_hash"] for row in creatives}) == 100
    assert set(ANGLES).issubset({row["angle"] for row in creatives})
    assert all(row["description"].endswith("Affiliate links may earn commission.") for row in creatives)


def test_quality_gate_and_ready_queue(tmp_path) -> None:
    settings, _, repository, importer = resources(tmp_path)
    product_id = approved_product(repository, importer)
    campaign_id = repository.create_campaign(
        CampaignCreate(
            name="Ready test",
            target_count=1,
            preferred_boards=["Desk Setup"],
        )
    )
    generate_batch(
        repository=repository,
        settings=settings,
        campaign_id=campaign_id,
        product_ids=[product_id],
    )
    creative = repository.list_creatives(campaign_id=campaign_id)[0]
    assert evaluate_creative(creative).passed is False

    repository.set_creative_status([creative["id"]], "approved")
    failures = move_creatives_to_ready(repository, [creative["id"]])
    assert failures == {}
    queue = repository.queued_creatives()
    assert len(queue) == 1
    assert queue[0]["status"] == "ready"
    assert queue[0]["job_status"] == "queued"


def test_local_renderer_dimensions(tmp_path) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(image_bytes("white"))
    output = tmp_path / "pin.png"
    copy = PinCopy(
        headline="Clean Setup Upgrade",
        bullets=["Simple desk refresh", "Made for daily use"],
        title="Desk Setup Product Inspiration",
        description="A practical product idea. Affiliate links may earn commission.",
        alt_text="A product on a dark graphic background",
        short_description="A practical product idea.",
        hashtags=["#DeskSetup", "#AmazonFinds"],
        keywords=["desk setup", "amazon finds"],
        visual_prompt="Local only",
    )
    LocalTemplateProvider("TEST BRAND").create(
        product_image=source,
        pin_copy=copy,
        visual_template="apple_clean",
        output_path=output,
    )
    with Image.open(output) as image:
        assert image.size == (1000, 1500)
