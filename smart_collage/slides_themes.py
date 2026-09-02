"""Theme cho slide (dung chung cho HTML va PPTX).

Moi theme dinh nghia mau sac + font cho trinh chieu tu dong (slideshow)
cho ket qua dong nhat. Ten theme dat trung voi theme collage de de nho.
"""

from __future__ import annotations

SLIDE_THEMES = {
    "classic": {
        "label": "Cổ điển — nền trắng, chữ đen",
        "bg": ("#FFFFFF", "#FFFFFF"),
        "text": "#1A202C", "muted": "#64748B",
        "h1": "#111827", "h2": "#1E3A5F", "accent": "#2563EB",
        "code_bg": "#F1F5F9", "code_text": "#0F172A",
        "quote_bg": "#F8FAFC", "quote_bar": "#2563EB",
        "table_head_bg": "#1E3A5F", "table_head_text": "#FFFFFF",
        "table_row_alt": "#F1F5F9", "table_border": "#CBD5E1",
        "footer": "#94A3B8", "dark": False,
    },
    "modern-light": {
        "label": "Hiện đại sáng — xám nhạt, xanh dương",
        "bg": ("#F8FAFC", "#E2E8F0"),
        "text": "#0F172A", "muted": "#64748B",
        "h1": "#0F172A", "h2": "#1D4ED8", "accent": "#3B82F6",
        "code_bg": "#0F172A", "code_text": "#E2E8F0",
        "quote_bg": "#EFF6FF", "quote_bar": "#3B82F6",
        "table_head_bg": "#1D4ED8", "table_head_text": "#FFFFFF",
        "table_row_alt": "#EFF6FF", "table_border": "#BFDBFE",
        "footer": "#94A3B8", "dark": False,
    },
    "modern-dark": {
        "label": "Hiện đại tối — nền than, chữ sáng",
        "bg": ("#1E293B", "#0F172A"),
        "text": "#E2E8F0", "muted": "#94A3B8",
        "h1": "#F8FAFC", "h2": "#7DD3FC", "accent": "#38BDF8",
        "code_bg": "#020617", "code_text": "#7DD3FC",
        "quote_bg": "#1E293B", "quote_bar": "#38BDF8",
        "table_head_bg": "#0EA5E9", "table_head_text": "#082F49",
        "table_row_alt": "#1E293B", "table_border": "#334155",
        "footer": "#64748B", "dark": True,
    },
    "boardroom": {
        "label": "Báo cáo — xanh navy chuyên nghiệp",
        "bg": ("#16324F", "#0B1F33"),
        "text": "#E6EDF5", "muted": "#9FB3C8",
        "h1": "#FFFFFF", "h2": "#F3C969", "accent": "#F3C969",
        "code_bg": "#0B1F33", "code_text": "#BCD9F5",
        "quote_bg": "#1D3A5C", "quote_bar": "#F3C969",
        "table_head_bg": "#F3C969", "table_head_text": "#16324F",
        "table_row_alt": "#1D3A5C", "table_border": "#2E517A",
        "footer": "#7A93AC", "dark": True,
    },
    "cream": {
        "label": "Kem ấm — nhẹ nhàng, kỷ niệm",
        "bg": ("#F5F0E6", "#E8DFCC"),
        "text": "#44403C", "muted": "#78716C",
        "h1": "#292524", "h2": "#9A6A3A", "accent": "#B45309",
        "code_bg": "#292524", "code_text": "#FDE68A",
        "quote_bg": "#EFE6D5", "quote_bar": "#B45309",
        "table_head_bg": "#9A6A3A", "table_head_text": "#FFF7ED",
        "table_row_alt": "#EFE6D5", "table_border": "#D6C7A8",
        "footer": "#A8A29E", "dark": False,
    },
    "gallery-black": {
        "label": "Triển lãm — đen tuyền tối giản",
        "bg": ("#000000", "#000000"),
        "text": "#D4D4D4", "muted": "#737373",
        "h1": "#FFFFFF", "h2": "#A3A3A3", "accent": "#FAFAFA",
        "code_bg": "#171717", "code_text": "#D4D4D4",
        "quote_bg": "#171717", "quote_bar": "#FAFAFA",
        "table_head_bg": "#262626", "table_head_text": "#FAFAFA",
        "table_row_alt": "#171717", "table_border": "#404040",
        "footer": "#525252", "dark": True,
    },
}

DEFAULT_SLIDE_THEME = "boardroom"

# Font: uu tien font he thong pho bien tren Windows, co fallback
FONT_STACK = ('"Segoe UI", "Helvetica Neue", Arial, "Noto Sans", sans-serif')
FONT_MONO = ('"Cascadia Code", Consolas, "Courier New", monospace')
PPTX_FONT = "Segoe UI"
PPTX_FONT_MONO = "Consolas"


def get_slide_theme(key: str) -> dict:
    if key not in SLIDE_THEMES:
        raise KeyError(
            f"Theme slide khong hop le: {key}. "
            f"Chon mot trong: {', '.join(SLIDE_THEMES)}")
    return SLIDE_THEMES[key]
