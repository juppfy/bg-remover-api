"""
Background Removal API - FastAPI application.
Removes backgrounds from product images and uploads results to storage.
"""
import logging
import time

import httpx
from dotenv import load_dotenv

load_dotenv()
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from utils.auth import verify_api_key
from utils.image_processor import (
    ALLOWED_CONTENT_TYPES,
    MAX_IMAGE_SIZE_BYTES,
    remove_background,
)
from utils.storage import upload_to_bucket

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Background Removal API",
    description="Remove backgrounds from product images and get a public URL.",
    version="1.0.0",
)

# Normalize path: collapse repeated slashes so //api/v1/... matches /api/v1/...
@app.middleware("http")
async def normalize_path(request, call_next):
    if "//" in request.url.path:
        path = "/" + "/".join(p for p in request.url.path.split("/") if p)
        request.scope["path"] = path
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api/v1", tags=["remove-bg"])


class UrlRequest(BaseModel):
    image_url: HttpUrl


def _success_response(
    original_url: str | None,
    processed_url: str,
    processing_time: float,
    width: int,
    height: int,
) -> dict:
    return {
        "success": True,
        "original_url": original_url or "",
        "processed_url": processed_url,
        "processing_time": round(processing_time, 2),
        "image_dimensions": {"width": width, "height": height},
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Return {"error": "message"} for all HTTP errors."""
    d = exc.detail
    if isinstance(d, dict) and "error" in d:
        msg = d["error"]
    elif isinstance(d, list) and d:
        msg = d[0].get("msg", str(d[0])) if isinstance(d[0], dict) else str(d[0])
    else:
        msg = d
    return JSONResponse(status_code=exc.status_code, content={"error": str(msg)})


@router.post("/remove-bg/binary")
async def remove_bg_binary(
    image: UploadFile = File(..., alias="image"),
    _: str = Depends(verify_api_key),
):
    """
    Accept image as multipart/form-data (field name: image).
    Supported: PNG, JPG, JPEG, WEBP. Max 10MB.
    """
    if not image.content_type or image.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Use PNG, JPG, JPEG, or WEBP.",
        )

    try:
        raw = await image.read()
    except Exception as e:
        logger.exception("Failed to read uploaded file")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read image data.",
        )

    if len(raw) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Maximum size is 10MB.",
        )

    if len(raw) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image file.",
        )

    start = time.perf_counter()
    try:
        processed_bytes, width, height = remove_background(raw)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.exception("Processing error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    try:
        processed_url = upload_to_bucket(processed_bytes, content_type="image/png")
    except RuntimeError as e:
        logger.exception("Storage upload error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    elapsed = time.perf_counter() - start
    return _success_response(
        original_url=None,
        processed_url=processed_url,
        processing_time=elapsed,
        width=width,
        height=height,
    )


@router.post("/remove-bg/url")
async def remove_bg_url(
    body: UrlRequest,
    _: str = Depends(verify_api_key),
):
    """
    Accept JSON body with image_url. Download image, remove background, upload, return URL.
    """
    url = str(body.image_url)
    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            raw = resp.content
    except httpx.HTTPStatusError as e:
        logger.warning("Failed to download image: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to download image from URL.",
        )
    except Exception as e:
        logger.warning("Download error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to download image from URL.",
        )

    if len(raw) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Maximum size is 10MB.",
        )

    if len(raw) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Downloaded image is empty.",
        )

    try:
        processed_bytes, width, height = remove_background(raw)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.exception("Processing error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    try:
        processed_url = upload_to_bucket(processed_bytes, content_type="image/png")
    except RuntimeError as e:
        logger.exception("Storage upload error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    elapsed = time.perf_counter() - start
    return _success_response(
        original_url=url,
        processed_url=processed_url,
        processing_time=elapsed,
        width=width,
        height=height,
    )


app.include_router(router)


# Top-level health for Railway (root path)
@app.get("/health")
async def root_health():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {
        "message": "Background Removal API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "remove_bg_binary": "POST /api/v1/remove-bg/binary",
            "remove_bg_url": "POST /api/v1/remove-bg/url",
        },
    }


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
