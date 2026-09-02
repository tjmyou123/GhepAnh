"""Giao dien dong lenh — Ghep anh thong minh, phan mem boi Prodat09.

Vi du:
    python -m smart_collage "D:\\Anh du lich" -p fb-cover
    python -m smart_collage "D:\\Anh" -p ppt -o "D:\\bao_cao.jpg" --margin 6

Trinh chieu anh tu dong voi hieu ung zoom:
    python -m smart_collage show "D:\\Anh" --title "Ky niem he 2026"
    python -m smart_collage show "D:\\Anh" --pptx --dur 4
"""

from __future__ import annotations

import argparse
import sys
import time

from .core import CollageError, make_collage
from .layout import LAYOUT_STYLES
from .presets import DEFAULT_PRESET, PRESETS
from .themes import DEFAULT_THEME, THEMES


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="smart_collage",
        description="Ghep tat ca anh trong mot thu muc thanh 1 anh chat luong cao.",
        epilog="Ghep anh thong minh — (c) 2026 Prodat09",
    )
    p.add_argument("folder", help="Thu muc chua anh dau vao")
    p.add_argument(
        "-p", "--preset", default=DEFAULT_PRESET, choices=list(PRESETS),
        help="Kich thuoc dau ra: "
             + "; ".join(f"{k} = {v[0]}" for k, v in PRESETS.items()),
    )
    p.add_argument(
        "-l", "--layout", default="justified", choices=list(LAYOUT_STYLES),
        help="Kieu xep anh: "
             + "; ".join(f"{k} = {v}" for k, v in LAYOUT_STYLES.items()),
    )
    p.add_argument(
        "-t", "--theme", default=DEFAULT_THEME, choices=list(THEMES),
        help="Theme trang tri: "
             + "; ".join(f"{k} = {v['label']}" for k, v in THEMES.items()),
    )
    p.add_argument("-o", "--out", default=None,
                   help="File ket qua (.jpg/.png). Mac dinh: collage_<preset>_<layout>.jpg "
                        "trong thu muc anh, tu dong tranh trung ten")
    p.add_argument("--overwrite", action="store_true",
                   help="Ghi de neu file da ton tai (mac dinh: tu them ' (2)', ' (3)'...)")
    p.add_argument("--margin", type=int, default=None,
                   help="Khoang cach giua cac anh (px). Mac dinh: theo theme")
    p.add_argument("--outer", type=int, default=None,
                   help="Le ngoai xung quanh (px). Mac dinh: theo theme")
    p.add_argument("--bg", default="#FFFFFF",
                   help="Mau nen, vd #FFFFFF hoac #000000")
    p.add_argument("--order", default="name",
                   choices=["name", "random", "aspect"],
                   help="Thu tu anh: name = theo ten file; random = ngau nhien; "
                        "aspect = gom theo ti le (it phai cat anh nhat)")
    p.add_argument("--heroes", type=int, default=1, choices=range(1, 7),
                   metavar="1-6",
                   help="So anh chu dao cho layout 'hero' (mac dinh 1). "
                        ">=2: cac anh chu xep thanh dai lon tren cung")
    p.add_argument("--hero", action="append", default=None, metavar="TEN_FILE",
                   help="Chon dich danh anh chu theo ten file (lap lai duoc, "
                        "toi da 6 lan). Vd: --hero em_be.jpg --hero hoa.png")
    p.add_argument("--hero-fill", default="justified",
                   choices=["justified", "grid", "masonry"],
                   help="Kieu xep cac anh phu quanh anh chu (layout 'hero'): "
                        "justified = hang can bang; grid = luoi deu; "
                        "masonry = cot kieu Pinterest")
    p.add_argument("--no-numbers", action="store_true",
                   help="An so thu tu (cham moc timeline, huy hieu buoc, "
                        "so khung phim) o cac layout infographic")
    p.add_argument("--no-captions", action="store_true",
                   help="An nhan ten anh (timeline, timeline-doc, string)")
    p.add_argument("--no-markers", action="store_true",
                   help="An diem xuat phat + mui ten ket thuc (timeline)")
    p.add_argument("--num-color", default=None, metavar="MAU",
                   help="Mau so/huy hieu so, vd #E11D48 hoac orange "
                        "(mac dinh: tu dong theo nen)")
    p.add_argument("--line-color", default=None, metavar="MAU",
                   help="Mau truc/duong noi/day treo, vd #0EA5E9 "
                        "(mac dinh: tu dong theo nen)")
    p.add_argument("--scale", type=int, default=2, choices=[1, 2, 3],
                   help="He so sieu lay mau de anh net hon (mac dinh 2)")
    p.add_argument("--quality", type=int, default=95,
                   help="Chat luong JPEG 1-100 (mac dinh 95)")
    return p


def build_show_parser() -> argparse.ArgumentParser:
    from .slides_themes import SLIDE_THEMES

    p = argparse.ArgumentParser(
        prog="smart_collage show",
        description="Trinh chieu anh tu dong voi hieu ung zoom in/out "
                    "(Ken Burns) — chi can chon thu muc anh.",
    )
    p.add_argument("folder", help="Thu muc chua anh")
    p.add_argument("--html", action="store_true",
                   help="Xuat HTML tu chay (mac dinh)")
    p.add_argument("--pptx", action="store_true",
                   help="Xuat PowerPoint co zoom + fade + tu chuyen slide")
    p.add_argument("--all", action="store_true", help="Xuat ca hai")
    p.add_argument("-o", "--out", default=None,
                   help="File ket qua (mac dinh: slideshow.html/.pptx trong thu muc)")
    p.add_argument("-t", "--theme", default="gallery-black",
                   choices=list(SLIDE_THEMES),
                   help="Mau nen/chu cho slide tieu de va collage mo dau")
    p.add_argument("--title", default="", help="Tieu de slide mo dau (bo trong = khong co)")
    p.add_argument("--subtitle", default="", help="Dong phu duoi tieu de")
    p.add_argument("--dur", type=float, default=5.0,
                   help="So giay moi anh (mac dinh 5)")
    p.add_argument("--zoom", type=int, default=12,
                   help="Muc zoom %% (4-40, mac dinh 12)")
    p.add_argument("--order", default="name", choices=["name", "random"],
                   help="Thu tu anh")
    p.add_argument("--captions", action="store_true",
                   help="Hien ten file duoi moi anh (HTML)")
    p.add_argument("--no-intro", action="store_true",
                   help="Bo slide collage mo dau (mac dinh: tu them khi >= 4 anh)")
    p.add_argument("--no-loop", action="store_true",
                   help="Khong lap lai khi het anh (HTML)")
    p.add_argument("--size", default="16:9", choices=["16:9", "4:3"],
                   help="Ti le man hinh")
    p.add_argument("--overwrite", action="store_true", help="Ghi de file cu")
    p.add_argument("--open", action="store_true", dest="open_result",
                   help="Mo file sau khi xuat")
    return p


def show_main(argv) -> int:
    from .slideshow import export_slideshow_html, export_slideshow_pptx

    args = build_show_parser().parse_args(argv)

    def status(msg: str) -> None:
        print(f"\r  {msg}", end="", flush=True)

    common = dict(
        theme=args.theme, duration=args.dur, zoom=args.zoom,
        title=args.title, subtitle=args.subtitle, order=args.order,
        intro=False if args.no_intro else None, size=args.size,
        overwrite=args.overwrite, status=status,
    )
    outputs: list = []
    warnings: list[str] = []
    try:
        if args.html or args.all or not (args.pptx or args.all):
            out, warns = export_slideshow_html(
                args.folder, out=args.out, captions=args.captions,
                loop=not args.no_loop, **common)
            outputs.append(out)
            warnings.extend(warns)
            print()
        if args.pptx or args.all:
            out_arg = None if (outputs and args.out) else args.out
            out, warns = export_slideshow_pptx(
                args.folder, out=out_arg, **common)
            outputs.append(out)
            warnings.extend(warns)
            print()
    except CollageError as e:
        print(f"\nLoi: {e}", file=sys.stderr)
        return 1

    for w in dict.fromkeys(warnings):
        print(f"  Luu y: {w}")
    for out in outputs:
        print(f"Xong -> {out}")
    if args.open_result:
        import os
        for out in outputs:
            os.startfile(out)  # noqa: S606 - mo file local do user tao
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    if argv and argv[0] == "show":
        return show_main(argv[1:])
    args = build_parser().parse_args(argv)

    last = {"pct": -1}

    def progress(done: int, total: int) -> None:
        pct = done * 100 // total
        if pct != last["pct"] and pct % 5 == 0:
            last["pct"] = pct
            print(f"\r  Dang ghep... {pct:3d}% ({done}/{total} anh)", end="", flush=True)

    t0 = time.time()
    try:
        out_path, warnings = make_collage(
            args.folder, preset=args.preset, layout_style=args.layout,
            theme=args.theme, out=args.out, margin=args.margin,
            outer=args.outer, bg=args.bg, order=args.order,
            supersample=args.scale, jpeg_quality=args.quality,
            overwrite=args.overwrite, progress=progress,
            hero_count=args.heroes, hero_files=args.hero,
            hero_fill=args.hero_fill,
            info_opts=dict(
                numbers=not args.no_numbers,
                captions=not args.no_captions,
                markers=not args.no_markers,
                num_color=args.num_color,
                line_color=args.line_color,
            ),
        )
    except CollageError as e:
        print(f"Loi: {e}", file=sys.stderr)
        return 1

    print()
    for w in warnings:
        print(f"  Canh bao: {w}")
    print(f"Xong sau {time.time() - t0:.1f}s -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
