import io
from dataclasses import dataclass

from fastapi import status
from PIL import Image, UnidentifiedImageError

from app.core.exceptions import AppError

# Formats accepted from staff uploads, keyed by what Pillow detects from the file's bytes.
ALLOWED_FORMATS = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}
MAX_PIXELS = 40_000_000  # about 8000 x 5000


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    mime_type: str
    extension: str
    width: int
    height: int


def process_image(raw: bytes, max_bytes: int) -> ProcessedImage:
    """Validate an uploaded image by its content (not its name or declared type) and strip metadata.

    Re-encoding drops EXIF data such as GPS location, and a file that only pretends to be an image
    fails to decode.
    """
    if not raw:
        raise AppError("invalid_image", "The file is empty")
    if len(raw) > max_bytes:
        raise AppError(
            "image_too_large",
            f"Images must be {max_bytes // (1024 * 1024)} MB or smaller",
            status.HTTP_413_CONTENT_TOO_LARGE,
        )
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            fmt = probe.format or ""
            probe.verify()
        if fmt not in ALLOWED_FORMATS:
            raise AppError("unsupported_image", "Upload a JPEG, PNG or WebP image")
        with Image.open(io.BytesIO(raw)) as img:
            if img.width * img.height > MAX_PIXELS:
                raise AppError("image_too_large", "Image dimensions are too large")
            img.load()
            mime, ext = ALLOWED_FORMATS[fmt]
            out = io.BytesIO()
            if fmt == "JPEG":
                img.convert("RGB").save(out, "JPEG", quality=90, optimize=True)
            else:
                img.save(out, fmt)
            return ProcessedImage(out.getvalue(), mime, ext, img.width, img.height)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise AppError("invalid_image", "The file is not a valid image") from exc
