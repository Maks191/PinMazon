from __future__ import annotations

import base64
import json
from pathlib import Path
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from openai import APIConnectionError, AuthenticationError, RateLimitError
from starlette.concurrency import run_in_threadpool

from pinmazon.compliance import ComplianceError
from pinmazon.links import build_affiliate_url
from pinmazon.schemas import PinCopy, ProductInput
from pinmazon.settings import Settings
from pinmazon.workflow import run_pin_job


PUBLIC_DIR = Path(__file__).resolve().parent / "public"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
MAX_UPLOAD_BYTES = 3 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}

app = FastAPI(
    title="PinMazon Cloud",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/privacy", response_class=HTMLResponse)
def privacy() -> str:
    return (TEMPLATE_DIR / "privacy.html").read_text(encoding="utf-8")


@app.get("/styles.css", include_in_schema=False)
def styles() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def javascript() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "app.js", media_type="text/javascript")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "generate_only", "manual_mode": "available"}


async def _read_product_image(product_image: UploadFile) -> bytes:
    if product_image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Upload a PNG, JPG, or WEBP product image.")
    image_bytes = await product_image.read(MAX_UPLOAD_BYTES + 1)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Product image is empty.")
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Product image must be 3 MB or smaller.")
    return image_bytes


def _execute_job(
    *,
    image_bytes: bytes,
    amazon_tracking_id: str,
    product_name: str,
    amazon_url: str,
    features: str,
    audience: str,
    cluster: str,
    style: str,
    use_ai_background: bool,
    openai_api_key: str = "",
    pin_copy: PinCopy | None = None,
) -> dict:
    destination_url = build_affiliate_url(
        amazon_url,
        amazon_tracking_id.strip(),
        "www.amazon.com",
    )
    with tempfile.TemporaryDirectory(prefix="pinmazon-") as temp_dir:
        root = Path(temp_dir)
        settings = Settings(
            _env_file=None,
            openai_api_key=openai_api_key,
            amazon_tracking_id=amazon_tracking_id.strip(),
            output_dir=str(root / "output"),
            history_file=str(root / "history.jsonl"),
            pinterest_token_file=str(root / "pinterest_token.json"),
        )
        product = ProductInput(
            product_name=product_name,
            amazon_url=amazon_url,
            destination_url=destination_url,
            features=features,
            audience=audience,
            cluster=cluster,
            style=style,
            board_id="",
            use_ai_background=use_ai_background,
        )
        result = run_pin_job(
            product=product,
            product_image_bytes=image_bytes,
            settings=settings,
            publish_now=False,
            pin_copy=pin_copy,
        )
        image_data = base64.b64encode(Path(result.image_path).read_bytes()).decode("ascii")
        metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
        metadata["image_path"] = "pin.png"
        metadata["generation_mode"] = "chatgpt_manual" if pin_copy else "openai_api"

    return {
        "image_base64": image_data,
        "metadata": metadata,
        "copy": result.pin_copy.model_dump(),
        "destination_url": destination_url,
        "published": False,
    }


def _parse_chatgpt_json(value: str) -> PinCopy:
    clean = value.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
    try:
        return PinCopy.model_validate(json.loads(clean))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="ChatGPT JSON is invalid or missing required fields.",
        ) from exc


@app.post("/api/generate")
async def generate(
    product_image: UploadFile = File(...),
    openai_api_key: str = Form(...),
    amazon_tracking_id: str = Form(...),
    product_name: str = Form(...),
    amazon_url: str = Form(...),
    features: str = Form(""),
    audience: str = Form("creators, remote workers, and tech buyers"),
    cluster: str = Form("Amazon Tech Finds"),
    style: str = Form("apple_clean"),
    use_ai_background: bool = Form(False),
) -> dict:
    api_key = openai_api_key.strip()
    if len(api_key) < 20:
        raise HTTPException(status_code=400, detail="Enter a valid OpenAI API key.")
    if not amazon_tracking_id.strip():
        raise HTTPException(status_code=400, detail="Amazon Tracking ID is required.")
    image_bytes = await _read_product_image(product_image)

    try:
        payload = await run_in_threadpool(
            _execute_job,
            image_bytes=image_bytes,
            amazon_tracking_id=amazon_tracking_id,
            product_name=product_name,
            amazon_url=amazon_url,
            features=features,
            audience=audience,
            cluster=cluster,
            style=style,
            use_ai_background=use_ai_background,
            openai_api_key=api_key,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail="OpenAI rejected this API key.") from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="OpenAI rate limit or account quota was reached.",
        ) from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=502, detail="Could not connect to OpenAI.") from exc
    except (ComplianceError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Generation failed. Check the supplied facts and try again.",
        ) from exc

    return payload


@app.post("/api/render-manual")
async def render_manual(
    product_image: UploadFile = File(...),
    amazon_tracking_id: str = Form(...),
    product_name: str = Form(...),
    amazon_url: str = Form(...),
    pin_copy_json: str = Form(...),
    features: str = Form(""),
    audience: str = Form("creators, remote workers, and tech buyers"),
    cluster: str = Form("Amazon Tech Finds"),
    style: str = Form("apple_clean"),
) -> dict:
    if not amazon_tracking_id.strip():
        raise HTTPException(status_code=400, detail="Amazon Tracking ID is required.")
    image_bytes = await _read_product_image(product_image)
    pin_copy = _parse_chatgpt_json(pin_copy_json)

    try:
        return await run_in_threadpool(
            _execute_job,
            image_bytes=image_bytes,
            amazon_tracking_id=amazon_tracking_id,
            product_name=product_name,
            amazon_url=amazon_url,
            features=features,
            audience=audience,
            cluster=cluster,
            style=style,
            use_ai_background=False,
            pin_copy=pin_copy,
        )
    except (ComplianceError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Rendering failed. Check the JSON and product image.",
        ) from exc
