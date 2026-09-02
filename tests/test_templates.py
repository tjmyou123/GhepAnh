"""Kiem tra bo cuc mau 2-9 anh: phu kin, khong chong cheo, o hop le."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smart_collage.templates import TEMPLATES, get_template, template_cells  # noqa: E402


def check_norm(tpl):
    cells = tpl["cells"]
    area = 0.0
    for (x, y, w, h) in cells:
        assert -1e-9 <= x and -1e-9 <= y, f"{tpl['id']}: goc am"
        assert x + w <= 1 + 1e-9 and y + h <= 1 + 1e-9, f"{tpl['id']}: vuot khung"
        assert w > 0.01 and h > 0.01, f"{tpl['id']}: o qua nho"
        area += w * h
    assert abs(area - 1.0) < 1e-6, f"{tpl['id']}: tong dien tich {area}"
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            ax, ay, aw, ah = cells[i]
            bx, by, bw, bh = cells[j]
            ox = min(ax + aw, bx + bw) - max(ax, bx)
            oy = min(ay + ah, by + bh) - max(ay, by)
            assert ox <= 1e-6 or oy <= 1e-6, (
                f"{tpl['id']}: o {i} va {j} chong cheo {ox:.4f}x{oy:.4f}")


def check_pixels(tpl, w, h, margin, outer):
    cells = template_cells(tpl, w, h, margin=margin, outer=outer)
    assert len(cells) == len(tpl["cells"])
    for c in cells:
        assert c.x0 >= 0 and c.y0 >= 0 and c.x1 <= w and c.y1 <= h, (
            f"{tpl['id']}: cell ngoai khung {c}")
        assert c.w >= 4 and c.h >= 4, f"{tpl['id']}: cell qua nho {c}"
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            a, b = cells[i], cells[j]
            ox = min(a.x1, b.x1) - max(a.x0, b.x0)
            oy = min(a.y1, b.y1) - max(a.y0, b.y0)
            assert ox <= 0 or oy <= 0, (
                f"{tpl['id']} @{w}x{h} m={margin}: chong cheo {i}-{j}")


def main():
    total = 0
    for n in range(2, 10):
        tpls = TEMPLATES[n]
        assert len(tpls) >= 6, f"n={n}: chi co {len(tpls)} mau"
        ids = [t["id"] for t in tpls]
        assert len(set(ids)) == len(ids), f"n={n}: trung id"
        for tpl in tpls:
            assert len(tpl["cells"]) == n, (
                f"{tpl['id']}: co {len(tpl['cells'])} o, can {n}")
            check_norm(tpl)
            for (w, h, m, o) in [(1080, 1080, 8, 0), (1920, 1080, 4, 12),
                                 (1080, 1920, 0, 0), (820, 312, 6, 6)]:
                check_pixels(tpl, w, h, m, o)
            total += 1
    t, fb = get_template("4-4", 4)
    assert t["id"] == "4-4" and not fb
    t, fb = get_template("khong-co", 5)
    assert fb and t["id"] == TEMPLATES[5][0]["id"]
    print(f"OK: {total} bo cuc mau (2-9 anh) deu hop le "
          "(phu kin, khong chong cheo, du kich thuoc)")


if __name__ == "__main__":
    main()
