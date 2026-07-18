from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable

from pinmazon_core.db import Database
from pinmazon_core.schemas import CampaignCreate, CreativeDraft, ProductCreate


JSON_COLUMNS = {
    "preferred_boards_json": "preferred_boards",
    "visual_templates_json": "visual_templates",
    "verified_facts_json": "verified_facts",
    "risk_flags_json": "risk_flags",
    "bullets_json": "bullets",
    "hashtags_json": "hashtags",
    "keywords_json": "keywords",
}


def _decode_row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    value = dict(row)
    for column, alias in JSON_COLUMNS.items():
        if column in value:
            try:
                value[alias] = json.loads(value[column] or "[]")
            except json.JSONDecodeError:
                value[alias] = []
    return value


class Repository:
    def __init__(self, database: Database):
        self.db = database
        self.db.migrate()

    def create_campaign(self, campaign: CampaignCreate) -> int:
        with self.db.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO campaigns(
                    name, topic, target_count, pins_per_product,
                    preferred_boards_json, funnel, audience, copy_provider,
                    image_provider, visual_templates_json, require_review
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign.name,
                    campaign.topic,
                    campaign.target_count,
                    campaign.pins_per_product,
                    json.dumps(campaign.preferred_boards),
                    campaign.funnel,
                    campaign.audience,
                    campaign.copy_provider,
                    campaign.image_provider,
                    json.dumps(campaign.visual_templates),
                    int(campaign.require_review),
                ),
            )
            return int(cursor.lastrowid)

    def list_campaigns(self) -> list[dict]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.*,
                       COUNT(cr.id) AS creative_count,
                       SUM(CASE WHEN cr.status IN ('ready', 'queued') THEN 1 ELSE 0 END) AS ready_count
                FROM campaigns c
                LEFT JOIN creatives cr ON cr.campaign_id = c.id
                GROUP BY c.id
                ORDER BY c.id DESC
                """
            ).fetchall()
        return [_decode_row(row) for row in rows]

    def get_campaign(self, campaign_id: int) -> dict | None:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
            ).fetchone()
        return _decode_row(row)

    def add_product(self, product: ProductCreate) -> int:
        with self.db.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO products(
                    source, source_url, canonical_url, asin, product_name, brand,
                    category, audience, image_path, image_source_url,
                    verified_facts_json, affiliate_url, score, review_status,
                    risk_flags_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.source,
                    product.source_url,
                    product.canonical_url,
                    product.asin,
                    product.product_name,
                    product.brand,
                    product.category,
                    product.audience,
                    product.image_path,
                    product.image_source_url,
                    json.dumps(product.verified_facts, ensure_ascii=False),
                    product.affiliate_url,
                    product.score,
                    product.review_status,
                    json.dumps(product.risk_flags, ensure_ascii=False),
                ),
            )
            return int(cursor.lastrowid)

    def upsert_product(self, product: ProductCreate) -> int:
        if product.source_url:
            existing = self.find_product_by_source_url(product.source_url)
            if existing:
                return int(existing["id"])
        return self.add_product(product)

    def find_product_by_source_url(self, source_url: str) -> dict | None:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT * FROM products WHERE source_url = ?", (source_url,)
            ).fetchone()
        return _decode_row(row)

    def list_products(self, statuses: Iterable[str] | None = None) -> list[dict]:
        query = "SELECT * FROM products"
        params: list[str] = []
        if statuses:
            status_list = list(statuses)
            query += f" WHERE review_status IN ({','.join('?' for _ in status_list)})"
            params.extend(status_list)
        query += " ORDER BY id DESC"
        with self.db.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_decode_row(row) for row in rows]

    def set_product_status(self, product_ids: Iterable[int], status: str) -> int:
        ids = [int(value) for value in product_ids]
        if not ids:
            return 0
        with self.db.connect() as connection:
            cursor = connection.execute(
                f"UPDATE products SET review_status = ?, updated_at = CURRENT_TIMESTAMP "
                f"WHERE id IN ({','.join('?' for _ in ids)})",
                [status, *ids],
            )
            return cursor.rowcount

    def create_creative(self, creative: CreativeDraft) -> int:
        with self.db.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO creatives(
                    campaign_id, product_id, slot_index, angle, visual_template,
                    headline, bullets_json, title, description, alt_text,
                    hashtags_json, keywords_json, board, destination_url,
                    image_path, generation_prompt, duplicate_hash, quality_score,
                    risk_flags_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    creative.campaign_id,
                    creative.product_id,
                    creative.slot_index,
                    creative.angle,
                    creative.visual_template,
                    creative.headline,
                    json.dumps(creative.bullets),
                    creative.title,
                    creative.description,
                    creative.alt_text,
                    json.dumps(creative.hashtags),
                    json.dumps(creative.keywords),
                    creative.board,
                    creative.destination_url,
                    creative.image_path,
                    creative.generation_prompt,
                    creative.duplicate_hash,
                    creative.quality_score,
                    json.dumps(creative.risk_flags),
                    creative.status,
                ),
            )
            return int(cursor.lastrowid)

    def list_creatives(
        self,
        campaign_id: int | None = None,
        statuses: Iterable[str] | None = None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []
        if campaign_id is not None:
            clauses.append("cr.campaign_id = ?")
            params.append(campaign_id)
        if statuses:
            status_list = list(statuses)
            clauses.append(f"cr.status IN ({','.join('?' for _ in status_list)})")
            params.extend(status_list)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.db.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT cr.*, p.product_name, p.category,
                       p.image_path AS product_image_path,
                       c.name AS campaign_name
                FROM creatives cr
                JOIN products p ON p.id = cr.product_id
                JOIN campaigns c ON c.id = cr.campaign_id
                {where}
                ORDER BY cr.campaign_id DESC, cr.slot_index ASC
                """,
                params,
            ).fetchall()
        return [_decode_row(row) for row in rows]

    def creative_count(self, campaign_id: int) -> int:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM creatives WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
        return int(row["total"])

    def creative_slots(self, campaign_id: int) -> set[int]:
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT slot_index FROM creatives WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchall()
        return {int(row["slot_index"]) for row in rows}

    def get_creative(self, creative_id: int) -> dict | None:
        with self.db.connect() as connection:
            row = connection.execute(
                """
                SELECT cr.*, p.product_name, p.category,
                       p.image_path AS product_image_path,
                       c.name AS campaign_name
                FROM creatives cr
                JOIN products p ON p.id = cr.product_id
                JOIN campaigns c ON c.id = cr.campaign_id
                WHERE cr.id = ?
                """,
                (creative_id,),
            ).fetchone()
        return _decode_row(row)

    def set_creative_status(self, creative_ids: Iterable[int], status: str) -> int:
        ids = [int(value) for value in creative_ids]
        if not ids:
            return 0
        with self.db.connect() as connection:
            cursor = connection.execute(
                f"UPDATE creatives SET status = ?, updated_at = CURRENT_TIMESTAMP "
                f"WHERE id IN ({','.join('?' for _ in ids)})",
                [status, *ids],
            )
            if status == "ready":
                connection.executemany(
                    """
                    INSERT INTO publish_jobs(creative_id, mode, status)
                    VALUES (?, 'manual', 'queued')
                    ON CONFLICT(creative_id) DO NOTHING
                    """,
                    [(value,) for value in ids],
                )
            return cursor.rowcount

    def update_creative_fields(self, creative_id: int, values: dict) -> None:
        allowed = {
            "headline",
            "bullets_json",
            "title",
            "description",
            "alt_text",
            "board",
            "image_path",
            "quality_score",
            "risk_flags_json",
            "status",
        }
        clean = {key: value for key, value in values.items() if key in allowed}
        if not clean:
            return
        assignments = ", ".join(f"{key} = ?" for key in clean)
        with self.db.connect() as connection:
            connection.execute(
                f"UPDATE creatives SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                [*clean.values(), creative_id],
            )

    def queued_creatives(self) -> list[dict]:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT j.id AS job_id, j.status AS job_status, j.publish_at,
                       cr.*, p.product_name, c.name AS campaign_name
                FROM publish_jobs j
                JOIN creatives cr ON cr.id = j.creative_id
                JOIN products p ON p.id = cr.product_id
                JOIN campaigns c ON c.id = cr.campaign_id
                WHERE j.status IN ('queued', 'reserved')
                  AND cr.status IN ('ready', 'queued')
                ORDER BY COALESCE(j.publish_at, '9999-12-31'), j.id
                """
            ).fetchall()
        return [_decode_row(row) for row in rows]
