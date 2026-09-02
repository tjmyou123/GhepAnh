"""Kiem tra thuat toan layout: khong chong cheo, phu kin, moi so luong 1..300.

    python tests/test_layout.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smart_collage.layout import (
    LAYOUT_STYLES,
    compute_style_layout,
    min_cell_size,
    validate_no_overlap,
)
from smart_collage.presets import PRESETS


def check(n: int, w: int, h: int, margin: int = 4, style: str = "justified") -> None:
    rng = random.Random(n)
    aspects = [rng.choice([4 / 3, 3 / 4, 16 / 9, 9 / 16, 1.0, 2.5]) for _ in range(n)]
    cells = compute_style_layout(style, aspects, w, h, margin=margin)

    assert len(cells) == n, f"{style} n={n}: thieu o ({len(cells)}/{n})"
    assert validate_no_overlap(cells), f"{style} n={n} {w}x{h}: CHONG CHEO!"
    for c in cells:
        assert 0 <= c.x0 < c.x1 <= w and 0 <= c.y0 < c.y1 <= h, \
            f"{style} n={n}: o vuot khung {c}"
    # Moi anh xuat hien dung 1 lan
    assert sorted(c.index for c in cells) == list(range(n))
    # Phu kin cac mep khung
    assert min(c.y0 for c in cells) == 0
    assert max(c.y1 for c in cells) == h
    assert min(c.x0 for c in cells) == 0
    assert max(c.x1 for c in cells) == w
    # Rieng hero: anh chu dao phai lon noi bat so voi trung binh
    # (n>=5 dung chu L nen >=2x; n=3..4 chia doc, toi da dat ~1.5x)
    if style == "hero" and n >= 3:
        hero = next(c for c in cells if c.index == 0)
        avg = sum(c.w * c.h for c in cells) / n
        need = 2.0 if n >= 5 else 1.4
        assert hero.w * hero.h >= need * avg, \
            f"hero n={n} {w}x{h}: anh chu chua du lon"


def check_multi_hero(n: int, w: int, h: int, hc: int) -> None:
    rng = random.Random(1000 + n * 7 + hc)
    aspects = [rng.choice([4 / 3, 3 / 4, 16 / 9, 9 / 16, 1.0, 2.5]) for _ in range(n)]
    cells = compute_style_layout("hero", aspects, w, h, margin=4, hero_count=hc)

    assert len(cells) == n, f"multi-hero n={n} hc={hc}: thieu o"
    assert validate_no_overlap(cells), f"multi-hero n={n} hc={hc}: CHONG CHEO!"
    assert sorted(c.index for c in cells) == list(range(n))
    assert min(c.y0 for c in cells) == 0 and max(c.y1 for c in cells) == h
    assert min(c.x0 for c in cells) == 0 and max(c.x1 for c in cells) == w
    if n > hc:
        # cac anh chu phai nam tron trong dai tren, phan con lai o duoi
        hero_bottom = max(c.y1 for c in cells if c.index < hc)
        rest_top = min(c.y0 for c in cells if c.index >= hc)
        assert hero_bottom <= rest_top, \
            f"multi-hero n={n} hc={hc}: dai hero khong tach biet"


def main() -> None:
    counts = list(range(1, 31)) + [40, 47, 60, 75, 100, 130, 150, 200, 250, 299, 300]
    total = 0
    for style in LAYOUT_STYLES:
        for _, w, h in PRESETS.values():
            for n in counts:
                check(n, w, h, style=style)
                total += 1
            # margin lon + nhieu anh -> tu giam margin, van phai hop le
            check(300, w, h, margin=20, style=style)
            check(1, w, h, margin=0, style=style)
            total += 2
    # nhieu anh chu (hero_count 2..6)
    for _, w, h in PRESETS.values():
        for hc in (2, 3, 4, 6):
            for n in [2, 3, 4, 5, 6, 7, 8, 13, 30, 47, 120, 300]:
                check_multi_hero(n, w, h, hc)
                total += 1
    # ket hop hero voi kieu xep anh phu (grid / masonry)
    for _, w, h in PRESETS.values():
        for fill in ("grid", "masonry"):
            for hc in (1, 3):
                for n in [2, 4, 5, 8, 13, 47, 150, 300]:
                    rng = random.Random(n * 13 + hc)
                    aspects = [rng.choice([4 / 3, 3 / 4, 16 / 9, 9 / 16, 1.0, 2.5])
                               for _ in range(n)]
                    cells = compute_style_layout("hero", aspects, w, h, margin=4,
                                                 hero_count=hc, fill_style=fill)
                    assert len(cells) == n
                    assert validate_no_overlap(cells), \
                        f"hero+{fill} n={n} hc={hc}: CHONG CHEO!"
                    assert sorted(c.index for c in cells) == list(range(n))
                    assert min(c.y0 for c in cells) == 0
                    assert max(c.y1 for c in cells) == h
                    assert min(c.x0 for c in cells) == 0
                    assert max(c.x1 for c in cells) == w
                    total += 1
    print(f"OK: {total} truong hop deu hop le (khong chong cheo, phu kin khung).")


if __name__ == "__main__":
    main()
