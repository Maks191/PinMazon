from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from pinmazon.compliance import validate_copy
from pinmazon.schemas import PinCopy
from pinmazon_core.batch import BatchPreflightError, generate_batch
from pinmazon_core.compliance import move_creatives_to_ready
from pinmazon_core.db import Database
from pinmazon_core.image_providers import LocalTemplateProvider
from pinmazon_core.product_sources import ProductImporter
from pinmazon_core.repositories import Repository
from pinmazon_core.schemas import CampaignCreate
from pinmazon_core.settings import CoreSettings


st.set_page_config(page_title="PinMazon — Pin Studio", page_icon="🎨", layout="wide")


@st.cache_resource
def load_resources(data_dir: str):
    settings = CoreSettings(pinmazon_data_dir=data_dir)
    database = Database(settings)
    repository = Repository(database)
    return settings, database, repository, ProductImporter(repository, settings)


base_settings = CoreSettings()
settings, database, repository, importer = load_resources(str(base_settings.data_dir))

st.title("Pin Studio")
st.caption("Товары → локальный SEO package → 1000×1500 PNG → review → ready. Публикации здесь нет.")

with st.sidebar:
    st.subheader("Локальное хранилище")
    st.code(str(settings.data_dir))
    st.write("SQLite:", str(settings.database_path))
    st.write("Amazon tag:", "✅" if settings.amazon_tracking_id else "⚠️ не задан")
    st.info("Milestone B: Template copy + Local renderer. OpenAI API не нужен.")

campaign_tab, products_tab, batch_tab, review_tab = st.tabs(
    ["1. Кампании", "2. Товары", "3. Generate Batch", "4. Review Table"]
)

with campaign_tab:
    st.subheader("Новая кампания")
    with st.form("create_campaign", clear_on_submit=True):
        name = st.text_input("Campaign name", placeholder="Clean Desk — July")
        topic = st.text_input("Product topic", placeholder="Clean desk setup gadgets")
        col_a, col_b, col_c = st.columns(3)
        target_count = col_a.number_input("Target creatives", 1, 100, 100)
        pins_per_product = col_b.number_input("Pins per product", 1, 12, 3)
        funnel = col_c.selectbox("Funnel", ["consideration", "discovery", "conversion"])
        audience = st.text_input("Audience", "creators, remote workers, and tech buyers")
        boards_text = st.text_area(
            "Pinterest boards — по одной на строке",
            placeholder="Clean Desk Setup\nAmazon Tech Finds",
        )
        templates = st.multiselect(
            "Visual templates",
            ["apple_clean", "luxury_editorial", "viral_useful", "creator_setup", "warm_lifestyle"],
            default=["apple_clean", "creator_setup", "warm_lifestyle"],
        )
        submitted = st.form_submit_button("Создать кампанию", type="primary")
    if submitted:
        boards = [line.strip() for line in boards_text.splitlines() if line.strip()]
        if not boards:
            st.error("Добавьте хотя бы одну реальную Pinterest board.")
        else:
            campaign_id = repository.create_campaign(
                CampaignCreate(
                    name=name,
                    topic=topic,
                    target_count=int(target_count),
                    pins_per_product=int(pins_per_product),
                    preferred_boards=boards,
                    funnel=funnel,
                    audience=audience,
                    copy_provider="template",
                    image_provider="local_template",
                    visual_templates=templates or ["apple_clean"],
                )
            )
            st.success(f"Кампания #{campaign_id} создана.")

    campaigns = repository.list_campaigns()
    if campaigns:
        st.dataframe(
            pd.DataFrame(campaigns)[
                ["id", "name", "topic", "target_count", "creative_count", "ready_count", "status"]
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Пока нет кампаний.")

with products_tab:
    manual_tab, import_tab, review_products_tab = st.tabs(
        ["Добавить товар", "CSV / XLSX", "Product Review"]
    )
    with manual_tab:
        st.warning(
            "Программа не читает Amazon HTML. Нужны название, Amazon/SiteStripe ссылка и реальное фото товара."
        )
        with st.form("manual_product", clear_on_submit=True):
            product_name = st.text_input("Product name")
            source_url = st.text_input("Amazon product URL")
            affiliate_url = st.text_input(
                "Affiliate URL",
                help="Можно оставить пустым, если AMAZON_TRACKING_ID уже задан в .env.",
            )
            image = st.file_uploader("Real product image", type=["png", "jpg", "jpeg", "webp"])
            col_a, col_b = st.columns(2)
            category = col_a.text_input("Category", "Desk accessories")
            product_audience = col_b.text_input("Audience", "creators and remote workers")
            facts = st.text_area("Verified facts — по одной строке")
            score = st.slider("Pinterest potential score", 0, 25, 15)
            add_product = st.form_submit_button("Сохранить товар", type="primary")
        if add_product:
            try:
                image_path = str(importer.save_uploaded_image(image.name, image.getvalue())) if image else ""
                product_id = importer.import_row(
                    {
                        "Product": product_name,
                        "Product URL": source_url,
                        "Affiliate URL": affiliate_url,
                        "Image Path": image_path,
                        "Category": category,
                        "Audience": product_audience,
                        "Verified Facts": facts,
                        "Score": score,
                    },
                    source="manual",
                )
                st.success(f"Товар #{product_id} сохранён для проверки.")
            except Exception as exc:
                st.error(str(exc))

    with import_tab:
        st.write(
            "Колонки: Product, Product URL, Affiliate URL, Image URL или Local Image, "
            "Category, Audience, Verified Facts. Image URL должен вести прямо на PNG/JPG/WEBP."
        )
        uploaded_table = st.file_uploader("CSV или XLSX", type=["csv", "xlsx", "xlsm"])
        if st.button("Импортировать таблицу", disabled=uploaded_table is None):
            try:
                ids = importer.import_table(io.BytesIO(uploaded_table.getvalue()), uploaded_table.name)
                st.success(f"Импортировано товаров: {len(ids)}")
            except Exception as exc:
                st.error(str(exc))

    with review_products_tab:
        products = repository.list_products()
        if products:
            product_frame = pd.DataFrame(
                [
                    {
                        "Select": False,
                        "ID": row["id"],
                        "Product": row["product_name"],
                        "ASIN": row["asin"] or "",
                        "Category": row["category"],
                        "Image": row["image_path"],
                        "Score": row["score"],
                        "Affiliate URL": row["affiliate_url"],
                        "Verified facts": "; ".join(row["verified_facts"]),
                        "Risk flags": ", ".join(row["risk_flags"]),
                        "Status": row["review_status"],
                    }
                    for row in products
                ]
            )
            edited_products = st.data_editor(
                product_frame,
                hide_index=True,
                use_container_width=True,
                disabled=[column for column in product_frame.columns if column != "Select"],
                key="product_review_editor",
            )
            selected_ids = edited_products.loc[edited_products["Select"], "ID"].astype(int).tolist()
            approve_col, reject_col = st.columns(2)
            if approve_col.button("Approve selected", disabled=not selected_ids, type="primary"):
                repository.set_product_status(selected_ids, "approved")
                st.rerun()
            if reject_col.button("Reject selected", disabled=not selected_ids):
                repository.set_product_status(selected_ids, "rejected")
                st.rerun()
        else:
            st.info("Сначала добавьте товары.")

with batch_tab:
    campaigns = repository.list_campaigns()
    approved_products = repository.list_products(statuses=["approved"])
    if not campaigns:
        st.info("Сначала создайте кампанию.")
    elif not approved_products:
        st.info("Сначала одобрите хотя бы один товар.")
    else:
        campaign_labels = {f"#{row['id']} — {row['name']}": row for row in campaigns}
        selected_campaign_label = st.selectbox("Campaign", list(campaign_labels), key="batch_campaign")
        selected_campaign = campaign_labels[selected_campaign_label]
        product_frame = pd.DataFrame(
            [
                {
                    "Select": True,
                    "ID": row["id"],
                    "Product": row["product_name"],
                    "Category": row["category"],
                    "Score": row["score"],
                }
                for row in approved_products
            ]
        )
        selected_products = st.data_editor(
            product_frame,
            hide_index=True,
            use_container_width=True,
            disabled=["ID", "Product", "Category", "Score"],
            key="batch_products_editor",
        )
        product_ids = selected_products.loc[selected_products["Select"], "ID"].astype(int).tolist()
        recommended = max(1, (int(selected_campaign["target_count"]) + 2) // 3)
        if len(product_ids) < recommended:
            st.warning(
                f"Для разнообразия лучше минимум {recommended} товаров. Сейчас {len(product_ids)}; "
                "программа создаст варианты, но контент будет повторяться по товарам."
            )
        existing = repository.creative_count(int(selected_campaign["id"]))
        st.write(f"Готово записей: {existing} / {selected_campaign['target_count']}")
        if st.button("Generate / Resume Batch", type="primary", disabled=not product_ids):
            progress_bar = st.progress(existing / int(selected_campaign["target_count"]))
            status_line = st.empty()

            def update_progress(done: int, total: int) -> None:
                progress_bar.progress(done / total)
                status_line.write(f"Рендер {done} / {total}")

            try:
                created = generate_batch(
                    repository=repository,
                    settings=settings,
                    campaign_id=int(selected_campaign["id"]),
                    product_ids=product_ids,
                    progress=update_progress,
                )
                total = repository.creative_count(int(selected_campaign["id"]))
                st.success(f"Создано новых: {created}. Всего: {total}.")
            except BatchPreflightError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.exception(exc)

with review_tab:
    campaigns = repository.list_campaigns()
    if not campaigns:
        st.info("Пока нет кампаний.")
    else:
        campaign_labels = {f"#{row['id']} — {row['name']}": row for row in campaigns}
        selected_label = st.selectbox("Campaign", list(campaign_labels), key="review_campaign")
        campaign = campaign_labels[selected_label]
        creatives = repository.list_creatives(campaign_id=int(campaign["id"]))
        if not creatives:
            st.info("В этой кампании ещё нет creatives.")
        else:
            frame = pd.DataFrame(
                [
                    {
                        "Select": False,
                        "ID": row["id"],
                        "Preview": row["image_path"],
                        "Product": row["product_name"],
                        "Angle": row["angle"],
                        "Headline": row["headline"],
                        "Bullets": " | ".join(row["bullets"]),
                        "Title": row["title"],
                        "Description": row["description"],
                        "Alt text": row["alt_text"],
                        "Board": row["board"],
                        "Destination": row["destination_url"],
                        "Quality": row["quality_score"],
                        "Risk flags": ", ".join(row["risk_flags"]),
                        "Status": row["status"],
                    }
                    for row in creatives
                ]
            )
            editor = st.data_editor(
                frame,
                hide_index=True,
                use_container_width=True,
                height=560,
                disabled=[
                    "ID",
                    "Preview",
                    "Product",
                    "Angle",
                    "Destination",
                    "Quality",
                    "Risk flags",
                    "Status",
                ],
                key="creative_review_editor",
            )
            selected_ids = editor.loc[editor["Select"], "ID"].astype(int).tolist()
            save_col, approve_col, reject_col, ready_col = st.columns(4)
            if save_col.button("Save edits + re-render"):
                changed = 0
                original_by_id = {int(row["id"]): row for row in creatives}
                provider = LocalTemplateProvider(settings.brand_name)
                try:
                    for row in editor.to_dict("records"):
                        creative_id = int(row["ID"])
                        original = original_by_id[creative_id]
                        bullets = [part.strip() for part in str(row["Bullets"]).split("|") if part.strip()]
                        candidate = validate_copy(
                            PinCopy(
                                headline=str(row["Headline"]),
                                bullets=bullets,
                                title=str(row["Title"]),
                                description=str(row["Description"]),
                                alt_text=str(row["Alt text"]),
                                short_description=original["title"][:75],
                                hashtags=original["hashtags"],
                                keywords=original["keywords"],
                                visual_prompt="Local template background only",
                            )
                        )
                        fields = {
                            "headline": candidate.headline,
                            "bullets_json": json.dumps(candidate.bullets),
                            "title": candidate.title,
                            "description": candidate.description,
                            "alt_text": candidate.alt_text,
                            "board": str(row["Board"]).strip(),
                            "status": "needs_review",
                        }
                        if (
                            candidate.headline != original["headline"]
                            or candidate.bullets != original["bullets"]
                            or candidate.title != original["title"]
                            or candidate.description != original["description"]
                            or candidate.alt_text != original["alt_text"]
                            or fields["board"] != original["board"]
                        ):
                            repository.update_creative_fields(creative_id, fields)
                            provider.create(
                                product_image=Path(original["product_image_path"]),
                                pin_copy=candidate,
                                visual_template=original["visual_template"],
                                output_path=Path(original["image_path"]),
                            )
                            changed += 1
                    st.success(f"Обновлено и перерисовано: {changed}")
                except Exception as exc:
                    st.error(str(exc))
            if approve_col.button("Approve selected", type="primary", disabled=not selected_ids):
                repository.set_creative_status(selected_ids, "approved")
                st.rerun()
            if reject_col.button("Reject selected", disabled=not selected_ids):
                repository.set_creative_status(selected_ids, "rejected")
                st.rerun()
            if ready_col.button("Send selected to ready", disabled=not selected_ids):
                failures = move_creatives_to_ready(repository, selected_ids)
                if failures:
                    st.error("Quality gates не пройдены:\n" + "\n".join(
                        f"#{key}: {', '.join(value)}" for key, value in failures.items()
                    ))
                else:
                    st.success("Выбранные creatives добавлены в очередь Publisher.")
                    st.rerun()

            csv_data = frame.drop(columns=["Select"]).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Export campaign CSV",
                data=csv_data,
                file_name=f"campaign-{campaign['id']}-creatives.csv",
                mime="text/csv",
            )
            if selected_ids:
                st.subheader("Preview selected")
                for creative in [row for row in creatives if int(row["id"]) in selected_ids][:6]:
                    st.image(creative["image_path"], caption=f"#{creative['id']} — {creative['title']}", width=360)
