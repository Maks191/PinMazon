from __future__ import annotations

from pathlib import Path

import streamlit as st

from pinmazon.links import build_affiliate_url
from pinmazon.pinterest import PinterestClient
from pinmazon.schemas import ProductInput
from pinmazon.settings import Settings
from pinmazon.workflow import run_pin_job


st.set_page_config(
    page_title="PinMazon One-Click",
    page_icon="📌",
    layout="wide",
)

settings = Settings()

st.title("PinMazon One-Click")
st.caption("Product image + verified facts → Pinterest pin → SEO metadata → optional direct publish")

with st.sidebar:
    st.subheader("Connection")
    st.write("OpenAI:", "✅" if settings.openai_api_key else "❌")
    st.write("Pinterest token:", "✅" if settings.token_path.exists() else "❌")
    publish_mode = st.selectbox(
        "Action",
        options=["Generate only", "Generate + publish now"],
        index=1 if settings.default_publish_mode == "publish_now" else 0,
    )
    force_duplicate = st.checkbox("Allow intentional duplicate", value=False)

boards: list[dict] = []
if settings.token_path.exists():
    try:
        boards = PinterestClient(settings).list_boards()
    except Exception as exc:
        st.sidebar.warning(f"Could not load boards: {exc}")

left, right = st.columns([1.05, 0.95])

def sync_destination_url() -> None:
    amazon_value = st.session_state.get("amazon_url", "")
    if amazon_value:
        st.session_state["destination_url"] = build_affiliate_url(
            amazon_value,
            settings.amazon_tracking_id,
            settings.amazon_marketplace_host,
        )


with left:
    product_name = st.text_input("Product name")
    amazon_url = st.text_input(
        "Amazon product URL",
        key="amazon_url",
        on_change=sync_destination_url,
    )
    destination_url = st.text_input(
        "Destination / affiliate link",
        key="destination_url",
        help="Prefer a valid Amazon SiteStripe/Special Link or your own landing page.",
    )
    product_image = st.file_uploader(
        "Product image",
        type=["png", "jpg", "jpeg", "webp"],
    )
    image_url = st.text_input("Or direct product image URL")
    features = st.text_area(
        "Verified facts / useful benefits",
        height=150,
        placeholder="Only facts you have verified. Leave blank rather than inventing specs.",
    )

with right:
    audience = st.text_input("Audience", value="creators, remote workers, and tech buyers")
    cluster = st.selectbox(
        "Cluster",
        [
            "Clean Desk Setup Gadgets",
            "Laptop Accessories and Desk Setup",
            "Smart Home Gadgets",
            "Creator Gear for Photo and Video",
            "Travel Creator Cameras",
            "FPV Drones and Aerial Gear",
            "Amazon Tech Finds",
            "Tech Gifts for Creators",
        ],
    )
    style = st.selectbox(
        "Visual style",
        ["apple_clean", "luxury_editorial", "viral_useful", "creator_setup", "warm_lifestyle"],
    )
    use_ai_background = st.checkbox(
        "Generate AI background",
        value=False,
        help="The real product image is composited on top. Pinterest AI_MODIFIED disclosure is sent.",
    )

    if boards:
        labels = {
            f"{board.get('name', 'Unnamed')} — {board.get('id')}": board
            for board in boards
        }
        selected = st.selectbox("Pinterest board", list(labels))
        board = labels[selected]
        board_id = board["id"]
        board_name = board.get("name", "")
    else:
        board_id = st.text_input(
            "Pinterest board ID (required only for publish)",
            value=settings.pinterest_default_board_id,
        )
        board_name = st.text_input("Board name (optional)")

button_label = "Generate + Publish" if publish_mode == "Generate + publish now" else "Generate Pin Pack"
clicked = st.button(button_label, type="primary", use_container_width=True)

if clicked:
    try:
        product = ProductInput(
            product_name=product_name,
            amazon_url=amazon_url,
            destination_url=destination_url,
            image_url=image_url,
            features=features,
            audience=audience,
            cluster=cluster,
            style=style,
            board_id=board_id,
            board_name=board_name,
            use_ai_background=use_ai_background,
        )
        with st.spinner("Creating pin package..."):
            result = run_pin_job(
                product=product,
                product_image_bytes=product_image.getvalue() if product_image else None,
                settings=settings,
                publish_now=publish_mode == "Generate + publish now",
                force_duplicate=force_duplicate,
            )

        st.success("Published." if result.published else "Pin package generated.")
        st.image(result.image_path, caption=result.pin_copy.title, width=500)
        st.subheader("Pinterest metadata")
        st.write("**Headline:**", result.pin_copy.headline)
        st.write("**Bullets:**", " · ".join(result.pin_copy.bullets))
        st.write("**Title:**", result.pin_copy.title)
        st.write("**Description:**", result.pin_copy.description)
        st.write("**ALT:**", result.pin_copy.alt_text)
        st.write("**Hashtags:**", " ".join(result.pin_copy.hashtags))
        if result.pin_id:
            st.write("**Pinterest Pin ID:**", result.pin_id)
        st.download_button(
            "Download pin PNG",
            data=Path(result.image_path).read_bytes(),
            file_name=Path(result.image_path).name,
            mime="image/png",
        )
        st.download_button(
            "Download metadata JSON",
            data=Path(result.metadata_path).read_bytes(),
            file_name=Path(result.metadata_path).name,
            mime="application/json",
        )
    except Exception as exc:
        st.exception(exc)
