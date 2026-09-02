"""Theme trang tri cho anh ghep: mau nen, gradient, bo goc, do bong.

Moi theme la mot dict:
    bg          : mau nen phang "#RRGGBB", hoac None neu dung gradient
    gradient    : (mau_tren, mau_duoi) — nen chuyen sac doc, de len tren bg
    corner_pct  : bo goc moi o anh, tinh theo % canh ngan cua o (0 = vuong)
    shadow      : do bong mem duoi moi o anh (True/False)
    margin      : khoang cach goi y giua cac anh (px, GUI/CLI co the ghi de)
    outer       : le ngoai goi y (px)
"""

from __future__ import annotations

from PIL import Image

THEMES = {
    "classic": {
        "label": "Cổ điển — nền trắng phẳng",
        "bg": "#FFFFFF", "gradient": None,
        "corner_pct": 0.0, "shadow": False,
        "margin": 4, "outer": 0,
    },
    "modern-light": {
        "label": "Hiện đại sáng — bo góc, bóng đổ, nền xám nhạt",
        "bg": None, "gradient": ("#F8FAFC", "#E2E8F0"),
        "corner_pct": 6.0, "shadow": True,
        "margin": 10, "outer": 16,
    },
    "modern-dark": {
        "label": "Hiện đại tối — hợp slide nền đen",
        "bg": None, "gradient": ("#1E293B", "#0F172A"),
        "corner_pct": 6.0, "shadow": True,
        "margin": 10, "outer": 16,
    },
    "boardroom": {
        "label": "Báo cáo — xanh navy chuyên nghiệp",
        "bg": None, "gradient": ("#16324F", "#0B1F33"),
        "corner_pct": 3.0, "shadow": True,
        "margin": 8, "outer": 20,
    },
    "cream": {
        "label": "Kem ấm — hợp polaroid/kỷ niệm",
        "bg": None, "gradient": ("#F5F0E6", "#E8DFCC"),
        "corner_pct": 0.0, "shadow": False,
        "margin": 12, "outer": 18,
    },
    "gallery-black": {
        "label": "Triển lãm — nền đen tuyền, viền mảnh",
        "bg": "#000000", "gradient": None,
        "corner_pct": 0.0, "shadow": False,
        "margin": 6, "outer": 24,
    },
    "sunset": {
        "label": "Hoàng hôn — cam hồng ấm áp",
        "bg": None, "gradient": ("#FDBA74", "#DB2777"),
        "corner_pct": 6.0, "shadow": True,
        "margin": 10, "outer": 18,
    },
    "ocean": {
        "label": "Đại dương — xanh biển sâu",
        "bg": None, "gradient": ("#38BDF8", "#1E3A8A"),
        "corner_pct": 6.0, "shadow": True,
        "margin": 10, "outer": 18,
    },
    "forest": {
        "label": "Rừng xanh — lục đậm sang trọng",
        "bg": None, "gradient": ("#166534", "#052E16"),
        "corner_pct": 4.0, "shadow": True,
        "margin": 8, "outer": 20,
    },
    "pastel": {
        "label": "Pastel — hồng kem dịu nhẹ",
        "bg": None, "gradient": ("#FDE2E4", "#DDE7F0"),
        "corner_pct": 8.0, "shadow": True,
        "margin": 12, "outer": 20,
    },
}

DEFAULT_THEME = "classic"


def get_theme(key: str) -> dict:
    if key not in THEMES:
        raise KeyError(
            f"Theme khong hop le: {key}. Chon mot trong: {', '.join(THEMES)}"
        )
    return THEMES[key]


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def make_background(width: int, height: int, theme: dict, bg_override: str | None = None) -> Image.Image:
    """Tao nen theo theme: mau phang hoac gradient doc (ve o 1px roi phong to
    -> nhanh va min voi moi kich thuoc, ke ca 5760x3240)."""
    if bg_override:
        return Image.new("RGB", (width, height), bg_override)
    if theme.get("gradient"):
        top, bottom = (_hex_to_rgb(c) for c in theme["gradient"])
        strip = Image.new("RGB", (1, 256))
        px = strip.load()
        for y in range(256):
            t = y / 255
            px[0, y] = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        return strip.resize((width, height), Image.Resampling.BILINEAR)
    return Image.new("RGB", (width, height), theme.get("bg") or "#FFFFFF")
