# PinMazon Codex instructions

## Product goal
Maintain a reliable one-click Pinterest + Amazon affiliate content pipeline.
The system must optimize for outbound clicks and compliance, not visual novelty.

## Non-negotiable rules
1. Never scrape Amazon HTML as the primary product-data source.
2. Use Amazon Creators API / PA API only after credentials and permissions are confirmed.
3. Never invent price, discount, rating, review count, compatibility, or technical specifications.
4. Keep the real product image as the source of truth.
5. AI may generate a background, never silently redesign the product.
6. Every affiliate description must contain: "Affiliate links may earn commission."
7. Never publish if an Amazon destination lacks a valid tracking tag, unless explicitly configured.
8. Use Pinterest API or current official bulk-upload flow; do not automate browser clicking as the main path.
9. Keep a dry-run mode and an audit log.
10. Prevent duplicate publishes by default.
11. Use 1000x1500 / 2:3 assets and mobile-readable typography.
12. Preserve the product as the visual hero: one headline, two bullets maximum.

## Engineering standards
- Python 3.11+
- Type hints and Pydantic models
- Secrets only in environment variables or local token files excluded from Git
- Timeouts and readable errors on all network calls
- Idempotent workflow
- Tests for links, compliance rules, renderer dimensions, and Pinterest payload shape
- Do not commit generated output, tokens, or .env

## Definition of done for a feature
- implementation;
- tests;
- README update;
- safe failure path;
- no new unsupported product claims;
- no regression in generate-only mode.
