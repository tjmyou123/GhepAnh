"""Bo cuc mau co dinh cho che do "Ghep nhanh 2-9 anh".

Moi template la danh sach o (x, y, w, h) theo toa do chuan hoa 0..1,
phu kin khung va khong chong cheo. Thu tu o = thu tu anh (o dau tien
thuong la o LON nhat de anh so 1 noi bat).
"""

from __future__ import annotations

from .layout import Cell

Rect = tuple[float, float, float, float]


def _rows(*rows: tuple[float, list[float]]) -> list[Rect]:
    """Chia khung thanh cac hang: (chieu cao tuong doi, [do rong tung o])."""
    th = float(sum(h for h, _ in rows))
    out: list[Rect] = []
    y = 0.0
    for h, ws in rows:
        rh = h / th
        tw = float(sum(ws))
        x = 0.0
        for w in ws:
            rw = w / tw
            out.append((x, y, rw, rh))
            x += rw
        y += rh
    return out


def _cols(*cols: tuple[float, list[float]]) -> list[Rect]:
    """Chia khung thanh cac cot: (do rong tuong doi, [chieu cao tung o])."""
    return [(y, x, h, w) for (x, y, w, h) in _rows(*cols)]


def _big_first(cells: list[Rect]) -> list[Rect]:
    """Dua o lon nhat len dau de anh so 1 vao o noi bat (sap xep on dinh)."""
    return sorted(cells, key=lambda c: -(c[2] * c[3]))


def _golden(n: int) -> list[Rect]:
    """Xoan oc ti le vang: cat dan 0.618 va xoay chieu, anh 1 lon nhat."""
    phi = 0.6180339887498949
    x, y, w, h = 0.0, 0.0, 1.0, 1.0
    out: list[Rect] = []
    d = 0
    for _ in range(n - 1):
        if d == 0:
            out.append((x, y, w * phi, h))
            x += w * phi
            w *= 1 - phi
        elif d == 1:
            out.append((x, y, w, h * phi))
            y += h * phi
            h *= 1 - phi
        elif d == 2:
            out.append((x + w * (1 - phi), y, w * phi, h))
            w *= 1 - phi
        else:
            out.append((x, y + h * (1 - phi), w, h * phi))
            h *= 1 - phi
        d = (d + 1) % 4
    out.append((x, y, w, h))
    return out


def _flip(cells: list[Rect]) -> list[Rect]:
    """Doi cho x/y (lat cheo bo cuc) de tao bien the ngang/doc."""
    return [(y, x, h, w) for (x, y, w, h) in cells]


def _t(tid: str, name: str, cells: list[Rect]) -> dict:
    return {"id": tid, "name": name, "cells": [tuple(c) for c in cells]}


T = 1.0 / 3.0

TEMPLATES: dict[int, list[dict]] = {
    2: [
        _t("2-1", "2 cột", _cols((1, [1]), (1, [1]))),
        _t("2-2", "2 hàng", _rows((1, [1]), (1, [1]))),
        _t("2-3", "Trái lớn", _cols((2, [1]), (1, [1]))),
        _t("2-4", "Phải lớn", _big_first(_cols((1, [1]), (2, [1])))),
        _t("2-5", "Trên lớn", _rows((2, [1]), (1, [1]))),
        _t("2-6", "Dưới lớn", _big_first(_rows((1, [1]), (2, [1])))),
        _t("2-7", "Tỷ lệ vàng", _golden(2)),
        _t("2-8", "Vàng ngang", _rows((1.618, [1]), (1, [1]))),
        _t("2-9", "Pano trên", _rows((2.6, [1]), (1, [1]))),
        _t("2-10", "Pano dưới", _big_first(_rows((1, [1]), (2.6, [1])))),
    ],
    3: [
        _t("3-1", "3 cột", _cols((1, [1]), (1, [1]), (1, [1]))),
        _t("3-2", "3 hàng", _rows((1, [1]), (1, [1]), (1, [1]))),
        _t("3-3", "1 lớn trái", _cols((2, [1]), (1, [1, 1]))),
        _t("3-4", "1 lớn phải", _big_first(_cols((1, [1, 1]), (2, [1])))),
        _t("3-5", "1 lớn trên", _rows((2, [1]), (1, [1, 1]))),
        _t("3-6", "1 lớn dưới", _big_first(_rows((1, [1, 1]), (2, [1])))),
        _t("3-7", "Cột giữa", _big_first(_cols((1, [1]), (2, [1]), (1, [1])))),
        _t("3-8", "Hàng giữa", _big_first(_rows((1, [1]), (2, [1]), (1, [1])))),
        _t("3-9", "Xoắn vàng", _golden(3)),
        _t("3-10", "Lệch trái", _rows((1.5, [1.8, 1]), (1, [1]))),
        _t("3-11", "Lệch phải", _big_first(_rows((1.5, [1, 1.8]), (1, [1])))),
        _t("3-12", "Xoắn ngang", _flip(_golden(3))),
    ],
    4: [
        _t("4-1", "Lưới 2×2", _rows((1, [1, 1]), (1, [1, 1]))),
        _t("4-2", "4 cột", _cols((1, [1]), (1, [1]), (1, [1]), (1, [1]))),
        _t("4-3", "4 hàng", _rows((1, [1]), (1, [1]), (1, [1]), (1, [1]))),
        _t("4-4", "1 lớn trái", _cols((2, [1]), (1, [1, 1, 1]))),
        _t("4-5", "1 lớn phải", _big_first(_cols((1, [1, 1, 1]), (2, [1])))),
        _t("4-6", "1 lớn trên", _rows((2, [1]), (1, [1, 1, 1]))),
        _t("4-7", "1 lớn dưới", _big_first(_rows((1, [1, 1, 1]), (2, [1])))),
        _t("4-8", "Góc lớn", [(0, 0, 2 * T, 2 * T), (2 * T, 0, T, T),
                              (2 * T, T, T, T), (0, 2 * T, 1.0, T)]),
        _t("4-9", "Xoắn vàng", _golden(4)),
        _t("4-10", "Lệch chéo", _rows((1.4, [1.6, 1]), (1, [1, 1.6]))),
        _t("4-11", "Kẹp giữa", _big_first(_rows((1, [1]), (1.4, [1, 1]),
                                              (1, [1])))),
        _t("4-12", "Xoắn ngang", _flip(_golden(4))),
        _t("4-13", "Cột giữa đôi",
           _big_first(_cols((1, [1]), (1.5, [1, 1]), (1, [1])))),
    ],
    5: [
        _t("5-1", "1 lớn trái", _cols((3, [1]), (2, [1, 1, 1, 1]))),
        _t("5-2", "1 lớn phải", _big_first(_cols((2, [1, 1, 1, 1]), (3, [1])))),
        _t("5-3", "1 lớn trên", _rows((2, [1]), (1, [1, 1, 1, 1]))),
        _t("5-4", "1 lớn dưới", _big_first(_rows((1, [1, 1, 1, 1]), (2, [1])))),
        _t("5-5", "2 + 3", _rows((1, [1, 1]), (1, [1, 1, 1]))),
        _t("5-6", "3 + 2", _rows((1, [1, 1, 1]), (1, [1, 1]))),
        _t("5-7", "5 cột", _cols(*[(1, [1])] * 5)),
        _t("5-8", "Giữa lớn",
           _big_first(_cols((1, [1, 1]), (1.5, [1]), (1, [1, 1])))),
        _t("5-9", "Xoắn vàng", _golden(5)),
        _t("5-10", "Băng giữa",
           _big_first(_rows((1, [1, 1]), (1.4, [1]), (1, [1, 1])))),
        _t("5-11", "Góc lớn", [(0, 0, 2 * T, 2 * T), (2 * T, 0, T, T),
                                (2 * T, T, T, T), (0, 2 * T, 0.5, T),
                                (0.5, 2 * T, 0.5, T)]),
        _t("5-12", "Xoắn ngang", _flip(_golden(5))),
        _t("5-13", "Tháp", _rows((1.6, [1]), (1, [1, 1]), (1, [1, 1]))),
    ],
    6: [
        _t("6-1", "Lưới 2×3", _rows((1, [1, 1, 1]), (1, [1, 1, 1]))),
        _t("6-2", "Lưới 3×2", _rows((1, [1, 1]), (1, [1, 1]), (1, [1, 1]))),
        _t("6-3", "Góc lớn trái", [
            (0, 0, 2 * T, 2 * T), (2 * T, 0, T, T), (2 * T, T, T, T),
            (0, 2 * T, T, T), (T, 2 * T, T, T), (2 * T, 2 * T, T, T)]),
        _t("6-4", "Góc lớn phải", [
            (T, 0, 2 * T, 2 * T), (0, 0, T, T), (0, T, T, T),
            (0, 2 * T, T, T), (T, 2 * T, T, T), (2 * T, 2 * T, T, T)]),
        _t("6-5", "2 lớn trên", _rows((1.6, [1, 1]), (1, [1, 1, 1, 1]))),
        _t("6-6", "2 lớn dưới",
           _big_first(_rows((1, [1, 1, 1, 1]), (1.6, [1, 1])))),
        _t("6-7", "Băng giữa",
           _big_first(_rows((1, [1, 1, 1]), (1.6, [1]), (1, [1, 1])))),
        _t("6-8", "Xoắn vàng", _golden(6)),
        _t("6-9", "Tháp", _rows((1.5, [1]), (1, [1, 1]), (1, [1, 1, 1]))),
        _t("6-10", "Cột giữa",
           _big_first(_cols((1, [1, 1]), (1.6, [1]), (1, [1, 1, 1])))),
        _t("6-11", "2 lớn trái",
           _big_first(_cols((1.6, [1, 1]), (1, [1, 1, 1, 1])))),
        _t("6-12", "Xoắn ngang", _flip(_golden(6))),
    ],
    7: [
        _t("7-1", "3 + 4", _rows((1, [1, 1, 1]), (1, [1, 1, 1, 1]))),
        _t("7-2", "4 + 3", _rows((1, [1, 1, 1, 1]), (1, [1, 1, 1]))),
        _t("7-3", "1 lớn trái", _cols((2, [1]), (1, [1, 1, 1]), (1, [1, 1, 1]))),
        _t("7-4", "1 lớn trên", _rows((2, [1]), (1, [1, 1, 1]), (1, [1, 1, 1]))),
        _t("7-5", "2-3-2", _rows((1, [1, 1]), (1, [1, 1, 1]), (1, [1, 1]))),
        _t("7-6", "Góc lớn", [(0, 0, 2 * T, 2 * T), (2 * T, 0, T, T),
                              (2 * T, T, T, T)]
           + [(i / 4, 2 * T, 1 / 4, T) for i in range(4)]),
        _t("7-7", "7 cột", _cols(*[(1, [1])] * 7)),
        _t("7-8", "Xoắn vàng", _golden(7)),
        _t("7-9", "Giữa lớn",
           _big_first(_cols((1, [1, 1]), (1.6, [1, 3, 1]), (1, [1, 1])))),
        _t("7-10", "Băng giữa",
           _big_first(_rows((1, [1, 1, 1]), (1.5, [1]), (1, [1, 1, 1])))),
        _t("7-11", "Tháp", _rows((1.5, [1]), (1, [1, 1]), (1, [1, 1, 1, 1]))),
        _t("7-12", "2 lớn trên", _rows((1.6, [1, 1]), (1, [1, 1, 1, 1, 1]))),
        _t("7-13", "Xoắn ngang", _flip(_golden(7))),
    ],
    8: [
        _t("8-1", "Lưới 2×4", _rows((1, [1, 1, 1, 1]), (1, [1, 1, 1, 1]))),
        _t("8-2", "Lưới 4×2", _rows(*[(1, [1, 1])] * 4)),
        _t("8-3", "3-2-3",
           _big_first(_rows((1, [1, 1, 1]), (1.4, [1, 1]), (1, [1, 1, 1])))),
        _t("8-4", "2-4-2", _rows((1.3, [1, 1]), (1, [1, 1, 1, 1]),
                                 (1.3, [1, 1]))),
        _t("8-5", "1 lớn + 7", [(0, 0, 2 * T, 2 * T), (2 * T, 0, T, T),
                                (2 * T, T, T, T)]
           + [(i / 5, 2 * T, 1 / 5, T) for i in range(5)]),
        _t("8-6", "Cột giữa",
           _big_first(_cols((1, [1, 1, 1]), (1.4, [1, 1]), (1, [1, 1, 1])))),
        _t("8-7", "8 cột", _cols(*[(1, [1])] * 8)),
        _t("8-8", "Xoắn vàng", _golden(8)),
        _t("8-9", "Tâm điểm",
           _big_first(_rows((1, [1, 1, 1]), (1.5, [1, 2, 1]), (1, [1, 1])))),
        _t("8-10", "Tháp", _rows((1.5, [1]), (1, [1, 1, 1]),
                                  (1, [1, 1, 1, 1]))),
        _t("8-11", "2 lớn trái",
           _big_first(_cols((1.7, [1, 1]), (1, [1, 1, 1]), (1, [1, 1, 1])))),
        _t("8-12", "2 lớn trên", _rows((1.6, [1, 1]), (1, [1, 1, 1]),
                                       (1, [1, 1, 1]))),
    ],
    9: [
        _t("9-1", "Lưới 3×3", _rows(*[(1, [1, 1, 1])] * 3)),
        _t("9-2", "1 lớn trái",
           _cols((2, [1]), (1, [1, 1, 1, 1]), (1, [1, 1, 1, 1]))),
        _t("9-3", "1 lớn trên",
           _rows((2, [1]), (1, [1, 1, 1, 1]), (1, [1, 1, 1, 1]))),
        _t("9-4", "2-3-4", _rows((1, [1, 1]), (1, [1, 1, 1]),
                                 (1, [1, 1, 1, 1]))),
        _t("9-5", "4-3-2", _rows((1, [1, 1, 1, 1]), (1, [1, 1, 1]),
                                 (1, [1, 1]))),
        _t("9-6", "Hàng giữa",
           _big_first(_rows((1, [1, 1, 1]), (1.6, [1, 1, 1]), (1, [1, 1, 1])))),
        _t("9-7", "Cột giữa",
           _big_first(_cols((1, [1, 1, 1]), (1.6, [1, 1, 1]), (1, [1, 1, 1])))),
        _t("9-8", "Tâm điểm",
           _big_first(_rows((1, [1, 1, 1]), (1.5, [1, 2, 1]), (1, [1, 1, 1])))),
        _t("9-9", "Tháp", _rows((1.6, [1]), (1, [1, 1, 1]),
                                 (1, [1, 1, 1, 1, 1]))),
        _t("9-10", "2 lớn trên", _rows((1.5, [1, 1]), (1, [1, 1, 1]),
                                       (1, [1, 1, 1, 1]))),
        _t("9-11", "Băng giữa",
           _big_first(_rows((1, [1, 1, 1, 1]), (1.6, [1]), (1, [1, 1, 1, 1])))),
        _t("9-12", "Trụ giữa",
           _big_first(_cols((1, [1, 1, 1, 1]), (1.6, [1]), (1, [1, 1, 1, 1])))),
    ],
}

TEMPLATE_MIN = min(TEMPLATES)
TEMPLATE_MAX = max(TEMPLATES)


def get_template(tid: str, n: int) -> tuple[dict, bool]:
    """Tra ve (template, da_phai_fallback) cho n anh."""
    tpls = TEMPLATES.get(n)
    if not tpls:
        raise ValueError(
            f"Khong co bo cuc mau cho {n} anh (chi ho tro "
            f"{TEMPLATE_MIN}-{TEMPLATE_MAX} anh)."
        )
    for t in tpls:
        if t["id"] == tid:
            return t, False
    return tpls[0], True


def template_cells(tpl: dict, width: int, height: int,
                   margin: int = 0, outer: int = 0) -> list[Cell]:
    """Doi template chuan hoa -> danh sach Cell pixel (co le trong/ngoai).

    Cac o canh nhau chia deu khoang cach `margin`, mep khung lui vao `outer`.
    """
    iw, ih = width - 2 * outer, height - 2 * outer
    if iw <= 0 or ih <= 0:
        raise ValueError("Le ngoai (outer) qua lon so voi kich thuoc anh ra.")
    m_lo, m_hi = margin // 2, margin - margin // 2
    eps = 1e-6
    cells: list[Cell] = []
    for i, (x, y, w, h) in enumerate(tpl["cells"]):
        x0 = outer + round(x * iw)
        y0 = outer + round(y * ih)
        x1 = outer + round((x + w) * iw)
        y1 = outer + round((y + h) * ih)
        if x > eps:
            x0 += m_lo
        if x + w < 1 - eps:
            x1 -= m_hi
        if y > eps:
            y0 += m_lo
        if y + h < 1 - eps:
            y1 -= m_hi
        if x1 - x0 < 4 or y1 - y0 < 4:
            raise ValueError(
                "Khoang cach qua lon so voi kich thuoc anh ra, hay giam bot."
            )
        cells.append(Cell(index=i, x0=x0, y0=y0, x1=x1, y1=y1))
    return cells
