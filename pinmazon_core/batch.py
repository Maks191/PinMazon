from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from pinmazon.compliance import validate_copy
from pinmazon.links import has_affiliate_tag
from pinmazon.schemas import PinCopy

from pinmazon_core.copy_providers import PinCopyRequest, TemplateCopyProvider
from pinmazon_core.image_providers import LocalTemplateProvider
from pinmazon_core.repositories import Repository
from pinmazon_core.schemas import CreativeDraft
from pinmazon_core.settings import CoreSettings


ANGLES = ("result", "problem_solution", "audience_use_case")


class BatchPreflightError(ValueError):
    pass


def _eligible_products(repository: Repository, product_ids: list[int] | None) -> list[dict]:
    products = repository.list_products(statuses=["approved"])
    if product_ids is not None:
        selected = {int(value) for value in product_ids}
        products = [product for product in products if int(product["id"]) in selected]
    errors: list[str] = []
    for product in products:
        if not Path(str(product.get("image_path") or "")).is_file():
            errors.append(f"{product['product_name']}: missing real product image")
        destination = str(product.get("affiliate_url") or "")
        if not destination:
            errors.append(f"{product['product_name']}: missing destination URL")
        elif ("amazon." in destination or "amzn.to" in destination) and not has_affiliate_tag(destination):
            errors.append(f"{product['product_name']}: Amazon link has no tracking tag")
        if product.get("risk_flags"):
            errors.append(f"{product['product_name']}: unresolved risk flags")
    if errors:
        raise BatchPreflightError("\n".join(errors))
    if not products:
        raise BatchPreflightError("Approve at least one product with a real image and affiliate link.")
    return sorted(products, key=lambda item: int(item["id"]))


def generate_batch(
    *,
    repository: Repository,
    settings: CoreSettings,
    campaign_id: int,
    product_ids: list[int] | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> int:
    campaign = repository.get_campaign(campaign_id)
    if not campaign:
        raise BatchPreflightError("Campaign not found.")
    if campaign["copy_provider"] != "template":
        raise BatchPreflightError("Milestone B supports the no-API Template provider only.")
    if campaign["image_provider"] != "local_template":
        raise BatchPreflightError("Milestone B supports the local renderer only.")
    boards = [str(value).strip() for value in campaign["preferred_boards"] if str(value).strip()]
    if not boards:
        raise BatchPreflightError("Add at least one Pinterest board before batch generation.")

    products = _eligible_products(repository, product_ids)
    target_count = int(campaign["target_count"])
    existing_slots = repository.creative_slots(campaign_id)
    copy_provider = TemplateCopyProvider()
    image_provider = LocalTemplateProvider(settings.brand_name)
    templates = campaign["visual_templates"] or ["apple_clean"]
    created = 0

    for slot_index in range(target_count):
        if slot_index in existing_slots:
            if progress:
                progress(slot_index + 1, target_count)
            continue
        product_index = slot_index % len(products)
        round_index = slot_index // len(products)
        product = products[product_index]
        angle = ANGLES[round_index % len(ANGLES)]
        variant_index = round_index // len(ANGLES)
        board = boards[(product_index + round_index) % len(boards)]
        visual_template = templates[slot_index % len(templates)]
        copy = copy_provider.generate(
            PinCopyRequest(
                product=product,
                angle=angle,
                audience=campaign["audience"],
                board=board,
                funnel=campaign["funnel"],
                variant_index=variant_index,
            )
        )
        pin_copy = validate_copy(
            PinCopy(
                headline=copy.headline,
                bullets=copy.bullets,
                title=copy.title,
                description=copy.description,
                alt_text=copy.alt_text,
                short_description=copy.short_description,
                hashtags=copy.hashtags,
                keywords=copy.keywords,
                visual_prompt=copy.visual_prompt,
            )
        )
        digest_source = json.dumps(
            {
                "campaign": campaign_id,
                "product": product["id"],
                "angle": angle,
                "variant": variant_index,
                "template": visual_template,
                "headline": pin_copy.headline,
            },
            sort_keys=True,
        )
        duplicate_hash = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
        output_path = (
            settings.creative_assets_dir
            / f"campaign-{campaign_id}"
            / f"pin-{slot_index + 1:03d}.png"
        )
        image_provider.create(
            product_image=Path(product["image_path"]),
            pin_copy=pin_copy,
            visual_template=visual_template,
            output_path=output_path,
        )
        repository.create_creative(
            CreativeDraft(
                campaign_id=campaign_id,
                product_id=int(product["id"]),
                slot_index=slot_index,
                angle=angle,
                visual_template=visual_template,
                headline=pin_copy.headline,
                bullets=pin_copy.bullets,
                title=pin_copy.title,
                description=pin_copy.description,
                alt_text=pin_copy.alt_text,
                hashtags=pin_copy.hashtags,
                keywords=pin_copy.keywords,
                board=board,
                destination_url=product["affiliate_url"],
                image_path=str(output_path),
                generation_prompt="Deterministic local template; no AI API call.",
                duplicate_hash=duplicate_hash,
                quality_score=90,
                risk_flags=copy.risk_flags,
                status="needs_review",
            )
        )
        created += 1
        if progress:
            progress(slot_index + 1, target_count)
    return created
