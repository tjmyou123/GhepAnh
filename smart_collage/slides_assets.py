"""Helper nhung anh dung cho trinh chieu tu dong (HTML/PPTX)."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image

# Anh nhung vao HTML duoc thu nho ve canh dai toi da nay (du net cho 4K)
HTML_MAX_PX = 2200
HTML_JPEG_QUALITY = 87


def _flatten_rgb(img: Image.Image) -> Image.Image:
    """Chuyen ve RGB, dat anh trong suot len nen trang."""
    if img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info
    ):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info
    )


def _downscale(img: Image.Image, max_px: int) -> Image.Image:
    if max(img.size) <= max_px:
        return img
    k = max_px / max(img.size)
    return img.resize(
        (max(1, round(img.width * k)), max(1, round(img.height * k))),
        Image.Resampling.LANCZOS,
    )


def image_bytes_for_html(path: Path, max_px: int = HTML_MAX_PX) -> tuple[bytes, str]:
    """Doc anh tu dia -> (bytes, mime) da toi uu de nhung vao HTML.

    GIF/SVG giu nguyen (bao toan animation/vector); PNG trong suot giu PNG;
    con lai chuyen JPEG va thu nho neu qua lon.
    """
    ext = path.suffix.lower()
    if ext == ".svg":
        return path.read_bytes(), "image/svg+xml"
    if ext == ".gif":
        return path.read_bytes(), "image/gif"

    from PIL import ImageOps
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        keep_alpha = _has_alpha(im)
        im = _downscale(im, max_px)
        buf = BytesIO()
        if keep_alpha:
            im.convert("RGBA").save(buf, "PNG", optimize=True)
            return buf.getvalue(), "image/png"
        _flatten_rgb(im).save(buf, "JPEG", quality=HTML_JPEG_QUALITY,
                              optimize=True, subsampling=1)
        return buf.getvalue(), "image/jpeg"


def data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def pil_to_stream(img: Image.Image, jpeg_quality: int = 92) -> BytesIO:
    buf = BytesIO()
    _flatten_rgb(img).save(buf, "JPEG", quality=jpeg_quality,
                           optimize=True, subsampling=1)
    buf.seek(0)
    return buf
