"""Ham dieu phoi chinh: tu thu muc anh -> file collage hoan chinh."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Callable, Optional

from PIL import Image

from . import layout, renderer
from .layout import LAYOUT_STYLES
from .presets import PRESETS, get_preset
from .themes import DEFAULT_THEME, THEMES, get_theme

MAX_IMAGES = 300


class CollageError(Exception):
    pass


def unique_path(p: Path) -> Path:
    """Tra ve duong dan chua ton tai: them ' (2)', ' (3)'... nhu Windows."""
    if not p.exists():
        return p
    i = 2
    while True:
        cand = p.with_name(f"{p.stem} ({i}){p.suffix}")
        if not cand.exists():
            return cand
        i += 1


def _match_files(
    files: list[Path], wanted: list[str], limit: Optional[int] = None
) -> tuple[list[int], list[str]]:
    """Khop danh sach ten/duong dan voi files. Tra ve (chi so khop, ten thieu)."""
    sel: list[int] = []
    missing: list[str] = []
    for want in (wanted[:limit] if limit else wanted):
        w = str(want).replace("/", "\\").lower()
        hit = next(
            (i for i, f in enumerate(files)
             if i not in sel and (f.name.lower() == w
                                  or str(f).lower() == w
                                  or str(f).lower().endswith("\\" + w))),
            None,
        )
        if hit is None:
            missing.append(str(want))
        else:
            sel.append(hit)
    return sel, missing


def _prepare(
    folder: Path, order: str, custom_order: Optional[list[str]] = None,
    extra_files: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> tuple[list[Path], list[float], list[str]]:
    """Quet thu muc (+ anh them le), loc anh bot, doc kich thuoc, sap thu tu."""
    warnings: list[str] = []
    if not folder.is_dir():
        raise CollageError(f"Khong tim thay thu muc: {folder}")

    files = renderer.find_images(folder)
    if extra_files:
        known = {str(f).lower() for f in files}
        for e in extra_files:
            p = Path(e)
            if str(p).lower() in known:
                continue
            if p.is_file() and p.suffix.lower() in renderer.SUPPORTED_EXTS:
                files.append(p)
                known.add(str(p).lower())
            else:
                warnings.append(f"Khong them duoc anh: {e}")
    if exclude:
        excl = {str(x).lower() for x in exclude}
        files = [f for f in files if f.name.lower() not in excl]
    if not files:
        raise CollageError(
            "Khong con anh nao de ghep (thu muc trong hoac da bot het anh)."
        )
    if len(files) > MAX_IMAGES:
        warnings.append(
            f"Thu muc co {len(files)} anh, chi dung {MAX_IMAGES} anh dau tien."
        )
        files = files[:MAX_IMAGES]

    files, aspects, errors = renderer.probe_images(files)
    for e in errors:
        warnings.append(f"Bo qua anh loi: {e}")
    if not files:
        raise CollageError("Tat ca anh trong thu muc deu bi loi, khong doc duoc.")

    idx = list(range(len(files)))
    if order == "custom" and custom_order:
        sel, missing = _match_files(files, custom_order)
        if missing:
            show = ", ".join(missing[:5]) + ("..." if len(missing) > 5 else "")
            warnings.append(f"Khong tim thay anh trong thu tu tu chon: {show}")
        if sel:
            idx = sel + [i for i in range(len(files)) if i not in sel]
    elif order == "random":
        random.shuffle(idx)
    elif order == "aspect":
        idx.sort(key=lambda i: -aspects[i])
    files = [files[i] for i in idx]
    aspects = [aspects[i] for i in idx]
    return files, aspects, warnings


def make_collage_image(
    folder: str | Path,
    preset: str = "fb-post",
    layout_style: str = "justified",
    theme: str = DEFAULT_THEME,
    margin: Optional[int] = None,
    outer: Optional[int] = None,
    bg: str = "#FFFFFF",
    order: str = "name",  # name | random | aspect | custom
    custom_order: Optional[list[str]] = None,
    supersample: int = 2,
    progress: Optional[Callable[[int, int], None]] = None,
    preview_max: Optional[int] = None,
    hero_count: int = 1,
    hero_files: Optional[list[str]] = None,
    hero_fill: str = "justified",
    info_opts: Optional[dict] = None,
    adjust: Optional[dict] = None,
    extra_files: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
    meta_out: Optional[dict] = None,
) -> tuple[Image.Image, list[str]]:
    """Ghep anh va tra ve PIL Image (chua luu file).

    theme: ten theme trong themes.py (nen, bo goc, do bong).
    margin/outer: None = tu dong theo theme.
    preview_max: neu dat (vd 560), thu nho kich thuoc dich de xem truoc nhanh.
    order='custom' + custom_order: tu sap vi tri anh — danh sach ten file theo
        thu tu mong muon; anh khong co trong danh sach xep sau theo ten.
    hero_count: so anh chu dao (chi dung cho layout 'hero', 1-6).
    hero_files: chon dich danh anh chu (ten file hoac duong dan) — cac anh
        nay duoc dua len dau va hero_count = so anh tim thay.
    hero_fill: kieu xep cac anh phu quanh hero (justified | grid | masonry).
    info_opts: tuy chon chi tiet cho layout infographic (timeline, process...):
        numbers/captions/markers (bool), num_color/line_color (mau hoac None).
    adjust: chinh rieng tung anh theo ten file: {"anh.jpg": {"rot": 90,
        "zoom": 1.5, "dx": -0.4, "dy": 0.0}} — xoay (doi ca ti le layout),
        phong to vung cat va doi cua so cat trong o.
    extra_files: duong dan anh them vao ngoai thu muc.
    exclude: ten anh bot khoi ban ghep.
    meta_out: neu truyen dict, se duoc dien "files" (thu tu anh da dung) va
        "cells" [(x0,y0,x1,y1)...] theo toa do anh ket qua — cho GUI keo tha.
    """
    if preset not in PRESETS:
        raise CollageError(
            f"Preset khong hop le: {preset}. Chon mot trong: {', '.join(PRESETS)}"
        )
    if layout_style not in LAYOUT_STYLES:
        raise CollageError(
            f"Kieu layout khong hop le: {layout_style}. "
            f"Chon mot trong: {', '.join(LAYOUT_STYLES)}"
        )
    if theme not in THEMES:
        raise CollageError(
            f"Theme khong hop le: {theme}. Chon mot trong: {', '.join(THEMES)}"
        )
    if hero_fill not in ("justified", "grid", "masonry"):
        raise CollageError(
            f"Kieu xep anh phu khong hop le: {hero_fill}. "
            "Chon: justified, grid, masonry"
        )
    if info_opts:
        from PIL import ImageColor
        for key in ("num_color", "line_color"):
            val = info_opts.get(key)
            if val:
                try:
                    ImageColor.getrgb(str(val).strip())
                except ValueError:
                    raise CollageError(
                        f"Mau khong hop le: {val} (dung ma hex nhu #E11D48 "
                        "hoac ten mau tieng Anh nhu red, orange)"
                    )
    theme_cfg = get_theme(theme)
    if margin is None:
        margin = int(theme_cfg["margin"])
    if outer is None:
        outer = int(theme_cfg["outer"])

    files, aspects, warnings = _prepare(Path(folder), order, custom_order,
                                        extra_files=extra_files,
                                        exclude=exclude)

    # anh bi xoay 90/270 -> dao ti le de layout tu thich nghi
    if adjust:
        adj_low = {str(k).lower(): v for k, v in adjust.items()}
        for i, f in enumerate(files):
            if int(adj_low.get(f.name.lower(), {}).get("rot", 0)) % 180 == 90:
                aspects[i] = 1.0 / max(1e-6, aspects[i])

    # chon dich danh anh chu: dua len dau danh sach (hero / giua / xoan oc)
    if hero_files and layout_style in ("hero", "hero-center", "golden"):
        sel, missing = _match_files(files, hero_files, limit=6)
        if missing:
            warnings.append("Khong tim thay anh chu: " + ", ".join(missing))
        if sel:
            rest = [i for i in range(len(files)) if i not in sel]
            files = [files[i] for i in sel] + [files[i] for i in rest]
            aspects = [aspects[i] for i in sel] + [aspects[i] for i in rest]
            hero_count = len(sel)

    width, height = get_preset(preset)
    if preview_max:
        k = min(1.0, preview_max / max(width, height))
        width = max(64, round(width * k))
        height = max(64, round(height * k))
        margin = max(1 if margin > 0 else 0, round(margin * k))
        outer = round(outer * k)
        supersample = 1

    s = max(1, supersample)
    # Bao ve RAM: canvas sieu lay mau qua lon (vd 8K x2 x3) -> tu giam
    MAX_CANVAS_PX = 150_000_000
    while s > 1 and (width * s) * (height * s) > MAX_CANVAS_PX:
        s -= 1
        warnings.append(
            f"Dau ra rat lon ({width}x{height}), da giam sieu lay mau xuong "
            f"{s}x de tiet kiem bo nho (chat luong van rat cao)."
        )
    cells = layout.compute_style_layout(
        layout_style, aspects, width * s, height * s,
        margin=margin * s, outer=outer * s, hero_count=hero_count,
        fill_style=hero_fill,
    )

    mcs = layout.min_cell_size(cells) // s
    if not preview_max and mcs < 32:
        warnings.append(
            f"Rat nhieu anh cho kho nay: moi anh chi rong ~{mcs}px. "
            "Nen chon preset lon hon (vd. ppt/fb-post) hoac bot anh."
        )

    style = layout_style if layout_style in renderer.STYLED_LAYOUTS else "normal"
    img = renderer.render_image(
        files, cells, width, height,
        bg=bg, supersample=s, style=style,
        theme=None if theme == "classic" else theme_cfg,
        progress=progress, info_opts=info_opts, adjust=adjust,
    )
    if meta_out is not None:
        by_index = {c.index: c for c in cells}
        meta_out["files"] = list(files)
        meta_out["cells"] = [
            (by_index[i].x0 // s, by_index[i].y0 // s,
             by_index[i].x1 // s, by_index[i].y1 // s)
            for i in range(len(files))
        ]
    return img, warnings


def make_template_collage_image(
    files: list[str | Path],
    template: str = "",
    preset: str = "fb-post",
    theme: str = DEFAULT_THEME,
    margin: Optional[int] = None,
    outer: Optional[int] = None,
    bg: str = "#FFFFFF",
    supersample: int = 2,
    progress: Optional[Callable[[int, int], None]] = None,
    preview_max: Optional[int] = None,
    adjust: Optional[dict] = None,
    meta_out: Optional[dict] = None,
) -> tuple[Image.Image, list[str]]:
    """Ghep nhanh 2-9 anh theo bo cuc mau co dinh (templates.py).

    files: danh sach duong dan anh THEO THU TU o cua template (o 1 = anh 1).
    template: id bo cuc (vd "4-4"); rong/khong hop le -> dung mau dau tien.
    Cac tham so preset/theme/margin/outer/bg/adjust/preview_max/meta_out nhu
    make_collage_image. Tra ve (PIL Image, canh bao).
    """
    from . import templates as tpl_mod

    if preset not in PRESETS:
        raise CollageError(
            f"Preset khong hop le: {preset}. Chon mot trong: {', '.join(PRESETS)}"
        )
    if theme not in THEMES:
        raise CollageError(
            f"Theme khong hop le: {theme}. Chon mot trong: {', '.join(THEMES)}"
        )
    warnings: list[str] = []
    paths: list[Path] = []
    seen: set[str] = set()
    for f in files:
        p = Path(f)
        key = str(p).lower()
        if key in seen:
            continue
        if p.is_file() and p.suffix.lower() in renderer.SUPPORTED_EXTS:
            paths.append(p)
            seen.add(key)
        else:
            warnings.append(f"Bo qua anh khong hop le: {f}")
    paths = paths[:tpl_mod.TEMPLATE_MAX]
    paths, _aspects, errors = renderer.probe_images(paths)
    for e in errors:
        warnings.append(f"Bo qua anh loi: {e}")
    n = len(paths)
    if n < tpl_mod.TEMPLATE_MIN:
        raise CollageError(
            f"Can chon it nhat {tpl_mod.TEMPLATE_MIN} anh hop le de ghep nhanh "
            f"(hien co {n})."
        )

    tpl, fallback = tpl_mod.get_template(template, n)
    if fallback and template:
        warnings.append(
            f"Bo cuc '{template}' khong dung cho {n} anh, da dung mau "
            f"'{tpl['name']}'."
        )

    theme_cfg = get_theme(theme)
    if margin is None:
        margin = int(theme_cfg["margin"])
    if outer is None:
        outer = int(theme_cfg["outer"])

    width, height = get_preset(preset)
    if preview_max:
        k = min(1.0, preview_max / max(width, height))
        width = max(64, round(width * k))
        height = max(64, round(height * k))
        margin = max(1 if margin > 0 else 0, round(margin * k))
        outer = round(outer * k)
        supersample = 1

    s = max(1, supersample)
    MAX_CANVAS_PX = 150_000_000
    while s > 1 and (width * s) * (height * s) > MAX_CANVAS_PX:
        s -= 1
        warnings.append(
            f"Dau ra rat lon ({width}x{height}), da giam sieu lay mau xuong "
            f"{s}x de tiet kiem bo nho (chat luong van rat cao)."
        )
    try:
        cells = tpl_mod.template_cells(tpl, width * s, height * s,
                                       margin=margin * s, outer=outer * s)
    except ValueError as e:
        raise CollageError(str(e))

    img = renderer.render_image(
        paths, cells, width, height,
        bg=bg, supersample=s, style="normal",
        theme=None if theme == "classic" else theme_cfg,
        progress=progress, adjust=adjust,
    )
    if meta_out is not None:
        meta_out["files"] = list(paths)
        meta_out["cells"] = [
            (c.x0 // s, c.y0 // s, c.x1 // s, c.y1 // s) for c in cells
        ]
        meta_out["template"] = tpl["id"]
    return img, warnings


def make_template_collage(
    files: list[str | Path],
    template: str = "",
    preset: str = "fb-post",
    theme: str = DEFAULT_THEME,
    out: Optional[str | Path] = None,
    margin: Optional[int] = None,
    outer: Optional[int] = None,
    bg: str = "#FFFFFF",
    supersample: int = 2,
    jpeg_quality: int = 95,
    overwrite: bool = False,
    progress: Optional[Callable[[int, int], None]] = None,
    adjust: Optional[dict] = None,
) -> tuple[Path, list[str]]:
    """Ghep nhanh 2-9 anh theo template va luu file.

    Mac dinh luu canh anh dau tien: collage_nhanh_<template>_<preset>.jpg
    (tu tranh trung ten nhu make_collage).
    """
    img, warnings = make_template_collage_image(
        files, template=template, preset=preset, theme=theme,
        margin=margin, outer=outer, bg=bg, supersample=supersample,
        progress=progress, adjust=adjust,
    )
    if out is None:
        base = Path(files[0]).parent if files else Path(".")
        tid = template.replace("/", "-") if template else "auto"
        out_path = base / f"collage_nhanh_{tid}_{preset}.jpg"
    else:
        out_path = Path(out)
        if out_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            out_path = out_path.with_suffix(".jpg")
    if not overwrite:
        out_path = unique_path(out_path)

    renderer.save_image(img, out_path, jpeg_quality=jpeg_quality)
    return out_path, warnings


def make_collage(
    folder: str | Path,
    preset: str = "fb-post",
    layout_style: str = "justified",
    theme: str = DEFAULT_THEME,
    out: Optional[str | Path] = None,
    margin: Optional[int] = None,
    outer: Optional[int] = None,
    bg: str = "#FFFFFF",
    order: str = "name",
    custom_order: Optional[list[str]] = None,
    supersample: int = 2,
    jpeg_quality: int = 95,
    overwrite: bool = False,
    progress: Optional[Callable[[int, int], None]] = None,
    hero_count: int = 1,
    hero_files: Optional[list[str]] = None,
    hero_fill: str = "justified",
    info_opts: Optional[dict] = None,
    adjust: Optional[dict] = None,
    extra_files: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> tuple[Path, list[str]]:
    """Ghep toan bo anh trong `folder` va luu file.

    Ten file tu dong tranh trung: collage_<preset>_<layout>_<theme>.jpg, neu
    da ton tai thi them ' (2)', ' (3)'... (tru khi overwrite=True).
    Tra ve (duong dan file ket qua, danh sach canh bao).
    """
    folder = Path(folder)
    img, warnings = make_collage_image(
        folder, preset=preset, layout_style=layout_style, theme=theme,
        margin=margin, outer=outer, bg=bg, order=order,
        custom_order=custom_order,
        supersample=supersample, progress=progress, hero_count=hero_count,
        hero_files=hero_files, hero_fill=hero_fill, info_opts=info_opts,
        adjust=adjust, extra_files=extra_files, exclude=exclude,
    )

    if out is None:
        out_path = folder / f"collage_{preset}_{layout_style}_{theme}.jpg"
    else:
        out_path = Path(out)
        if out_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            out_path = out_path.with_suffix(".jpg")
    if not overwrite:
        out_path = unique_path(out_path)

    renderer.save_image(img, out_path, jpeg_quality=jpeg_quality)
    return out_path, warnings
