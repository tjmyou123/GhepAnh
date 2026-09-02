"""Cac kich thuoc dau ra chuan (preset)."""

# key: (ten hien thi, rong, cao)
# Facebook: kich thuoc x2 so voi khuyen nghi de anh net hon khi bi nen.
# Slide zoom: do phan giai cao de khi phong to (hieu ung Zoom/Morph trong
# PowerPoint) anh van sac net.
PRESETS = {
    "fb-cover": ("Ảnh bìa Facebook (1702×630)", 1702, 630),
    "fb-post": ("Ảnh đăng Facebook — vuông 1:1 (2160×2160)", 2160, 2160),
    "fb-post-doc": ("Ảnh đăng Facebook — dọc 4:5 (2160×2700)", 2160, 2700),
    "fb-post-ngang": ("Ảnh đăng Facebook — ngang 1.91:1 (2400×1260)", 2400, 1260),
    "fb-story": ("Story / Reels — dọc 9:16 (2160×3840)", 2160, 3840),
    "ig-post": ("Instagram — vuông 1:1 (2160×2160)", 2160, 2160),
    "ig-doc": ("Instagram / Threads — dọc 4:5 (2160×2700)", 2160, 2700),
    "ig-story": ("IG / TikTok Story·Reels — 9:16 (2160×3840)", 2160, 3840),
    "x-post": ("X (Twitter) — ngang 16:9 (2400×1350)", 2400, 1350),
    "linkedin": ("LinkedIn — ngang 1.91:1 (2400×1256)", 2400, 1256),
    "pinterest": ("Pinterest — đứng 2:3 (2000×3000)", 2000, 3000),
    "youtube": ("YouTube thumbnail — 16:9 (2560×1440)", 2560, 1440),
    "ppt": ("Slide PowerPoint 16:9 — FHD (1920×1080)", 1920, 1080),
    "ppt-4k": ("Slide PowerPoint 16:9 — 4K (3840×2160)", 3840, 2160),
    "ppt-43": ("Slide PowerPoint 4:3 (2048×1536)", 2048, 1536),
    "ppt-zoom": ("Slide Zoom/Morph — nét 3× (5760×3240)", 5760, 3240),
    "ppt-zoom-4x": ("Slide Zoom/Morph — nét 4×, 8K (7680×4320)", 7680, 4320),
    "ppt-zoom-43": ("Slide Zoom/Morph 4:3 — nét 3× (6144×4608)", 6144, 4608),
}

# Nhom preset de hien thi tren giao dien
PRESET_GROUPS = {
    "Facebook": ["fb-cover", "fb-post", "fb-post-doc", "fb-post-ngang", "fb-story"],
    "Instagram · Threads · TikTok": ["ig-post", "ig-doc", "ig-story"],
    "X · LinkedIn · Pinterest · YouTube": ["x-post", "linkedin", "pinterest", "youtube"],
    "Slide trình chiếu": ["ppt", "ppt-4k", "ppt-43"],
    "Slide Zoom/Morph (phóng to vẫn nét)": ["ppt-zoom", "ppt-zoom-4x", "ppt-zoom-43"],
}

DEFAULT_PRESET = "fb-post"


def get_preset(key: str):
    """Tra ve (rong, cao) cua preset. Nem KeyError neu khong ton tai."""
    _, w, h = PRESETS[key]
    return w, h
