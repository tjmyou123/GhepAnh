"""Doc anh, cat/ghep va xuat file chat luong cao."""

from __future__ import annotations

import math
import random
import re
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageColor, ImageDraw, ImageFile, ImageFilter, ImageFont, ImageOps

from .layout import Cell
from .themes import make_background

# Kinh nghiem tu PhotoCollage (issue #65): van tiep tuc khi file anh bi hong nhe
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None  # cho phep anh panorama rat lon

SUPPORTED_EXTS = {
    ".jpg", ".jpeg", ".jfif", ".jpe", ".png", ".webp",
    ".bmp", ".tif", ".tiff", ".gif",
}

# Cac file output cua chinh tool -> khong lay lam input khi chay lai
OUTPUT_PREFIX = "collage_"


def _natural_key(p: Path):
    """Sap xep tu nhien: anh2.jpg < anh10.jpg."""
    parts = re.split(r"(\d+)", p.name.lower())
    return [int(s) if s.isdigit() else s for s in parts]


def find_images(folder: Path) -> list[Path]:
    """Liet ke anh trong thu muc (khong de quy), sap xep tu nhien."""
    files = [
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTS
        and not p.name.lower().startswith(OUTPUT_PREFIX)
    ]
    files.sort(key=_natural_key)
    return files


def probe_images(paths: list[Path]) -> tuple[list[Path], list[float], list[str]]:
    """Doc kich thuoc (co tinh xoay EXIF) cua tung anh.

    Tra ve (danh sach file hop le, ti le w/h tuong ung, danh sach loi).
    """
    valid: list[Path] = []
    aspects: list[float] = []
    errors: list[str] = []
    for p in paths:
        try:
            with Image.open(p) as im:
                w, h = im.size
                try:
                    orientation = im.getexif().get(274, 1)
                except Exception:
                    orientation = 1
                if orientation in (5, 6, 7, 8):
                    w, h = h, w
            if w < 2 or h < 2:
                raise ValueError("anh qua nho")
            valid.append(p)
            aspects.append(w / h)
        except Exception as e:
            errors.append(f"{p.name}: {e}")
    return valid, aspects, errors


# Chinh sua rieng tung anh (theo ten file thuong): rot/zoom/dx/dy.
# Duoc render_image() dat truoc moi lan ghep; cac ham paste doc qua
# _load_for_cell. Moi tien trinh chi render 1 anh mot luc (GUI co _busy).
_ADJUST: dict[str, dict] = {}


def _load_for_cell(path: Path, cw: int, ch: int) -> Image.Image:
    """Doc anh va cover-crop vua khit o (cw x ch), chat luong cao.

    Ton trong chinh sua rieng cua anh trong _ADJUST (neu co):
    rot 0/90/180/270 (theo chieu kim dong ho), zoom >= 1 (phong to vung cat),
    dx/dy trong [-1, 1] (doi cua so cat: -1 = mep trai/tren, 1 = mep phai/duoi).
    """
    adj = _ADJUST.get(path.name.lower(), {})
    rot = int(adj.get("rot", 0)) % 360
    zoom = max(1.0, min(4.0, float(adj.get("zoom", 1.0))))
    dx = max(-1.0, min(1.0, float(adj.get("dx", 0.0))))
    dy = max(-1.0, min(1.0, float(adj.get("dy", 0.0))))

    img = Image.open(path)
    # JPEG: giai ma nhanh o kich thuoc ~2x dich -> nhanh gap nhieu lan voi
    # 300 anh may chuc MP ma khong giam chat luong dau ra.
    if (img.format or "").upper() == "JPEG":
        m = round(max(cw, ch) * 2 * zoom)
        img.draft("RGB", (m, m))
    img = ImageOps.exif_transpose(img)
    if rot:
        img = img.transpose({90: Image.Transpose.ROTATE_270,
                             180: Image.Transpose.ROTATE_180,
                             270: Image.Transpose.ROTATE_90}[rot])
    if img.mode != "RGB":
        # Anh co kenh trong suot -> dat len nen trang
        if img.mode in ("RGBA", "LA", "PA") or (
            img.mode == "P" and "transparency" in img.info
        ):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

    iw, ih = img.size
    scale = max(cw / iw, ch / ih) * zoom
    nw = max(cw, int(round(iw * scale)))
    nh = max(ch, int(round(ih * scale)))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    # cat phan thua: mac dinh o giua, dich theo dx/dy neu nguoi dung chinh
    left = min(nw - cw, max(0, round((nw - cw) * (0.5 + 0.5 * dx))))
    top = min(nh - ch, max(0, round((nh - ch) * (0.5 + 0.5 * dy))))
    return img.crop((left, top, left + cw, top + ch))


def _paste_polaroid(canvas: Image.Image, path: Path, cell: Cell, rng: random.Random) -> None:
    """Ve mot "the anh polaroid": khung trang, anh vuong, xoay nhe, do bong.
    The anh luon nam gon trong o cua no -> cac the khong de len nhau."""
    rot = rng.uniform(-6.0, 6.0)
    rad = math.radians(abs(rot))
    c, si = math.cos(rad), math.sin(rad)
    # kich thuoc the theo canh anh s: rong = 1.14s, cao = 1.266s (vien duoi day)
    s_size = min(
        0.94 * cell.w / (1.14 * c + 1.266 * si),
        0.94 * cell.h / (1.14 * si + 1.266 * c),
    )
    s_size = max(8, int(s_size))
    b = max(2, round(0.07 * s_size))

    photo = _load_for_cell(path, s_size, s_size)
    card = Image.new("RGB", (s_size + 2 * b, s_size + b + round(2.8 * b)), (252, 250, 246))
    card.paste(photo, (b, b))
    photo.close()
    card = card.convert("RGBA")
    card = card.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)

    # bong do mem phia sau the
    pad = 14
    shadow = Image.new("RGBA", (card.width + pad * 2, card.height + pad * 2), (0, 0, 0, 0))
    black = Image.new("RGBA", card.size, (25, 22, 20, 115))
    shadow.paste(black, (pad, pad), card.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))

    cx = cell.x0 + (cell.w - card.width) // 2
    cy = cell.y0 + (cell.h - card.height) // 2
    canvas.paste(shadow, (cx - pad + 3, cy - pad + 5), shadow)
    canvas.paste(card, (cx, cy), card)


def _paste_stack(canvas: Image.Image, path: Path, cell: Cell, rng: random.Random) -> None:
    """Anh xoay nhe tu do voi bong do mem, khong khung trang — kieu "ban anh".
    Anh luon lot gon trong o cua no -> khong de len nhau."""
    rot = rng.uniform(-4.5, 4.5)
    rad = math.radians(abs(rot))
    c, si = math.cos(rad), math.sin(rad)
    aw, ah = cell.w, cell.h
    k = min(0.96 * aw / (aw * c + ah * si), 0.96 * ah / (aw * si + ah * c))
    pw, ph = max(8, int(aw * k)), max(8, int(ah * k))

    photo = _load_for_cell(path, pw, ph).convert("RGBA")
    photo = photo.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)

    pad = 12
    shadow = Image.new("RGBA", (photo.width + pad * 2, photo.height + pad * 2), (0, 0, 0, 0))
    black = Image.new("RGBA", photo.size, (18, 18, 24, 110))
    shadow.paste(black, (pad, pad), photo.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))

    cx = cell.x0 + (cell.w - photo.width) // 2
    cy = cell.y0 + (cell.h - photo.height) // 2
    canvas.paste(shadow, (cx - pad + 3, cy - pad + 5), shadow)
    canvas.paste(photo, (cx, cy), photo)


def _hex_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _bg_is_light(theme: Optional[dict], bg: str) -> bool:
    """Nen sang hay toi? -> chon mau truc/cham moc tuong phan."""
    colors: list[str] = []
    if theme:
        if theme.get("gradient"):
            colors = list(theme["gradient"])
        elif theme.get("bg"):
            colors = [theme["bg"]]
    if not colors:
        colors = [bg if bg.startswith("#") else "#FFFFFF"]
    lum = 0.0
    for cstr in colors:
        r, g, b = _hex_rgb(cstr)
        lum += 0.299 * r + 0.587 * g + 0.114 * b
    return lum / len(colors) >= 140


def _timeline_font(px: int) -> Optional[ImageFont.FreeTypeFont]:
    for name in ("arialbd.ttf", "arial.ttf", "segoeuib.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except Exception:
            continue
    return None


def _font_cached(ctx: dict, px: int) -> Optional[ImageFont.FreeTypeFont]:
    fonts = ctx.setdefault("fonts", {})
    if px not in fonts:
        fonts[px] = _timeline_font(px)
    return fonts[px]


def _fit_text(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    """Cat bot chu cho vua be rong, them dau ba cham."""
    text = text.strip()
    if not text or max_w <= 4:
        return ""
    if font.getlength(text) <= max_w:
        return text
    while text and font.getlength(text + "…") > max_w:
        text = text[:-1]
    return (text.rstrip() + "…") if text else ""


def _parse_color(value) -> Optional[tuple[int, int, int]]:
    """'#RRGGBB' hoac ten mau PIL -> (r, g, b); None neu khong doc duoc."""
    if not value:
        return None
    try:
        return ImageColor.getrgb(str(value).strip())[:3]
    except ValueError:
        return None


# Tuy chon chi tiet cho cac layout infographic (nguoi dung bat/tat duoc)
INFO_OPT_DEFAULTS = {
    "numbers": True,     # so thu tu (cham moc, huy hieu buoc, so khung phim)
    "captions": True,    # nhan ten anh (timeline, timeline-doc, string)
    "markers": True,     # diem xuat phat + mui ten ket thuc (timeline)
    "num_color": None,   # mau so/huy hieu; None = tu dong theo nen
    "line_color": None,  # mau truc/duong noi/day treo; None = tu dong
}


def _info_colors(theme: Optional[dict], bg: str, opts: Optional[dict] = None) -> dict:
    """Bang mau tuong phan cho cac layout infographic (theo do sang nen).
    opts co the ghi de: num_color (so/huy hieu), line_color (truc/day)."""
    if _bg_is_light(theme, bg):
        col = {
            "light": True,
            "line": (82, 82, 91), "dot_fill": (255, 255, 255),
            "dot_ring": (82, 82, 91), "num": (51, 65, 85),
            "card": (252, 250, 246), "muted": (113, 113, 122),
            "accent": (37, 99, 235), "on_accent": (255, 255, 255),
            "string": (128, 116, 105), "film_num": (180, 83, 9),
        }
    else:
        col = {
            "light": False,
            "line": (226, 232, 240), "dot_fill": (15, 23, 42),
            "dot_ring": (226, 232, 240), "num": (241, 245, 249),
            "card": (248, 248, 246), "muted": (161, 161, 170),
            "accent": (96, 165, 250), "on_accent": (15, 23, 42),
            "string": (214, 211, 209), "film_num": (251, 191, 36),
        }
    if opts:
        rgb = _parse_color(opts.get("num_color"))
        if rgb:
            lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            col.update(accent=rgb, num=rgb, film_num=rgb,
                       on_accent=(255, 255, 255) if lum < 150 else (15, 23, 42))
        rgb = _parse_color(opts.get("line_color"))
        if rgb:
            col.update(line=rgb, dot_ring=rgb, string=rgb)
    return col


def _bands_of(cells: list[Cell]) -> tuple[list[dict], dict]:
    """Gom o theo dai ngang (y0,y1). Tra ve (bands tu tren xuong, map y0->band)."""
    groups: dict[tuple[int, int], list[Cell]] = {}
    for c in cells:
        groups.setdefault((c.y0, c.y1), []).append(c)
    bands = []
    for (y0, y1) in sorted(groups):
        bc = sorted(groups[(y0, y1)], key=lambda c: c.x0)
        first = min(bc, key=lambda c: c.index)
        x0, x1 = bc[0].x0, max(c.x1 for c in bc)
        bands.append({
            "y0": y0, "y1": y1, "mid": (y0 + y1) // 2, "h": y1 - y0,
            "x0": x0, "x1": x1,
            "lr": abs(first.x0 - x0) <= abs(x1 - first.x1),
            "min_w": min(c.w for c in bc),
            "cells": bc,
        })
    return bands, {b["y0"]: b for b in bands}


def _cols_of(cells: list[Cell]) -> tuple[list[dict], dict]:
    """Gom o theo cot doc (x0,x1). Tra ve (cols trai->phai, map x0->col)."""
    groups: dict[tuple[int, int], list[Cell]] = {}
    for c in cells:
        groups.setdefault((c.x0, c.x1), []).append(c)
    cols = []
    for (x0, x1) in sorted(groups):
        cc = sorted(groups[(x0, x1)], key=lambda c: c.y0)
        first = min(cc, key=lambda c: c.index)
        y0, y1 = cc[0].y0, max(c.y1 for c in cc)
        cols.append({
            "x0": x0, "x1": x1, "mid": (x0 + x1) // 2, "w": x1 - x0,
            "y0": y0, "y1": y1,
            "tb": abs(first.y0 - y0) <= abs(y1 - first.y1),  # chay tu tren xuong?
            "min_h": min(c.h for c in cc),
            "cells": cc,
        })
    return cols, {c["x0"]: c for c in cols}


def _arc_pts(cx: float, cy: float, r: float, a0: float, a1: float) -> list[tuple[float, float]]:
    """Diem lay mau tren cung tron (goc kieu PIL: 0 = 3h, tang thuan chieu kim).
    Dung de ve cung bang d.line -> net can giua nhu duong thang, khop moi noi
    (d.arc cua PIL ve net lan vao trong nen bi lech nua be rong net)."""
    steps = max(8, min(48, round(abs(a1 - a0) / 4)))
    out = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def _timeline_ctx(
    cells: list[Cell],
    width_s: int,
    height_s: int,
    s: int,
    theme: Optional[dict],
    bg: str,
    opts: dict,
) -> dict:
    """Tinh san so lieu chung cho timeline: dai bang, truc, mau, kich thuoc."""
    bands, by_y0 = _bands_of(cells)

    u = min(width_s, height_s)
    line_w = max(2, round(u * 0.0042))
    bh = min(b["h"] for b in bands)
    mw = min(b["min_w"] for b in bands)
    dot_r = max(3, min(round(bh * 0.075), round(mw * 0.28), round(u * 0.02)))

    col = _info_colors(theme, bg, opts)

    font = None
    if opts["numbers"] and (2 * dot_r) / s >= 15:  # cham du to -> ghi so
        font = _timeline_font(max(8, round(dot_r * 1.05)))
    cap_font = None
    if opts["captions"] and mw / s >= 78 and bh / s >= 90:  # du cho -> nhan ten
        cap_font = _timeline_font(max(9, min(round(u * 0.0135), round(mw * 0.14))))

    return {"bands": bands, "by_y0": by_y0, "line_w": line_w,
            "dot_r": dot_r, "s": s, "u": u, "col": col, "font": font,
            "cap_font": cap_font, "stem": max(2, round(bh * 0.05)),
            "opts": opts}


def _draw_timeline_base(canvas: Image.Image, ctx: dict) -> None:
    """Ve truc ngang moi dai + khuc quanh chu U noi cac dai (kieu ran bo)."""
    d = ImageDraw.Draw(canvas)
    bands = ctx["bands"]
    lw = ctx["line_w"]
    line = ctx["col"]["line"]

    # ban kinh khuc quanh
    turns: list[dict] = []
    for i in range(len(bands) - 1):
        a, b = bands[i], bands[i + 1]
        right = a["lr"]  # dai di L->R thi quanh o ben phai
        gap = b["mid"] - a["mid"]
        r = max(2, min(round(gap / 2) - lw, round(min(canvas.width, canvas.height) * 0.05)))
        xv = (min(a["x1"], b["x1"]) - max(2, lw)) if right else (max(a["x0"], b["x0"]) + max(2, lw))
        turns.append({"right": right, "r": r, "xv": xv, "m1": a["mid"], "m2": b["mid"]})

    # truc ngang tung dai (rut ngan o dau co khuc quanh)
    for i, b in enumerate(bands):
        xs, xe = b["x0"] + lw, b["x1"] - lw
        if i > 0:
            t = turns[i - 1]
            if t["right"]:
                xe = t["xv"] - t["r"]
            else:
                xs = t["xv"] + t["r"]
        if i < len(turns):
            t = turns[i]
            if t["right"]:
                xe = t["xv"] - t["r"]
            else:
                xs = t["xv"] + t["r"]
        d.line([(xs, b["mid"]), (xe, b["mid"])], fill=line, width=lw)

    # khuc quanh: polyline lay mau cung tron -> net can giua nhu truc ngang,
    # moi noi khop hoan toan (khong con lech nua be rong net nhu d.arc)
    for t in turns:
        r, xv, m1, m2 = t["r"], t["xv"], t["m1"], t["m2"]
        if r <= 3 or m2 - m1 <= 2 * r + 2:
            pts = ([(xv - r, m1), (xv, m1), (xv, m2), (xv - r, m2)] if t["right"]
                   else [(xv + r, m1), (xv, m1), (xv, m2), (xv + r, m2)])
            d.line(pts, fill=line, width=lw, joint="curve")
            continue
        ov = lw  # lan nhe vao truc ngang de moi noi lien mach
        if t["right"]:
            pts = ([(xv - r - ov, m1)]
                   + _arc_pts(xv - r, m1 + r, r, 270, 360)
                   + _arc_pts(xv - r, m2 - r, r, 0, 90)
                   + [(xv - r - ov, m2)])
        else:
            pts = ([(xv + r + ov, m1)]
                   + _arc_pts(xv + r, m1 + r, r, 270, 180)
                   + _arc_pts(xv + r, m2 - r, r, 180, 90)
                   + [(xv + r + ov, m2)])
        d.line(pts, fill=line, width=lw, joint="curve")

    # diem xuat phat (vong tron rong) + mui ten ket thuc theo huong dong chay
    if not ctx["opts"]["markers"]:
        return
    b0, bl = bands[0], bands[-1]
    rm = max(3, round(ctx["dot_r"] * 0.7))
    sx = (b0["x0"] + lw + rm) if b0["lr"] else (b0["x1"] - lw - rm)
    d.ellipse([sx - rm, b0["mid"] - rm, sx + rm, b0["mid"] + rm],
              fill=ctx["col"]["dot_fill"], outline=line, width=lw)
    ah = max(6, round(3.4 * lw))
    ay = round(ah * 0.66)
    if bl["lr"]:
        xe = bl["x1"] - lw
        tri = [(xe - ah, bl["mid"] - ay), (xe, bl["mid"]), (xe - ah, bl["mid"] + ay)]
    else:
        xs2 = bl["x0"] + lw
        tri = [(xs2 + ah, bl["mid"] - ay), (xs2, bl["mid"]), (xs2 + ah, bl["mid"] + ay)]
    d.polygon(tri, fill=line)


def _photo_aspect(path: Path) -> float:
    try:
        with Image.open(path) as im:
            w, h = im.size
            try:
                if im.getexif().get(274, 1) in (5, 6, 7, 8):
                    w, h = h, w
            except Exception:
                pass
        return w / max(1, h)
    except Exception:
        return 4 / 3


def _shadow_card(
    canvas: Image.Image,
    path: Path,
    x: int,
    y: int,
    pw: int,
    ph: int,
    b: int,
    card_col: tuple,
) -> tuple[int, int]:
    """Dan the anh (khung mau card + bong do mem) tai (x, y). Tra ve (w, h)."""
    card_w, card_h = pw + 2 * b, ph + 2 * b
    pad = max(6, b * 3)
    sh = Image.new("L", (card_w + pad * 2, card_h + pad * 2), 0)
    ImageDraw.Draw(sh).rectangle([pad, pad, pad + card_w - 1, pad + card_h - 1], fill=95)
    sh = sh.filter(ImageFilter.GaussianBlur(pad / 2.4))
    black = Image.new("RGB", sh.size, (12, 14, 18))
    canvas.paste(black, (x - pad + 2, y - pad + 4), sh)

    card = Image.new("RGB", (card_w, card_h), card_col)
    photo = _load_for_cell(path, pw, ph)
    card.paste(photo, (b, b))
    photo.close()
    canvas.paste(card, (x, y))
    return card_w, card_h


def _paste_timeline_card(canvas: Image.Image, path: Path, cell: Cell, ctx: dict) -> None:
    """The anh thu nho co khung trang + bong, nam nua tren/duoi truc,
    kem cuong noi xuong cham moc va nhan ten anh o nua doi dien."""
    band = ctx["by_y0"][cell.y0]
    mid = band["mid"]
    above = cell.index % 2 == 0
    lw, dot_r, stem = ctx["line_w"], ctx["dot_r"], ctx["stem"]

    pad_x = max(2, round(cell.w * 0.07))
    pad_y = max(2, round(cell.h * 0.035))
    b = max(2, round(min(canvas.width, canvas.height) * 0.0042))

    mw = cell.w - 2 * pad_x
    if above:
        top, bottom = cell.y0 + pad_y, mid - dot_r - stem
    else:
        top, bottom = mid + dot_r + stem, cell.y1 - pad_y
    mh = bottom - top
    if mw < 12 or mh < 12:  # o qua nho -> dan thang khong khung
        piece = _load_for_cell(path, max(4, cell.w), max(4, cell.h))
        canvas.paste(piece, (cell.x0, cell.y0))
        piece.close()
        return

    a = min(1.55, max(0.72, _photo_aspect(path)))
    ph = min(mh - 2 * b, (mw - 2 * b) / a)
    pw = max(8, round(ph * a))
    ph = max(8, round(ph))

    card_w, card_h = pw + 2 * b, ph + 2 * b
    cx = cell.x0 + (cell.w - card_w) // 2
    cy = top if not above else bottom - card_h

    # cuong noi the -> cham moc
    d = ImageDraw.Draw(canvas)
    dot_x = (cell.x0 + cell.x1) // 2
    y_edge = (cy + card_h - 2) if above else (cy + 2)
    d.line([(dot_x, y_edge), (dot_x, mid)], fill=ctx["col"]["line"], width=lw)

    _shadow_card(canvas, path, cx, cy, pw, ph, b, ctx["col"]["card"])

    # nhan ten anh o nua doi dien truc (nhu nhan moc thoi gian)
    cf = ctx.get("cap_font")
    if cf:
        label = _fit_text(path.stem, cf, mw)
        if label:
            gap = dot_r + stem + round(cf.size * 0.95)
            cy_t = mid + gap if above else mid - gap
            d.text((dot_x, cy_t), label, font=cf,
                   fill=ctx["col"]["muted"], anchor="mm")


def _draw_dot_num(d: ImageDraw.ImageDraw, cx: int, cy: int, ctx: dict, num_val: int) -> None:
    """Cham moc tron + so thu tu (neu du lon)."""
    r, lw = ctx["dot_r"], ctx["line_w"]
    col, font = ctx["col"], ctx["font"]
    d.ellipse([cx - r, cy - r, cx + r, cy + r],
              fill=col["dot_fill"], outline=col["dot_ring"],
              width=max(2, round(lw * 0.9)))
    if font:
        num = str(num_val)
        k = 1.0 if len(num) == 1 else (0.78 if len(num) == 2 else 0.58)
        f = font if k == 1.0 else _font_cached(ctx, max(8, round(r * 1.05 * k)))
        if f:
            d.text((cx, cy), num, font=f, fill=col["num"], anchor="mm")


def _draw_timeline_dots(canvas: Image.Image, cells: list[Cell], ctx: dict) -> None:
    """Cham moc tren truc + so thu tu (neu du lon)."""
    d = ImageDraw.Draw(canvas)
    for cell in cells:
        mid = ctx["by_y0"][cell.y0]["mid"]
        _draw_dot_num(d, (cell.x0 + cell.x1) // 2, mid, ctx, cell.index + 1)


# ---------------------------------------------------------------- timeline doc

def _timeline_doc_ctx(
    cells: list[Cell], width_s: int, height_s: int, s: int,
    theme: Optional[dict], bg: str, opts: dict,
) -> dict:
    """Timeline doc: truc doc giua moi cot, the anh trai/phai xen ke."""
    cols, by_x0 = _cols_of(cells)
    u = min(width_s, height_s)
    line_w = max(2, round(u * 0.0042))
    cwm = min(c["w"] for c in cols)
    mh = min(c["min_h"] for c in cols)
    dot_r = max(3, min(round(cwm * 0.075), round(mh * 0.28), round(u * 0.02)))
    col = _info_colors(theme, bg, opts)
    font = None
    if opts["numbers"] and (2 * dot_r) / s >= 15:
        font = _timeline_font(max(8, round(dot_r * 1.05)))
    cap_font = None
    if opts["captions"] and mh / s >= 64 and cwm / s >= 170:
        cap_font = _timeline_font(max(9, min(round(u * 0.0135), round(mh * 0.16))))
    return {"cols": cols, "by_x0": by_x0, "line_w": line_w, "dot_r": dot_r,
            "s": s, "u": u, "col": col, "font": font, "cap_font": cap_font,
            "stem": max(2, round(cwm * 0.05)), "opts": opts}


def _draw_timeline_doc_base(canvas: Image.Image, ctx: dict) -> None:
    """Truc doc moi cot + khuc quanh chu U noi cac cot (ran bo doc)."""
    d = ImageDraw.Draw(canvas)
    cols = ctx["cols"]
    lw = ctx["line_w"]
    line = ctx["col"]["line"]

    turns: list[dict] = []
    for i in range(len(cols) - 1):
        a, b = cols[i], cols[i + 1]
        bottom = a["tb"]  # cot chay xuong -> quanh o day
        gap = b["mid"] - a["mid"]
        r = max(2, min(round(gap / 2) - lw,
                       round(min(canvas.width, canvas.height) * 0.05)))
        yv = (min(a["y1"], b["y1"]) - max(2, lw)) if bottom \
            else (max(a["y0"], b["y0"]) + max(2, lw))
        turns.append({"bottom": bottom, "r": r, "yv": yv,
                      "m1": a["mid"], "m2": b["mid"]})

    for i, c in enumerate(cols):
        ys, ye = c["y0"] + lw, c["y1"] - lw
        near = ([turns[i - 1]] if i > 0 else []) + ([turns[i]] if i < len(turns) else [])
        for t in near:
            if t["bottom"]:
                ye = min(ye, t["yv"] - t["r"])
            else:
                ys = max(ys, t["yv"] + t["r"])
        d.line([(c["mid"], ys), (c["mid"], ye)], fill=line, width=lw)

    for t in turns:
        r, yv, m1, m2 = t["r"], t["yv"], t["m1"], t["m2"]
        if r <= 3 or m2 - m1 <= 2 * r + 2:
            off = -r if t["bottom"] else r
            d.line([(m1, yv + off), (m1, yv), (m2, yv), (m2, yv + off)],
                   fill=line, width=lw, joint="curve")
            continue
        ov = lw  # lan nhe vao truc doc de moi noi lien mach
        if t["bottom"]:
            pts = ([(m1, yv - r - ov)]
                   + _arc_pts(m1 + r, yv - r, r, 180, 90)
                   + _arc_pts(m2 - r, yv - r, r, 90, 0)
                   + [(m2, yv - r - ov)])
        else:
            pts = ([(m1, yv + r + ov)]
                   + _arc_pts(m1 + r, yv + r, r, 180, 270)
                   + _arc_pts(m2 - r, yv + r, r, 270, 360)
                   + [(m2, yv + r + ov)])
        d.line(pts, fill=line, width=lw, joint="curve")

    # diem xuat phat + mui ten ket thuc (doc theo dong chay)
    if not ctx["opts"]["markers"]:
        return
    c0, cl = cols[0], cols[-1]
    rm = max(3, round(ctx["dot_r"] * 0.7))
    sy = (c0["y0"] + lw + rm) if c0["tb"] else (c0["y1"] - lw - rm)
    d.ellipse([c0["mid"] - rm, sy - rm, c0["mid"] + rm, sy + rm],
              fill=ctx["col"]["dot_fill"], outline=line, width=lw)
    ah = max(6, round(3.4 * lw))
    ax = round(ah * 0.66)
    if cl["tb"]:
        ye2 = cl["y1"] - lw
        tri = [(cl["mid"] - ax, ye2 - ah), (cl["mid"], ye2), (cl["mid"] + ax, ye2 - ah)]
    else:
        ys2 = cl["y0"] + lw
        tri = [(cl["mid"] - ax, ys2 + ah), (cl["mid"], ys2), (cl["mid"] + ax, ys2 + ah)]
    d.polygon(tri, fill=line)


def _paste_timeline_doc_card(canvas: Image.Image, path: Path, cell: Cell, ctx: dict) -> None:
    """The anh ben trai/phai truc doc + cuong ngang + nhan ten doi dien."""
    colb = ctx["by_x0"][cell.x0]
    midx = colb["mid"]
    left = cell.index % 2 == 0
    lw, dot_r, stem = ctx["line_w"], ctx["dot_r"], ctx["stem"]

    pad_x = max(2, round(cell.w * 0.03))
    pad_y = max(2, round(cell.h * 0.07))
    b = max(2, round(min(canvas.width, canvas.height) * 0.0042))

    mh = cell.h - 2 * pad_y
    if left:
        lx, rx = cell.x0 + pad_x, midx - dot_r - stem
    else:
        lx, rx = midx + dot_r + stem, cell.x1 - pad_x
    mw = rx - lx
    if mw < 12 or mh < 12:
        piece = _load_for_cell(path, max(4, cell.w), max(4, cell.h))
        canvas.paste(piece, (cell.x0, cell.y0))
        piece.close()
        return

    a = min(1.55, max(0.72, _photo_aspect(path)))
    ph = min(mh - 2 * b, (mw - 2 * b) / a)
    pw = max(8, round(ph * a))
    ph = max(8, round(ph))

    card_w, card_h = pw + 2 * b, ph + 2 * b
    ccy = (cell.y0 + cell.y1) // 2
    cy = ccy - card_h // 2
    cx = (rx - card_w) if left else lx

    d = ImageDraw.Draw(canvas)
    x_edge = (cx + card_w - 2) if left else (cx + 2)
    d.line([(x_edge, ccy), (midx, ccy)], fill=ctx["col"]["line"], width=lw)

    _shadow_card(canvas, path, cx, cy, pw, ph, b, ctx["col"]["card"])

    cf = ctx.get("cap_font")
    if cf:
        free_w = (cell.x1 - pad_x - midx if left else midx - cell.x0 - pad_x) \
            - dot_r - stem * 2
        label = _fit_text(path.stem, cf, free_w)
        if label:
            gx = midx + dot_r + stem * 2 if left else midx - dot_r - stem * 2
            d.text((gx, ccy), label, font=cf, fill=ctx["col"]["muted"],
                   anchor="lm" if left else "rm")


def _draw_timeline_doc_dots(canvas: Image.Image, cells: list[Cell], ctx: dict) -> None:
    d = ImageDraw.Draw(canvas)
    for cell in cells:
        midx = ctx["by_x0"][cell.x0]["mid"]
        _draw_dot_num(d, midx, (cell.y0 + cell.y1) // 2, ctx, cell.index + 1)


# ---------------------------------------------------------------- process

def _poly_mask(w: int, h: int, pts: list[tuple[int, int]]) -> Image.Image:
    """Mat na da giac (ve 2x roi thu nho -> canh min)."""
    m = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m).polygon([(x * 2, y * 2) for x, y in pts], fill=255)
    return m.resize((w, h), Image.Resampling.LANCZOS)


def _process_ctx(
    cells: list[Cell], width_s: int, height_s: int, s: int,
    theme: Optional[dict], bg: str, opts: dict,
) -> dict:
    """Quy trinh mui ten: chevron cai nhau, so buoc trong huy hieu tron."""
    bands, by_y0 = _bands_of(cells)
    u = min(width_s, height_s)
    line_w = max(2, round(u * 0.0042))
    col = _info_colors(theme, bg, opts)
    bh = min(b["h"] for b in bands)
    mw = min(b["min_w"] for b in bands)
    rb = max(5, min(round(bh * 0.14), round(mw * 0.20), round(u * 0.022)))
    font = _timeline_font(max(8, round(rb * 1.1))) \
        if opts["numbers"] and (2 * rb) / s >= 12 else None
    return {"bands": bands, "by_y0": by_y0, "line_w": line_w, "s": s, "u": u,
            "col": col, "badge_r": rb, "font": font, "opts": opts}


def _paste_process_arrow(canvas: Image.Image, path: Path, cell: Cell, ctx: dict) -> None:
    band = ctx["by_y0"][cell.y0]
    right = band["lr"]
    cw, ch = cell.w, cell.h
    if cw < 26 or ch < 18:
        piece = _load_for_cell(path, max(4, cw), max(4, ch))
        canvas.paste(piece, (cell.x0, cell.y0))
        piece.close()
        return

    tip = max(4, round(min(cw * 0.20, ch * 0.55)))
    if right:
        pts = [(0, 0), (cw - tip, 0), (cw - 1, ch // 2),
               (cw - tip, ch - 1), (0, ch - 1), (tip - 1, ch // 2)]
    else:
        pts = [(cw - 1, 0), (tip, 0), (0, ch // 2),
               (tip, ch - 1), (cw - 1, ch - 1), (cw - tip, ch // 2)]
    m = _poly_mask(cw, ch, pts)
    photo = _load_for_cell(path, cw, ch)
    canvas.paste(photo, (cell.x0, cell.y0), m)
    photo.close()

    d = ImageDraw.Draw(canvas)
    outline = [(cell.x0 + x, cell.y0 + y) for x, y in pts]
    d.line(outline + [outline[0]], fill=ctx["col"]["card"],
           width=max(2, ctx["line_w"] - 1), joint="curve")

    rb, f = ctx["badge_r"], ctx["font"]
    if f and 2 * rb <= min(cw, ch):
        bx = (cell.x0 + tip + round(rb * 1.15)) if right \
            else (cell.x1 - tip - round(rb * 1.15))
        by = cell.y0 + ch // 2
        d.ellipse([bx - rb, by - rb, bx + rb, by + rb],
                  fill=ctx["col"]["accent"], outline=ctx["col"]["card"],
                  width=max(2, round(ctx["line_w"] * 0.8)))
        num = str(cell.index + 1)
        k = 1.0 if len(num) == 1 else (0.8 if len(num) == 2 else 0.6)
        ff = f if k == 1.0 else _font_cached(ctx, max(8, round(rb * 1.1 * k)))
        if ff:
            d.text((bx, by), num, font=ff, fill=ctx["col"]["on_accent"], anchor="mm")


# ---------------------------------------------------------------- path

def _circle_mask(dia: int) -> Image.Image:
    m = Image.new("L", (dia * 2, dia * 2), 0)
    ImageDraw.Draw(m).ellipse([0, 0, dia * 2 - 1, dia * 2 - 1], fill=255)
    return m.resize((dia, dia), Image.Resampling.LANCZOS)


def _dotted_seg(d: ImageDraw.ImageDraw, p1, p2, r: int, step: float, fill) -> None:
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    dist = math.hypot(dx, dy)
    if dist < 1:
        return
    k = int(dist // step)
    for i in range(1, k + 1):
        t = i * step / dist
        x, y = p1[0] + dx * t, p1[1] + dy * t
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _path_ctx(
    cells: list[Cell], width_s: int, height_s: int, s: int,
    theme: Optional[dict], bg: str, opts: dict,
) -> dict:
    """Hanh trinh bong bong: anh tron noi nhau bang duong cham."""
    bands, by_y0 = _bands_of(cells)
    u = min(width_s, height_s)
    line_w = max(2, round(u * 0.0042))
    col = _info_colors(theme, bg, opts)
    mind = min(min(c.w, c.h) for c in cells)
    rb = max(5, round(mind * 0.82 * 0.155))
    font = _timeline_font(max(8, round(rb * 1.1))) \
        if opts["numbers"] and (2 * rb) / s >= 12 else None
    return {"bands": bands, "by_y0": by_y0, "line_w": line_w, "s": s, "u": u,
            "col": col, "badge_r": rb, "font": font, "opts": opts}


def _draw_path_base(canvas: Image.Image, cells: list[Cell], ctx: dict) -> None:
    d = ImageDraw.Draw(canvas)
    pts = [((c.x0 + c.x1) // 2, (c.y0 + c.y1) // 2)
           for c in sorted(cells, key=lambda c: c.index)]
    rd = max(2, round(ctx["line_w"] * 0.95))
    step = rd * 4.6
    for i in range(len(pts) - 1):
        _dotted_seg(d, pts[i], pts[i + 1], rd, step, ctx["col"]["line"])


def _paste_path_bubble(canvas: Image.Image, path: Path, cell: Cell, ctx: dict) -> None:
    cw, ch = cell.w, cell.h
    dia = round(min(cw, ch) * 0.82)
    if dia < 14:
        piece = _load_for_cell(path, max(4, cw), max(4, ch))
        canvas.paste(piece, (cell.x0, cell.y0))
        piece.close()
        return
    ccx, ccy = cell.x0 + cw // 2, cell.y0 + ch // 2
    x0, y0 = ccx - dia // 2, ccy - dia // 2
    ring = max(2, round(dia * 0.035))

    pad = max(6, ring * 2)
    sh = Image.new("L", (dia + pad * 2, dia + pad * 2), 0)
    ImageDraw.Draw(sh).ellipse([pad, pad, pad + dia, pad + dia], fill=90)
    sh = sh.filter(ImageFilter.GaussianBlur(pad / 2.4))
    black = Image.new("RGB", sh.size, (12, 14, 18))
    canvas.paste(black, (x0 - pad + 2, y0 - pad + 4), sh)

    photo = _load_for_cell(path, dia, dia)
    canvas.paste(photo, (x0, y0), _circle_mask(dia))
    photo.close()
    d = ImageDraw.Draw(canvas)
    d.ellipse([x0, y0, x0 + dia - 1, y0 + dia - 1],
              outline=ctx["col"]["card"], width=ring)

    rb, f = ctx["badge_r"], ctx["font"]
    if f:
        off = round(dia * 0.335)
        bx, by = ccx + off, ccy + off
        d.ellipse([bx - rb, by - rb, bx + rb, by + rb],
                  fill=ctx["col"]["accent"], outline=ctx["col"]["card"],
                  width=max(2, round(ctx["line_w"] * 0.8)))
        num = str(cell.index + 1)
        k = 1.0 if len(num) == 1 else (0.8 if len(num) == 2 else 0.6)
        ff = f if k == 1.0 else _font_cached(ctx, max(8, round(rb * 1.1 * k)))
        if ff:
            d.text((bx, by), num, font=ff, fill=ctx["col"]["on_accent"], anchor="mm")


# ---------------------------------------------------------------- filmstrip

def _filmstrip_ctx(
    canvas: Image.Image, cells: list[Cell], width_s: int, height_s: int, s: int,
    theme: Optional[dict], bg: str, opts: dict,
) -> dict:
    """Cuon phim: dai toi mau + lo rang cua tren/duoi, anh la khung phim."""
    bands, by_y0 = _bands_of(cells)
    u = min(width_s, height_s)
    col = _info_colors(theme, bg, opts)
    d = ImageDraw.Draw(canvas)
    strip = (26, 26, 30)

    bh_min = min(b["h"] for b in bands)
    hz = max(5, round(bh_min * 0.13))
    font = None
    if opts["numbers"] and hz / s >= 9:
        font = _timeline_font(max(7, round(hz * 0.62)))

    for band in bands:
        g = max(1, round(band["h"] * 0.02))
        sy0, sy1 = band["y0"] + g, band["y1"] - g
        band["g"], band["hz"] = g, hz
        band["fy0"] = sy0 + hz + max(1, round(band["h"] * 0.015))
        band["fy1"] = sy1 - hz - max(1, round(band["h"] * 0.015))

        # lay mau nen tai vi tri lo TRUOC khi ve dai -> gia lap duc lo
        hw = max(3, round(hz * 0.60))
        spacing = round(hw * 2.3)
        cy_top, cy_bot = sy0 + hz // 2, sy1 - hz // 2
        holes = []
        x = band["x0"] + spacing
        while x + hw // 2 < band["x1"] - spacing // 2:
            for cy in (cy_top, cy_bot):
                px = min(max(x, 0), canvas.width - 1)
                py = min(max(cy, 0), canvas.height - 1)
                holes.append((x, cy, canvas.getpixel((px, py))))
            x += spacing

        rad = max(2, round(band["h"] * 0.03))
        d.rounded_rectangle([band["x0"], sy0, band["x1"] - 1, sy1 - 1],
                            radius=rad, fill=strip)
        hr = max(1, round(hw * 0.3))
        for (hx, hy, c_bg) in holes:
            d.rounded_rectangle([hx - hw // 2, hy - hw // 2,
                                 hx + hw // 2, hy + hw // 2],
                                radius=hr, fill=c_bg)

    return {"bands": bands, "by_y0": by_y0, "s": s, "u": u, "col": col,
            "font": font}


def _paste_film_frame(canvas: Image.Image, path: Path, cell: Cell, ctx: dict) -> None:
    band = ctx["by_y0"][cell.y0]
    fx = max(2, round(cell.w * 0.05))
    x0, x1 = cell.x0 + fx, cell.x1 - fx
    fy0, fy1 = band["fy0"], band["fy1"]
    if x1 - x0 < 8 or fy1 - fy0 < 8:
        piece = _load_for_cell(path, max(4, cell.w), max(4, cell.h))
        canvas.paste(piece, (cell.x0, cell.y0))
        piece.close()
        return
    photo = _load_for_cell(path, x1 - x0, fy1 - fy0)
    canvas.paste(photo, (x0, fy0))
    photo.close()
    f = ctx["font"]
    if f:  # so khung nho mau cam phim o mep duoi (nhu ma canh phim)
        d = ImageDraw.Draw(canvas)
        d.text((x1, band["y1"] - band["g"] - band["hz"] // 2),
               str(cell.index + 1), font=f, fill=ctx["col"]["film_num"],
               anchor="rm")


# ---------------------------------------------------------------- string

def _string_y(band: dict, x: int) -> int:
    """Cao do day vong tai hoanh do x (bezier bac 2 doi xung)."""
    t = (x - band["x0"]) / max(1, band["x1"] - band["x0"])
    ya, sag = band["ya"], band["sag"]
    return round((1 - t) ** 2 * ya + 2 * (1 - t) * t * (ya + 2 * sag) + t * t * ya)


def _string_ctx(
    canvas: Image.Image, cells: list[Cell], width_s: int, height_s: int, s: int,
    theme: Optional[dict], bg: str, opts: dict,
) -> dict:
    """Day treo anh: day vong nhe qua moi dai, anh polaroid kep go."""
    bands, by_y0 = _bands_of(cells)
    u = min(width_s, height_s)
    line_w = max(2, round(u * 0.0042))
    col = _info_colors(theme, bg, opts)
    d = ImageDraw.Draw(canvas)
    for band in bands:
        band["ya"] = band["y0"] + round(band["h"] * 0.10)
        band["sag"] = round(band["h"] * 0.055)
        pts = []
        n_seg = 36
        for i in range(n_seg + 1):
            x = band["x0"] + round((band["x1"] - band["x0"]) * i / n_seg)
            pts.append((x, _string_y(band, x)))
        d.line(pts, fill=col["string"], width=line_w, joint="curve")
        kr = max(2, round(line_w * 1.6))
        for (kx, ky) in (pts[0], pts[-1]):
            d.ellipse([kx - kr, ky - kr, kx + kr, ky + kr], fill=col["string"])
    return {"bands": bands, "by_y0": by_y0, "line_w": line_w, "s": s, "u": u,
            "col": col, "rng": random.Random(77), "opts": opts}


def _paste_string_card(canvas: Image.Image, path: Path, cell: Cell, ctx: dict) -> None:
    """Polaroid treo day: xoay nhe, kep go, chu thich ten anh o le duoi."""
    band = ctx["by_y0"][cell.y0]
    ccx = (cell.x0 + cell.x1) // 2
    y_att = _string_y(band, ccx)
    pad = max(2, round(min(cell.w, cell.h) * 0.05))
    avail_w = cell.w - 2 * pad
    avail_h = cell.y1 - pad - y_att
    if avail_w < 16 or avail_h < 16:
        piece = _load_for_cell(path, max(4, cell.w), max(4, cell.h))
        canvas.paste(piece, (cell.x0, cell.y0))
        piece.close()
        return

    b = max(2, round(ctx["u"] * 0.0045))
    bot = round(2.6 * b)
    rot = ctx["rng"].uniform(-3.5, 3.5)
    rad = math.radians(abs(rot))
    co, si = math.cos(rad), math.sin(rad)

    # anh vuong canh s_size sao cho the (sau khi xoay) lot vua vung treo
    s0 = min(avail_w, avail_h)
    cw0, ch0 = s0 + 2 * b, s0 + b + bot
    k = min(0.97 * avail_w / (cw0 * co + ch0 * si),
            0.97 * avail_h / (cw0 * si + ch0 * co), 1.0)
    s_size = max(8, int(s0 * k))
    card_w, card_h = s_size + 2 * b, s_size + b + bot

    card = Image.new("RGB", (card_w, card_h), ctx["col"]["card"])
    photo = _load_for_cell(path, s_size, s_size)
    card.paste(photo, (b, b))
    photo.close()
    if ctx["opts"]["captions"] and bot / ctx["s"] >= 10:  # chu thich le duoi
        f = _font_cached(ctx, max(8, round(bot * 0.48)))
        if f:
            label = _fit_text(path.stem, f, s_size)
            if label:
                cy_lbl = b + s_size + (card_h - b - s_size) // 2
                ImageDraw.Draw(card).text((card_w // 2, cy_lbl), label,
                                          font=f, fill=(120, 113, 108),
                                          anchor="mm")

    card = card.convert("RGBA").rotate(rot, expand=True,
                                       resample=Image.Resampling.BICUBIC)
    spad = 12
    shadow = Image.new("RGBA", (card.width + spad * 2, card.height + spad * 2),
                       (0, 0, 0, 0))
    black = Image.new("RGBA", card.size, (20, 18, 16, 110))
    shadow.paste(black, (spad, spad), card.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))

    px = ccx - card.width // 2
    py = y_att - max(1, b // 2)
    canvas.paste(shadow, (px - spad + 3, py - spad + 5), shadow)
    canvas.paste(card, (px, py), card)

    # kep go de len day + mep the
    pw_pin = max(4, round(s_size * 0.11))
    ph_pin = max(6, round(pw_pin * 1.9))
    d = ImageDraw.Draw(canvas)
    x0p = ccx - pw_pin // 2
    y0p = y_att - round(ph_pin * 0.45)
    d.rounded_rectangle([x0p, y0p, x0p + pw_pin, y0p + ph_pin],
                        radius=max(1, round(pw_pin * 0.35)),
                        fill=(196, 158, 110), outline=(141, 107, 70),
                        width=max(1, ctx["line_w"] // 2))
    d.line([(ccx, y0p + ph_pin // 2), (ccx, y0p + ph_pin - 2)],
           fill=(141, 107, 70), width=max(1, pw_pin // 4))


# ---------------------------------------------------------------- steps

def _steps_ctx(
    canvas: Image.Image, cells: list[Cell], width_s: int, height_s: int, s: int,
    theme: Optional[dict], bg: str, opts: dict,
) -> dict:
    """Bac thang tien buoc: the anh dat tren bac, duong bac di len theo dong."""
    bands, by_y0 = _bands_of(cells)
    u = min(width_s, height_s)
    line_w = max(2, round(u * 0.0042))
    col = _info_colors(theme, bg, opts)
    d = ImageDraw.Draw(canvas)
    tread_w = max(3, round(line_w * 1.6))

    bh = min(b["h"] for b in bands)
    mw = min(b["min_w"] for b in bands)
    rb = max(4, min(round(bh * 0.065), round(mw * 0.16), round(u * 0.018)))
    font = _timeline_font(max(8, round(rb * 1.1))) \
        if opts["numbers"] and (2 * rb) / s >= 12 else None

    for band in bands:
        flow = sorted(band["cells"], key=lambda c: c.index)
        k = len(flow)
        rise = round(band["h"] * 0.30)
        base = band["y1"] - max(2, round(band["h"] * 0.05))
        tread: dict[int, int] = {}
        for j, c in enumerate(flow):
            tread[c.index] = base - round(rise * (j + 1) / k)
        band["tread"] = tread

        pts: list[tuple[int, int]] = []
        lw = line_w
        for j, c in enumerate(flow):
            ty = tread[c.index]
            xa, xb = (c.x0, c.x1) if band["lr"] else (c.x1, c.x0)
            if j == 0:
                pts.append((xa + (lw if band["lr"] else -lw), ty))
            else:
                prev = flow[j - 1]
                xm = (prev.x1 + c.x0) // 2 if band["lr"] else (c.x1 + prev.x0) // 2
                pts.append((xm, tread[prev.index]))
                pts.append((xm, ty))
            if j == k - 1:
                pts.append((xb - (lw if band["lr"] else -lw), ty))
        d.line(pts, fill=col["line"], width=tread_w, joint="curve")

    return {"bands": bands, "by_y0": by_y0, "line_w": line_w, "s": s, "u": u,
            "col": col, "badge_r": rb, "font": font, "opts": opts}


def _paste_steps_card(canvas: Image.Image, path: Path, cell: Cell, ctx: dict) -> None:
    band = ctx["by_y0"][cell.y0]
    ty = band["tread"][cell.index]
    pad_x = max(2, round(cell.w * 0.08))
    pad_t = max(2, round(cell.h * 0.04))
    gap = max(2, round(band["h"] * 0.035))
    b = max(2, round(ctx["u"] * 0.0042))

    mw = cell.w - 2 * pad_x
    mh = (ty - gap) - (cell.y0 + pad_t)
    if mw < 12 or mh < 12:
        piece = _load_for_cell(path, max(4, cell.w), max(4, cell.h))
        canvas.paste(piece, (cell.x0, cell.y0))
        piece.close()
        return

    a = min(1.55, max(0.72, _photo_aspect(path)))
    ph = min(mh - 2 * b, (mw - 2 * b) / a)
    pw = max(8, round(ph * a))
    ph = max(8, round(ph))
    card_w, card_h = pw + 2 * b, ph + 2 * b
    cx = cell.x0 + (cell.w - card_w) // 2
    cy = ty - gap - card_h
    _shadow_card(canvas, path, cx, cy, pw, ph, b, ctx["col"]["card"])

    rb, f = ctx["badge_r"], ctx["font"]
    if f:  # huy hieu so dat ngay tren mep bac
        d = ImageDraw.Draw(canvas)
        ccx = (cell.x0 + cell.x1) // 2
        d.ellipse([ccx - rb, ty - rb, ccx + rb, ty + rb],
                  fill=ctx["col"]["accent"], outline=ctx["col"]["card"],
                  width=max(2, round(ctx["line_w"] * 0.8)))
        num = str(cell.index + 1)
        k = 1.0 if len(num) == 1 else (0.8 if len(num) == 2 else 0.6)
        ff = f if k == 1.0 else _font_cached(ctx, max(8, round(rb * 1.1 * k)))
        if ff:
            d.text((ccx, ty), num, font=ff, fill=ctx["col"]["on_accent"],
                   anchor="mm")


# ---------------------------------------------------------------- hexagon

def _hexagon_ctx(
    cells: list[Cell], width_s: int, height_s: int, s: int,
    theme: Optional[dict], bg: str, opts: dict,
) -> dict:
    """To ong luc giac: anh cat luc giac dinh nhon + vien sang."""
    u = min(width_s, height_s)
    return {"line_w": max(2, round(u * 0.0042)), "s": s, "u": u,
            "col": _info_colors(theme, bg, opts), "opts": opts}


def _paste_hexagon(canvas: Image.Image, path: Path, cell: Cell, ctx: dict) -> None:
    cw, ch = cell.w, cell.h
    if min(cw, ch) < 16:
        piece = _load_for_cell(path, max(4, cw), max(4, ch))
        canvas.paste(piece, (cell.x0, cell.y0))
        piece.close()
        return
    hw, hh = round(cw * 0.98), round(ch * 0.98)
    ox = cell.x0 + (cw - hw) // 2
    oy = cell.y0 + (ch - hh) // 2
    pts = [(hw // 2, 0), (hw - 1, round(hh * 0.25)), (hw - 1, round(hh * 0.75)),
           (hw // 2, hh - 1), (0, round(hh * 0.75)), (0, round(hh * 0.25))]
    m = _poly_mask(hw, hh, pts)

    pad = max(4, round(ctx["u"] * 0.004))
    sh = Image.new("L", (hw + pad * 2, hh + pad * 2), 0)
    ImageDraw.Draw(sh).polygon([(x + pad, y + pad) for x, y in pts], fill=85)
    sh = sh.filter(ImageFilter.GaussianBlur(pad / 1.8))
    black = Image.new("RGB", sh.size, (12, 14, 18))
    canvas.paste(black, (ox - pad + 2, oy - pad + 3), sh)

    photo = _load_for_cell(path, hw, hh)
    canvas.paste(photo, (ox, oy), m)
    photo.close()
    d = ImageDraw.Draw(canvas)
    outline = [(ox + x, oy + y) for x, y in pts]
    d.line(outline + [outline[0]], fill=ctx["col"]["card"],
           width=max(2, ctx["line_w"] - 1), joint="curve")


# ------------------------------------------------------- dieu phoi infographic

_INFO_STYLES = frozenset({
    "timeline", "timeline-doc", "process", "path",
    "filmstrip", "string", "steps", "hexagon",
})

# ten cong khai cho GUI/CLI: cac layout co tuy chon chi tiet infographic
INFO_LAYOUTS = _INFO_STYLES

# cac layout co cach ve rieng trong renderer (core dua thang style xuong)
STYLED_LAYOUTS = frozenset({"polaroid", "stack"}) | _INFO_STYLES

_INFO_PASTE = {
    "timeline": _paste_timeline_card,
    "timeline-doc": _paste_timeline_doc_card,
    "process": _paste_process_arrow,
    "path": _paste_path_bubble,
    "filmstrip": _paste_film_frame,
    "string": _paste_string_card,
    "steps": _paste_steps_card,
    "hexagon": _paste_hexagon,
}


def _info_prepare(
    style: str,
    canvas: Image.Image,
    cells: list[Cell],
    width_s: int,
    height_s: int,
    s: int,
    theme: Optional[dict],
    bg: str,
    opts: dict,
) -> dict:
    """Dung ctx + ve lop nen (truc, day, dai phim, bac thang...) cho tung kieu."""
    if style == "timeline":
        ctx = _timeline_ctx(cells, width_s, height_s, s, theme, bg, opts)
        _draw_timeline_base(canvas, ctx)
    elif style == "timeline-doc":
        ctx = _timeline_doc_ctx(cells, width_s, height_s, s, theme, bg, opts)
        _draw_timeline_doc_base(canvas, ctx)
    elif style == "process":
        ctx = _process_ctx(cells, width_s, height_s, s, theme, bg, opts)
    elif style == "path":
        ctx = _path_ctx(cells, width_s, height_s, s, theme, bg, opts)
        _draw_path_base(canvas, cells, ctx)
    elif style == "filmstrip":
        ctx = _filmstrip_ctx(canvas, cells, width_s, height_s, s, theme, bg, opts)
    elif style == "string":
        ctx = _string_ctx(canvas, cells, width_s, height_s, s, theme, bg, opts)
    elif style == "steps":
        ctx = _steps_ctx(canvas, cells, width_s, height_s, s, theme, bg, opts)
    else:  # hexagon
        ctx = _hexagon_ctx(cells, width_s, height_s, s, theme, bg, opts)
    return ctx


def _info_finish(style: str, canvas: Image.Image, cells: list[Cell], ctx: dict) -> None:
    """Lop ve sau cung (cham moc + so) cho cac kieu can."""
    if style == "timeline":
        _draw_timeline_dots(canvas, cells, ctx)
    elif style == "timeline-doc":
        _draw_timeline_doc_dots(canvas, cells, ctx)


def _rounded_mask(w: int, h: int, radius: int) -> Image.Image:
    """Mat na bo goc (ve 2x roi thu nho -> canh min)."""
    m = Image.new("L", (w * 2, h * 2), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=radius * 2, fill=255)
    return m.resize((w, h), Image.Resampling.LANCZOS)


def _paste_with_theme(
    canvas: Image.Image,
    piece: Image.Image,
    cell: Cell,
    corner_pct: float,
    shadow: bool,
) -> None:
    """Dan mot o anh len canvas voi bo goc + do bong theo theme."""
    radius = 0
    if corner_pct > 0:
        radius = max(2, round(min(cell.w, cell.h) * corner_pct / 100))
    mask = _rounded_mask(cell.w, cell.h, radius) if radius else None

    if shadow:
        pad = max(6, radius)
        sh = Image.new("L", (cell.w + pad * 2, cell.h + pad * 2), 0)
        d = ImageDraw.Draw(sh)
        d.rounded_rectangle(
            [pad, pad, pad + cell.w - 1, pad + cell.h - 1],
            radius=radius, fill=90,
        )
        sh = sh.filter(ImageFilter.GaussianBlur(pad / 2.2))
        black = Image.new("RGB", sh.size, (10, 12, 16))
        canvas.paste(black, (cell.x0 - pad + 2, cell.y0 - pad + 4), sh)

    if mask:
        canvas.paste(piece, (cell.x0, cell.y0), mask)
    else:
        canvas.paste(piece, (cell.x0, cell.y0))


def render_image(
    paths: list[Path],
    cells: list[Cell],
    width: int,
    height: int,
    bg: str = "#FFFFFF",
    supersample: int = 2,
    style: str = "normal",
    theme: Optional[dict] = None,
    progress: Optional[Callable[[int, int], None]] = None,
    info_opts: Optional[dict] = None,
    adjust: Optional[dict] = None,
) -> Image.Image:
    """Ghep anh theo layout `cells` (toa do da o kich thuoc width*s x height*s)
    roi thu nho ve width x height de tang do net (supersampling).

    style="polaroid": ve moi anh thanh the polaroid xoay nhe co bong do.
    style="stack": anh xoay nhe tu do, bong do, khong khung trang.
    Cac style infographic (timeline, timeline-doc, process, path, filmstrip,
    string, steps, hexagon): ve lop nen + noi dung trong tung o + lop moc.
    theme: dict tu themes.py — nen gradient, bo goc, do bong.
    info_opts: tuy chon chi tiet infographic (xem INFO_OPT_DEFAULTS):
        numbers/captions/markers (bool), num_color/line_color (mau hoac None).
    adjust: chinh rieng tung anh theo ten file, vd {"anh.jpg": {"rot": 90,
        "zoom": 1.5, "dx": -0.4, "dy": 0.0}} — xoay/cat sau trong tung o.
    """
    global _ADJUST
    _ADJUST = {str(k).lower(): dict(v) for k, v in (adjust or {}).items()}
    s = max(1, supersample)
    if theme:
        canvas = make_background(width * s, height * s, theme, bg_override=None)
        corner_pct = float(theme.get("corner_pct", 0))
        shadow = bool(theme.get("shadow", False))
    else:
        canvas = Image.new("RGB", (width * s, height * s), bg)
        corner_pct, shadow = 0.0, False

    info_ctx = None
    if style in _INFO_STYLES and cells:
        opts = dict(INFO_OPT_DEFAULTS)
        if info_opts:
            opts.update({k: v for k, v in info_opts.items() if v is not None})
        info_ctx = _info_prepare(style, canvas, cells, width * s, height * s,
                                 s, theme, bg, opts)

    rng = random.Random(1234)  # co dinh de ket qua lap lai duoc
    total = len(cells)
    for i, cell in enumerate(cells):
        if style == "polaroid":
            _paste_polaroid(canvas, paths[cell.index], cell, rng)
        elif style == "stack":
            _paste_stack(canvas, paths[cell.index], cell, rng)
        elif info_ctx is not None:
            _INFO_PASTE[style](canvas, paths[cell.index], cell, info_ctx)
        else:
            piece = _load_for_cell(paths[cell.index], cell.w, cell.h)
            if corner_pct > 0 or shadow:
                _paste_with_theme(canvas, piece, cell, corner_pct, shadow)
            else:
                canvas.paste(piece, (cell.x0, cell.y0))
            piece.close()
        if progress:
            progress(i + 1, total)

    if info_ctx is not None:
        _info_finish(style, canvas, cells, info_ctx)

    if s > 1:
        canvas = canvas.resize((width, height), Image.Resampling.LANCZOS)
    return canvas


def save_image(img: Image.Image, out_path: Path, jpeg_quality: int = 95) -> Path:
    """Luu anh ra file (.png hoac .jpg chat luong cao)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".png":
        img.save(out_path, "PNG", optimize=True)
    else:
        img.save(out_path, "JPEG", quality=jpeg_quality, subsampling=0, optimize=True)
    return out_path
