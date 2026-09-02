"""Thuat toan xep layout thong minh.

Ket hop kinh nghiem tu cac du an mo:
- flickr/justified-layout: xep anh theo hang ngang, moi hang cung chieu cao,
  giu nguyen ti le anh -> tu nhien, dep.
- Skiena's linear partition (quy hoach dong): chia day anh thanh cac hang
  can bang nhau -> hang nao cung day, khong bi hang qua ngan/qua dai.
- adrienverge/PhotoCollage: crop-to-fill tung o de khop chinh xac khung dich,
  khong meo anh, khong chong cheo.

Dam bao hinh hoc: cac o (Cell) duoc sinh ra tu cac khoang [x, x+w] don dieu
tang va cac hang xep tuan tu theo truc y => KHONG THE chong cheo, voi moi
so luong anh (1..300+).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Cell:
    """Mot o anh tren canvas: index la vi tri anh trong danh sach dau vao."""

    index: int
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def w(self) -> int:
        return self.x1 - self.x0

    @property
    def h(self) -> int:
        return self.y1 - self.y0


def _round(v: float) -> int:
    return int(math.floor(v + 0.5))


def _build_partition_table(aspects: list[float], k_max: int):
    """Bang quy hoach dong Skiena: M[j][i] = chi phi toi uu (tong ti le lon
    nhat cua 1 hang) khi chia i anh dau tien thanh j hang. D luu diem cat de
    truy vet."""
    n = len(aspects)
    prefix = [0.0]
    for a in aspects:
        prefix.append(prefix[-1] + a)

    inf = float("inf")
    M = [[inf] * (n + 1) for _ in range(k_max + 1)]
    D = [[0] * (n + 1) for _ in range(k_max + 1)]
    for i in range(1, n + 1):
        M[1][i] = prefix[i]

    for j in range(2, k_max + 1):
        for i in range(j, n + 1):
            best, best_t = inf, j - 1
            # chia i anh dau thanh j hang: hang cuoi la (t..i)
            for t in range(j - 1, i):
                left = M[j - 1][t]
                if left >= best:
                    continue
                v = prefix[i] - prefix[t]
                if v < left:
                    v = left
                if v < best:
                    best, best_t = v, t
            M[j][i] = best
            D[j][i] = best_t
    return D, prefix


def _backtrack_rows(D, n: int, k: int) -> list[list[int]]:
    """Truy vet bang DP -> danh sach hang, moi hang la list chi so anh."""
    rows: list[list[int]] = []
    i = n
    for j in range(k, 1, -1):
        t = D[j][i]
        rows.append(list(range(t, i)))
        i = t
    rows.append(list(range(0, i)))
    rows.reverse()
    return rows


def compute_layout(
    aspects: list[float],
    width: int,
    height: int,
    margin: int = 4,
    outer: int = 0,
) -> list[Cell]:
    """Tinh layout cho `len(aspects)` anh tren canvas width x height.

    aspects: ti le w/h cua tung anh (sau khi xoay EXIF).
    Tra ve danh sach Cell phu kin canvas, khong chong cheo.
    """
    n = len(aspects)
    if n == 0:
        return []

    cw = width - 2 * outer
    ch = height - 2 * outer
    if cw <= 0 or ch <= 0:
        raise ValueError("Le ngoai (outer) qua lon so voi kich thuoc anh ra.")

    aspects = [max(0.05, min(20.0, a)) for a in aspects]
    total_aspect = sum(aspects)

    # Uoc luong so hang ly tuong (cong thuc tuong tu PhotoCollage nhung cho
    # hang ngang): r0 = sqrt(tong_ti_le * H / W)
    r0 = math.sqrt(total_aspect * ch / cw)
    r_lo = max(1, int(math.floor(r0)) - 2)
    r_hi = min(n, max(1, int(math.ceil(r0)) + 2))
    if r_lo > r_hi:
        r_lo = r_hi
    candidates = list(range(r_lo, r_hi + 1))

    D, prefix = _build_partition_table(aspects, r_hi)

    best = None  # (score, rows, row_heights)
    for r in candidates:
        rows_h = ch - (r - 1) * margin  # phan chieu cao danh cho anh
        if rows_h <= r:  # moi hang < 1px -> vo nghia
            continue
        rows = _backtrack_rows(D, n, r)
        heights = []
        feasible = True
        for row in rows:
            k_i = len(row)
            avail = cw - (k_i - 1) * margin
            if avail < k_i:  # moi anh < 1px chieu rong
                feasible = False
                break
            s = prefix[row[-1] + 1] - prefix[row[0]]
            heights.append(avail / s)
        if not feasible:
            continue
        t_rows = sum(heights)
        # score: do lech giua chieu cao tu nhien va chieu cao dich
        score = abs(math.log(t_rows / rows_h))
        if best is None or score < best[0]:
            best = (score, rows, heights)

    if best is None:
        # margin qua lon so voi so anh -> giam margin va thu lai
        if margin > 0:
            return compute_layout(aspects, width, height, margin // 2, outer)
        raise ValueError("Khong the xep layout: qua nhieu anh cho khung nay.")

    _, rows, heights = best
    r = len(rows)
    rows_h = ch - (r - 1) * margin
    f = rows_h / sum(heights)  # he so ep chieu cao ve dung khung dich

    # Sinh toa do pixel. Chieu rong o dua tren chieu cao "tu nhien" h_i de
    # lap day chieu ngang; chieu cao o dung h_i * f de lap day chieu doc.
    # Anh trong o se duoc cover-crop nhe (renderer lo viec nay).
    cells: list[Cell] = []
    y = float(outer)
    for ri, row in enumerate(rows):
        h_nat = heights[ri]
        h_fit = h_nat * f
        y0 = _round(y)
        y1 = height - outer if ri == len(rows) - 1 else _round(y + h_fit)
        if y1 <= y0:
            y1 = y0 + 1
        x = float(outer)
        for ci, idx in enumerate(row):
            w = aspects[idx] * h_nat
            x0 = _round(x)
            x1 = width - outer if ci == len(row) - 1 else _round(x + w)
            if x1 <= x0:
                x1 = x0 + 1
            cells.append(Cell(idx, x0, y0, x1, y1))
            x += w + margin
        y += h_fit + margin

    return cells


def compute_grid_layout(
    n: int,
    width: int,
    height: int,
    margin: int = 4,
    outer: int = 0,
    cell_aspect: float = 4 / 3,
) -> list[Cell]:
    """Luoi deu: cac hang cao bang nhau, moi hang chia deu chieu ngang.

    So hang duoc chon de ti le o gan `cell_aspect` nhat. Hang co the lech
    nhau 1 anh de khong bao gio co lo trong.
    """
    if n == 0:
        return []
    cw = width - 2 * outer
    ch = height - 2 * outer

    best = None  # (score, r)
    for r in range(1, n + 1):
        cols_max = math.ceil(n / r)
        cell_h = (ch - (r - 1) * margin) / r
        cell_w = (cw - (cols_max - 1) * margin) / cols_max
        if cell_h < 1 or cell_w < 1:
            continue
        score = abs(math.log((cell_w / cell_h) / cell_aspect))
        if best is None or score < best[0]:
            best = (score, r)
    if best is None:
        if margin > 0:
            return compute_grid_layout(n, width, height, margin // 2, outer, cell_aspect)
        raise ValueError("Khong the xep luoi: qua nhieu anh cho khung nay.")

    r = best[1]
    base, extra = divmod(n, r)
    row_sizes = [base + 1 if i < extra else base for i in range(r)]

    cells: list[Cell] = []
    row_h = (ch - (r - 1) * margin) / r
    y = float(outer)
    idx = 0
    for ri, k in enumerate(row_sizes):
        y0 = _round(y)
        y1 = height - outer if ri == r - 1 else _round(y + row_h)
        if y1 <= y0:
            y1 = y0 + 1
        cell_w = (cw - (k - 1) * margin) / k
        x = float(outer)
        for ci in range(k):
            x0 = _round(x)
            x1 = width - outer if ci == k - 1 else _round(x + cell_w)
            if x1 <= x0:
                x1 = x0 + 1
            cells.append(Cell(idx, x0, y0, x1, y1))
            idx += 1
            x += cell_w + margin
        y += row_h + margin
    return cells


def compute_masonry_layout(
    aspects: list[float],
    width: int,
    height: int,
    margin: int = 4,
    outer: int = 0,
) -> list[Cell]:
    """Masonry (kieu Pinterest): cac cot doc, anh xep vao cot thap nhat.

    Moi cot duoc ep ve dung chieu cao khung (crop nhe tung anh).
    """
    n = len(aspects)
    if n == 0:
        return []
    aspects = [max(0.05, min(20.0, a)) for a in aspects]
    cw = width - 2 * outer
    ch = height - 2 * outer
    avg_a = sum(aspects) / n

    k0 = math.sqrt(n * cw / (ch * avg_a))
    k_lo = max(1, int(math.floor(k0)) - 2)
    k_hi = min(n, max(1, int(math.ceil(k0)) + 2))

    best = None  # (score, k, cols)
    for k in range(k_lo, k_hi + 1):
        colw = (cw - (k - 1) * margin) / k
        if colw < 1:
            continue
        cols: list[list[int]] = [[] for _ in range(k)]
        heights = [0.0] * k
        for i, a in enumerate(aspects):
            j = heights.index(min(heights))
            cols[j].append(i)
            if cols[j][:-1]:
                heights[j] += margin
            heights[j] += colw / a
        if any(not c for c in cols):
            continue
        # do lech lon nhat giua chieu cao tu nhien cua cot va khung dich
        score = max(abs(math.log(h / ch)) for h in heights)
        if best is None or score < best[0]:
            best = (score, k, cols)
    if best is None:
        if margin > 0:
            return compute_masonry_layout(aspects, width, height, margin // 2, outer)
        raise ValueError("Khong the xep masonry: qua nhieu anh cho khung nay.")

    _, k, cols = best
    colw = (cw - (k - 1) * margin) / k

    # bien doc cua cac cot (dung chung -> thang hang)
    x_edges = []
    x = float(outer)
    for j in range(k):
        x0 = _round(x)
        x1 = width - outer if j == k - 1 else _round(x + colw)
        if x1 <= x0:
            x1 = x0 + 1
        x_edges.append((x0, x1))
        x += colw + margin

    cells: list[Cell] = []
    for j, col in enumerate(cols):
        nat = [colw / aspects[i] for i in col]
        avail = ch - (len(col) - 1) * margin
        f = avail / sum(nat)
        x0, x1 = x_edges[j]
        y = float(outer)
        for ci, i in enumerate(col):
            h = nat[ci] * f
            y0 = _round(y)
            y1 = height - outer if ci == len(col) - 1 else _round(y + h)
            if y1 <= y0:
                y1 = y0 + 1
            cells.append(Cell(i, x0, y0, x1, y1))
            y += h + margin
    return cells


def compute_mosaic_layout(
    aspects: list[float],
    width: int,
    height: int,
    margin: int = 4,
    outer: int = 0,
) -> list[Cell]:
    """Luoi diem nhan: da so o nho deu nhau, xen ke vai o lon 2x2.

    Cac o lon dat tai vi tri "neo" hang/cot chan nen khong bao gio cham
    nhau; moi o deu bam luoi -> khong chong cheo, phu kin khung.
    """
    n = len(aspects)
    if n == 0:
        return []
    if n < 6:  # qua it anh, diem nhan khong co y nghia
        return compute_grid_layout(n, width, height, margin, outer, cell_aspect=1.0)
    cw = width - 2 * outer
    ch = height - 2 * outer

    b0 = max(1, round(n / 7))  # so o lon mong muon (~1/7 so anh)
    best = None  # (score, C, R, b)
    for b in range(1, min(n // 4, b0 + 4) + 1):
        slots = n + 3 * b  # moi o lon chiem 4 slot thay vi 1
        c0 = math.sqrt(slots * cw / ch)
        for C in range(max(2, int(c0) - 2), int(c0) + 4):
            if slots % C:
                continue
            R = slots // C
            if R < 2 or b > (R // 2) * (C // 2):
                continue
            cell_w = (cw - (C - 1) * margin) / C
            cell_h = (ch - (R - 1) * margin) / R
            if cell_w < 1 or cell_h < 1:
                continue
            score = abs(math.log(cell_w / cell_h)) + 0.05 * abs(b - b0)
            if best is None or score < best[0]:
                best = (score, C, R, b)
    if best is None:
        return compute_grid_layout(n, width, height, margin, outer, cell_aspect=1.0)
    _, C, R, b = best

    # toa do mep cac cot/hang (lam tron don dieu, mep cuoi ep sat khung)
    cell_w = (cw - (C - 1) * margin) / C
    cell_h = (ch - (R - 1) * margin) / R
    col_x0, col_x1 = [], []
    x = float(outer)
    for ci in range(C):
        x0 = _round(x)
        x1 = width - outer if ci == C - 1 else _round(x + cell_w)
        col_x0.append(x0)
        col_x1.append(max(x1, x0 + 1))
        x += cell_w + margin
    row_y0, row_y1 = [], []
    y = float(outer)
    for ri in range(R):
        y0 = _round(y)
        y1 = height - outer if ri == R - 1 else _round(y + cell_h)
        row_y0.append(y0)
        row_y1.append(max(y1, y0 + 1))
        y += cell_h + margin

    # chon vi tri o lon tu cac "neo" chan (khong the trung nhau)
    anchors = [(r, c) for r in range(0, R - 1, 2) for c in range(0, C - 1, 2)]
    rng = random.Random(n * 31 + C * 7 + R)  # co dinh -> lap lai duoc
    big_at = set(rng.sample(anchors, b))

    cells: list[Cell] = []
    taken = [[False] * C for _ in range(R)]
    idx = 0
    for r in range(R):
        for c in range(C):
            if taken[r][c]:
                continue
            if (r, c) in big_at:
                for dr in (0, 1):
                    for dc in (0, 1):
                        taken[r + dr][c + dc] = True
                cells.append(Cell(idx, col_x0[c], row_y0[r],
                                  col_x1[c + 1], row_y1[r + 1]))
            else:
                taken[r][c] = True
                cells.append(Cell(idx, col_x0[c], row_y0[r],
                                  col_x1[c], row_y1[r]))
            idx += 1
    return cells


def compute_band_layout(
    n: int,
    width: int,
    height: int,
    margin: int = 4,
    outer: int = 0,
    cell_aspect: float = 0.62,
    snake: bool = True,
) -> list[Cell]:
    """Chia thanh cac dai ngang xep chong, o trong dai chia deu.

    Nen tang chung cho cac layout infographic (timeline, quy trinh, cuon
    phim, day treo, bac thang...). `cell_aspect` la ti le w/h muc tieu cua
    o; `snake=True` -> thu tu anh chay uon luon kieu ran bo (dai le di
    nguoc) de dong chay lien tuc. Cac o luon phu kin khung.
    """
    if n == 0:
        return []
    cw = width - 2 * outer
    ch = height - 2 * outer

    best = None  # (score, r)
    for r in range(1, n + 1):
        k = math.ceil(n / r)
        cell_w = (cw - (k - 1) * margin) / k
        cell_h = (ch - (r - 1) * margin) / r
        if cell_w < 1 or cell_h < 1:
            continue
        score = abs(math.log((cell_w / cell_h) / cell_aspect))
        if best is None or score < best[0]:
            best = (score, r)
    if best is None:
        if margin > 0:
            return compute_band_layout(n, width, height, margin // 2, outer,
                                       cell_aspect, snake)
        raise ValueError("Khong the xep dai bang: qua nhieu anh cho khung nay.")

    r = best[1]
    base, extra = divmod(n, r)
    row_sizes = [base + 1 if i < extra else base for i in range(r)]

    cells: list[Cell] = []
    row_h = (ch - (r - 1) * margin) / r
    y = float(outer)
    idx = 0
    for ri, k in enumerate(row_sizes):
        y0 = _round(y)
        y1 = height - outer if ri == r - 1 else _round(y + row_h)
        if y1 <= y0:
            y1 = y0 + 1
        cell_w = (cw - (k - 1) * margin) / k
        xs: list[tuple[int, int]] = []
        x = float(outer)
        for ci in range(k):
            x0 = _round(x)
            x1 = width - outer if ci == k - 1 else _round(x + cell_w)
            if x1 <= x0:
                x1 = x0 + 1
            xs.append((x0, x1))
            x += cell_w + margin
        rev = snake and ri % 2 == 1  # ran bo: dai le di nguoc
        order = range(k - 1, -1, -1) if rev else range(k)
        for ci in order:
            x0, x1 = xs[ci]
            cells.append(Cell(idx, x0, y0, x1, y1))
            idx += 1
        y += row_h + margin
    return cells


def _transpose_cells(cells: list[Cell]) -> list[Cell]:
    """Doi cho x/y — bien dai ngang thanh cot doc (giu nguyen index)."""
    return [Cell(c.index, c.y0, c.x0, c.y1, c.x1) for c in cells]


def compute_timeline_layout(
    n: int,
    width: int,
    height: int,
    margin: int = 4,
    outer: int = 0,
) -> list[Cell]:
    """Timeline ngang: o cao (~0.62) de the anh nam nua tren/duoi truc."""
    return compute_band_layout(n, width, height, margin, outer,
                               cell_aspect=0.62, snake=True)


def _fill_region(
    fill: str,
    aspects: list[float],
    width: int,
    height: int,
    margin: int,
) -> list[Cell]:
    """Xep mot vung con theo kieu chon (dung cho cac vung phu cua hero).

    Neu vung qua chat cho kieu do (vd masonry trong dai rat thap) thi tu
    lui ve justified — kieu an toan nhat.
    """
    if not aspects:
        return []
    try:
        if fill == "grid":
            srt = sorted(aspects)
            med = srt[len(aspects) // 2]
            return compute_grid_layout(len(aspects), width, height, margin, 0,
                                       cell_aspect=med)
        if fill == "masonry":
            return compute_masonry_layout(aspects, width, height, margin, 0)
    except ValueError:
        pass  # vung khong du cho cho kieu nay
    return compute_layout(aspects, width, height, margin, 0)


def _hero_band(
    aspects: list[float],
    width: int,
    height: int,
    margin: int,
    outer: int,
    hc: int,
    band_h: int,
    fill_style: str = "justified",
) -> list[Cell]:
    """Dai hero ngang tren cung (full be rong) + cac anh con lai o duoi."""
    cw = width - 2 * outer
    ch = height - 2 * outer
    top = compute_layout(aspects[:hc], cw, band_h, margin, 0)
    bot = _fill_region(fill_style, aspects[hc:], cw, ch - band_h - margin, margin)
    dy = outer + band_h + margin
    cells = [
        Cell(c.index, c.x0 + outer, c.y0 + outer, c.x1 + outer, c.y1 + outer)
        for c in top
    ]
    cells += [
        Cell(c.index + hc, c.x0 + outer, c.y0 + dy, c.x1 + outer, c.y1 + dy)
        for c in bot
    ]
    return cells


def compute_hero_layout(
    aspects: list[float],
    width: int,
    height: int,
    margin: int = 4,
    outer: int = 0,
    hero_count: int = 1,
    fill_style: str = "justified",
) -> list[Cell]:
    """Hien dai kieu tap chi: cac anh dau tien lam anh chu dao (hero).

    - 1 anh chu: vung hero giu gan dung ti le anh goc. Anh ngang tren khung
      vuong/doc -> tu chuyen sang dai banner full be rong; binh thuong dung
      bo cuc chu L (hero goc trai + cot phai + dai duoi); it anh -> chia doc.
    - Nhieu anh chu (2..6): cac hero xep thanh dai lon tren cung, phan con
      lai xep ben duoi.
    - fill_style: kieu xep cac vung anh phu (justified | grid | masonry).
    Luon chon phuong an it phai cat anh chu nhat.
    """
    n = len(aspects)
    if n == 0:
        return []
    hc = max(1, min(int(hero_count), 6))
    if n == 1 or hc >= n:
        return compute_layout(aspects, width, height, margin, outer)

    cw = width - 2 * outer
    ch = height - 2 * outer
    a0 = max(0.05, min(20.0, aspects[0]))
    min_rest = max(24, 2 * margin)

    # ---------- NHIEU anh chu: dai hero tren cung ----------
    if hc >= 2:
        sa = sum(max(0.05, min(20.0, a)) for a in aspects[:hc])
        nat = (cw - (hc - 1) * margin) / sa  # cao tu nhien neu xep 1 hang
        lo_f = min(0.72, max(0.30, 1.30 * hc / n))
        hi_f = max(0.58, lo_f)
        band_h = int(round(min(max(nat, ch * lo_f), ch * hi_f)))
        band_h = min(band_h, ch - margin - min_rest)
        if band_h >= 48:
            return _hero_band(aspects, width, height, margin, outer, hc,
                              band_h, fill_style)
        return compute_layout(aspects, width, height, margin, outer)

    # ---------- MOT anh chu ----------
    def _crop(region_aspect: float) -> float:
        """Muc do phai cat: 1.0 = khong cat, cang lon cang xau."""
        return max(region_aspect / a0, a0 / region_aspect)

    # Phuong an "banner": hero full be rong tren cung, cao theo ti le anh
    need = 0.45 if n == 2 else (2.0 if n >= 5 else 1.4) / n + 0.02
    band_lo = ch * max(0.32, need)
    band_hi = min(ch * 0.62, ch - margin - min_rest)
    band_h = 0
    if band_hi >= max(band_lo, 48):
        band_h = int(round(min(max(cw / a0, band_lo), band_hi)))
    crop_band = _crop(cw / band_h) if band_h else 1e9

    # muc tieu: hero chiem bao nhieu % dien tich (anh cang nhieu cang nho)
    if n <= 4:
        f_area = 0.45
    elif n <= 8:
        f_area = 0.42
    elif n <= 12:
        f_area = 0.35
    elif n <= 40:
        f_area = 0.28
    else:
        f_area = 0.20

    # --- Phuong an chu L (can >=5 anh va con du cho cho dai duoi) ---
    if n >= 5:
        # kich thuoc hero: uu tien dung ti le anh goc; neu bi kep boi gioi
        # han khung thi tinh lai chieu kia de GIU DIEN TICH
        area = f_area * cw * ch
        hw = math.sqrt(area * a0)
        hh = min(max(hw / a0, 0.40 * ch), 0.80 * ch)
        hw = min(max(area / hh, 0.35 * cw), 0.72 * cw)
        hh = min(max(area / hw, 0.40 * ch), 0.80 * ch)
        hw_i, hh_i = int(round(hw)), int(round(hh))
        rest_w = cw - hw_i - margin
        rest_h = ch - hh_i - margin
        if (hh_i <= ch - max(40, 3 * margin)
                and rest_w >= 32 and rest_h >= 24):
            crop_l = _crop(hw_i / hh_i)
            # neu chu L bat cat anh chu qua nhieu (hero anh ngang tren
            # khung vuong/doc) va banner dep hon -> dung banner
            if crop_l > 1.35 and band_h and crop_band < crop_l:
                return _hero_band(aspects, width, height, margin, outer,
                                  1, band_h, fill_style)

            area_r = rest_w * hh_i
            area_b = cw * rest_h
            k_r = round((n - 1) * area_r / (area_r + area_b))
            k_r = min(max(k_r, 1), n - 2)  # moi vung it nhat 1 anh

            sub_r = _fill_region(fill_style, aspects[1:1 + k_r],
                                 rest_w, hh_i, margin)
            sub_b = _fill_region(fill_style, aspects[1 + k_r:],
                                 cw, rest_h, margin)
            dx_r = outer + hw_i + margin
            dy_b = outer + hh_i + margin

            cells = [Cell(0, outer, outer, outer + hw_i, outer + hh_i)]
            cells += [
                Cell(c.index + 1, c.x0 + dx_r, c.y0 + outer,
                     c.x1 + dx_r, c.y1 + outer)
                for c in sub_r
            ]
            cells += [
                Cell(c.index + 1 + k_r, c.x0 + outer, c.y0 + dy_b,
                     c.x1 + outer, c.y1 + dy_b)
                for c in sub_b
            ]
            return cells

    # --- It anh (2..4) hoac chu L khong kha thi: chia doc HAY banner? ---
    lo = 0.50 * cw if n <= 4 else 0.34 * cw
    hw_v = int(round(min(max(a0 * ch, lo), 0.62 * cw)))
    crop_v = _crop(hw_v / ch)
    if band_h and crop_band < crop_v:  # hero anh ngang -> banner dep hon
        return _hero_band(aspects, width, height, margin, outer, 1,
                          band_h, fill_style)

    rest_w = cw - hw_v - margin
    if rest_w < 32:  # khung qua hep -> rot ve justified
        return compute_layout(aspects, width, height, margin, outer)

    hero = Cell(0, outer, outer, outer + hw_v, height - outer)
    sub = _fill_region(fill_style, aspects[1:], rest_w, ch, margin)
    dx = outer + hw_v + margin
    cells = [hero] + [
        Cell(c.index + 1, c.x0 + dx, c.y0 + outer, c.x1 + dx, c.y1 + outer)
        for c in sub
    ]
    return cells


LAYOUT_STYLES = {
    "justified": "Hàng cân bằng (tự nhiên, ít cắt)",
    "grid": "Lưới đều (gọn gàng, báo cáo)",
    "mosaic": "Lưới điểm nhấn (ô to xen kẽ)",
    "masonry": "Masonry (kiểu Pinterest)",
    "hero": "Ảnh chủ đạo (hiện đại)",
    "polaroid": "Polaroid (nghệ thuật, hiện đại)",
    "stack": "Xếp nghiêng tự do (bàn ảnh)",
    "timeline": "Timeline (dòng thời gian kỷ niệm)",
    "timeline-doc": "Timeline dọc (trục giữa, thẻ 2 bên)",
    "process": "Quy trình mũi tên (bước đánh số)",
    "path": "Hành trình bong bóng (chấm nối)",
    "steps": "Bậc thang tiến bước (infographic)",
    "filmstrip": "Cuộn phim (khung + lỗ răng phim)",
    "string": "Dây treo ảnh (kẹp gỗ vintage)",
    "hexagon": "Tổ ong lục giác (infographic)",
}

# Cac kieu dua tren dai bang: ti le o muc tieu + co chay ran bo hay khong
_BAND_STYLES = {
    "timeline": (0.62, True),
    "process": (1.45, True),
    "path": (1.00, True),
    "steps": (0.85, True),
    "filmstrip": (1.50, False),
    "string": (0.74, False),
}


def compute_style_layout(
    style: str,
    aspects: list[float],
    width: int,
    height: int,
    margin: int = 4,
    outer: int = 0,
    hero_count: int = 1,
    fill_style: str = "justified",
) -> list[Cell]:
    """Bo chia layout theo kieu. Moi kieu deu dam bao khong chong cheo."""
    if style == "justified":
        return compute_layout(aspects, width, height, margin, outer)
    if style == "grid":
        n = len(aspects)
        srt = sorted(aspects)
        med = srt[n // 2] if n else 4 / 3
        return compute_grid_layout(n, width, height, margin, outer, cell_aspect=med)
    if style == "mosaic":
        return compute_mosaic_layout(aspects, width, height, margin, outer)
    if style == "masonry":
        return compute_masonry_layout(aspects, width, height, margin, outer)
    if style == "hero":
        return compute_hero_layout(aspects, width, height, margin, outer,
                                   hero_count=hero_count, fill_style=fill_style)
    if style == "stack":
        n = len(aspects)
        srt = sorted(aspects)
        med = srt[n // 2] if n else 4 / 3
        return compute_grid_layout(n, width, height, margin, outer, cell_aspect=med)
    if style == "polaroid":
        # polaroid dat the anh trong cac o luoi; the anh vuong nen o ~vuong
        n = len(aspects)
        return compute_grid_layout(n, width, height, margin, outer, cell_aspect=0.95)
    if style in _BAND_STYLES:
        asp, snake = _BAND_STYLES[style]
        return compute_band_layout(len(aspects), width, height, margin, outer,
                                   cell_aspect=asp, snake=snake)
    if style == "timeline-doc":
        # tinh nhu timeline ngang tren khung xoay 90 do roi doi cho x/y
        return _transpose_cells(
            compute_band_layout(len(aspects), height, width, margin, outer,
                                cell_aspect=0.60, snake=True))
    if style == "hexagon":
        # luc giac dinh nhon hoi cao -> o ~0.9
        return compute_grid_layout(len(aspects), width, height, margin, outer,
                                   cell_aspect=0.9)
    raise ValueError(f"Kieu layout khong hop le: {style}")


def min_cell_size(cells: list[Cell]) -> int:
    """Canh nho nhat trong cac o — dung de canh bao khi anh qua nhieu."""
    if not cells:
        return 0
    return min(min(c.w, c.h) for c in cells)


def validate_no_overlap(cells: list[Cell]) -> bool:
    """Kiem tra (dung cho test): khong co 2 o nao giao nhau."""
    for i in range(len(cells)):
        a = cells[i]
        for j in range(i + 1, len(cells)):
            b = cells[j]
            if a.x0 < b.x1 and b.x0 < a.x1 and a.y0 < b.y1 and b.y0 < a.y1:
                return False
    return True
