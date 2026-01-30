"""
Background removal using rembg (u2net model).
Maintains original dimensions and quality; outputs PNG with transparency.
"""
import io
import logging
from typing import Tuple

from PIL import Image
from rembg.bg import remove as rembg_remove, new_session

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

# Reuse u2net session for product images (lazy init)
_u2net_session = None


def _get_u2net_session():
    global _u2net_session
    if _u2net_session is None:
        _u2net_session = new_session("u2net")
    return _u2net_session


def remove_background(image_bytes: bytes) -> Tuple[bytes, int, int]:
    """
    Remove background from image using rembg with u2net model.
    Returns (processed_png_bytes, width, height).
    """
    try:
        input_image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        logger.exception("Failed to open image")
        raise ValueError(f"Invalid or corrupted image: {e!s}") from e

    width, height = input_image.size

    try:
        output_image = rembg_remove(input_image, session=_get_u2net_session())
    except Exception as e:
        logger.exception("Background removal failed")
        raise RuntimeError(f"Processing error: {e!s}") from e

    if output_image is None:
        raise RuntimeError("Background removal produced no output")

    # Ensure PNG with transparency
    if output_image.mode != "RGBA":
        output_image = output_image.convert("RGBA")

    out_buffer = io.BytesIO()
    output_image.save(out_buffer, format="PNG", optimize=True)
    out_buffer.seek(0)
    return out_buffer.getvalue(), width, height
