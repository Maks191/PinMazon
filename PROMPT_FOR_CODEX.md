# Master prompt for Codex

Open this repository and act as a senior automation engineer, Pinterest affiliate strategist, and QA owner.

First inspect `README_RU.md`, `AGENTS.md`, and the existing code. Do not rewrite the project blindly.

Goal: turn the MVP into a reliable local-first and later cloud-deployable one-click pipeline:

Amazon product input
→ verified product data
→ SEO package
→ exact product-based 1000×1500 creative
→ compliance validation
→ Pinterest board selection
→ publish or schedule
→ analytics history
→ winner-based variations.

Priorities:
1. Run the current app and fix every startup/runtime issue.
2. Add pytest coverage for:
   - Amazon ASIN extraction and affiliate links;
   - compliance rejection;
   - renderer size;
   - duplicate prevention;
   - Pinterest request payload.
3. Add an adapter interface for Amazon Creators API / PA API.
   Do not scrape product pages.
   If credentials are missing, keep the current manual-image workflow.
4. Add a SQLite products/jobs/pins database.
5. Add a queue and scheduler.
6. Add a batch screen: generate 3 distinct angles per product but publish at controlled intervals.
7. Add Pinterest analytics ingestion and a weekly winner report.
8. Add an automatic variant generator that only remixes proven winners.
9. Keep AI-generated backgrounds optional. Preserve the real product image.
10. Add clear onboarding and a diagnostics page for keys, scopes, boards, link tags, and API errors.

Before changing API calls, check current official OpenAI, Pinterest, and Amazon documentation.
Never guess endpoint fields or policy requirements.

Work in small commits. After each milestone:
- run tests;
- run the app;
- report what works;
- list credentials or approvals still needed;
- show exact next command.
