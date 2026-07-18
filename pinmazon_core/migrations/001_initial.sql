CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL DEFAULT 'manual',
    source_url TEXT NOT NULL DEFAULT '',
    canonical_url TEXT NOT NULL DEFAULT '',
    asin TEXT,
    product_name TEXT NOT NULL,
    brand TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    audience TEXT NOT NULL DEFAULT '',
    image_path TEXT NOT NULL DEFAULT '',
    image_source_url TEXT NOT NULL DEFAULT '',
    verified_facts_json TEXT NOT NULL DEFAULT '[]',
    affiliate_url TEXT NOT NULL DEFAULT '',
    score INTEGER NOT NULL DEFAULT 0 CHECK(score BETWEEN 0 AND 25),
    review_status TEXT NOT NULL DEFAULT 'needs_review',
    risk_flags_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS products_source_url_unique
ON products(source_url) WHERE source_url <> '';

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    topic TEXT NOT NULL DEFAULT '',
    target_count INTEGER NOT NULL DEFAULT 100 CHECK(target_count BETWEEN 1 AND 100),
    pins_per_product INTEGER NOT NULL DEFAULT 3 CHECK(pins_per_product BETWEEN 1 AND 12),
    preferred_boards_json TEXT NOT NULL DEFAULT '[]',
    funnel TEXT NOT NULL DEFAULT 'consideration',
    audience TEXT NOT NULL DEFAULT 'Pinterest shoppers',
    copy_provider TEXT NOT NULL DEFAULT 'template',
    image_provider TEXT NOT NULL DEFAULT 'local_template',
    visual_templates_json TEXT NOT NULL DEFAULT '["apple_clean"]',
    require_review INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS creatives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    slot_index INTEGER NOT NULL,
    angle TEXT NOT NULL,
    visual_template TEXT NOT NULL,
    headline TEXT NOT NULL,
    bullets_json TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    alt_text TEXT NOT NULL,
    hashtags_json TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    board TEXT NOT NULL,
    destination_url TEXT NOT NULL,
    image_path TEXT NOT NULL DEFAULT '',
    generation_prompt TEXT NOT NULL DEFAULT '',
    duplicate_hash TEXT NOT NULL,
    quality_score INTEGER NOT NULL DEFAULT 0,
    risk_flags_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'generated',
    publish_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, slot_index),
    UNIQUE(duplicate_hash)
);

CREATE INDEX IF NOT EXISTS creatives_status_idx ON creatives(status);
CREATE INDEX IF NOT EXISTS creatives_campaign_idx ON creatives(campaign_id);

CREATE TABLE IF NOT EXISTS publish_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creative_id INTEGER NOT NULL UNIQUE REFERENCES creatives(id) ON DELETE CASCADE,
    publish_at TEXT,
    mode TEXT NOT NULL DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    browser_screenshot TEXT NOT NULL DEFAULT '',
    published_url TEXT NOT NULL DEFAULT '',
    published_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS publish_jobs_due_idx ON publish_jobs(status, publish_at);

CREATE TABLE IF NOT EXISTS analytics (
    creative_id INTEGER PRIMARY KEY REFERENCES creatives(id) ON DELETE CASCADE,
    impressions INTEGER NOT NULL DEFAULT 0,
    saves INTEGER NOT NULL DEFAULT 0,
    outbound_clicks INTEGER NOT NULL DEFAULT 0,
    pin_clicks INTEGER NOT NULL DEFAULT 0,
    outbound_ctr REAL NOT NULL DEFAULT 0,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
