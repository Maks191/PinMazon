from __future__ import annotations

import pandas as pd
import streamlit as st

from pinmazon_core.db import Database
from pinmazon_core.repositories import Repository
from pinmazon_core.settings import CoreSettings


st.set_page_config(page_title="PinMazon — Pin Publisher", page_icon="📌", layout="wide")


@st.cache_resource
def load_resources(data_dir: str):
    settings = CoreSettings(pinmazon_data_dir=data_dir)
    database = Database(settings)
    return settings, database, Repository(database)


base_settings = CoreSettings()
settings, database, repository = load_resources(str(base_settings.data_dir))
queue = repository.queued_creatives()

st.title("Pin Publisher")
st.caption("Безопасная очередь из Pin Studio. Автоматическая публикация пока намеренно выключена.")

ready_count = len(queue)
today_col, next_col, limit_col, queue_col = st.columns(4)
today_col.metric("Published today", 0)
next_col.metric("Next job", "Not scheduled")
limit_col.metric("Daily limit", "Not enabled")
queue_col.metric("Ready queue", ready_count)

with st.sidebar:
    st.subheader("Shared storage")
    st.code(str(settings.data_dir))
    st.write("SQLite:", str(settings.database_path))
    st.write("Browser profile:", str(settings.browser_profile_dir))
    st.warning("Milestone B: Publisher is read-only. Ни одного Pin не будет опубликовано.")

queue_tab, diagnostics_tab = st.tabs(["Ready Queue", "Diagnostics"])

with queue_tab:
    if queue:
        frame = pd.DataFrame(
            [
                {
                    "Job": row["job_id"],
                    "Creative": row["id"],
                    "Campaign": row["campaign_name"],
                    "Product": row["product_name"],
                    "Angle": row["angle"],
                    "Board": row["board"],
                    "Title": row["title"],
                    "Destination": row["destination_url"],
                    "Image": row["image_path"],
                    "Creative status": row["status"],
                    "Job status": row["job_status"],
                }
                for row in queue
            ]
        )
        st.dataframe(frame, hide_index=True, use_container_width=True, height=560)
        st.download_button(
            "Export ready queue CSV",
            data=frame.to_csv(index=False).encode("utf-8-sig"),
            file_name="pinmazon-ready-queue.csv",
            mime="text/csv",
        )
    else:
        st.info("Очередь пустая. В Pin Studio одобрите creatives и отправьте их в ready.")

    action_cols = st.columns(4)
    action_cols[0].button("Open Pinterest Session", disabled=True)
    action_cols[1].button("Publish Next", disabled=True)
    action_cols[2].button("Start Worker", disabled=True)
    action_cols[3].button("Run Diagnostics", disabled=True)
    st.caption("Эти кнопки появятся только после Milestone D/E и отдельного dry-run теста.")

with diagnostics_tab:
    st.success("SQLite migration: OK")
    st.write("Database exists:", database.path.exists())
    st.write("Product assets:", settings.product_assets_dir)
    st.write("Creative assets:", settings.creative_assets_dir)
    st.write("Debug screenshots:", settings.debug_dir)
    st.write("Pinterest API credentials required now:", "No")
    st.write("Playwright installed/enabled:", "No — planned for Milestone E")
