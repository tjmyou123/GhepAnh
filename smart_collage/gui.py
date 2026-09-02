"""Giao dien do hoa cho Windows: dieu khien ben trai, xem truoc ben phai."""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from .core import (MAX_IMAGES, CollageError, make_collage, make_collage_image,
                   make_template_collage, make_template_collage_image)
from .layout import LAYOUT_STYLES
from .presets import DEFAULT_PRESET, PRESET_GROUPS, PRESETS
from .renderer import INFO_LAYOUTS, find_images
from .templates import TEMPLATES
from .themes import DEFAULT_THEME, THEMES

PREVIEW_W = 640   # kich thuoc toi thieu; se tu tang theo man hinh
PREVIEW_H = 480


class ThumbGallery(ttk.Frame):
    """Luoi thumbnail cuon doc, dung cho hop thoai chon anh / sap xep vi tri.

    mode="pick":    bam de chon/bo chon (toi da max_pick), huy hieu = thu tu chon.
    mode="reorder": bam de chon o, keo tha de doi vi tri, huy hieu = vi tri 1..n.
    Thumbnail duoc nap o luong nen roi hien dan (khong treo giao dien).
    """

    PAD = 8

    def __init__(self, parent, files: list[Path], mode: str = "pick",
                 thumb: int = 104, cols: int = 5, rows_visible: int = 4,
                 max_pick: int = 6, on_change=None, init_order=None):
        super().__init__(parent)
        self._files = files
        self.mode = mode
        self.thumb = thumb
        self.cols = cols
        self.max_pick = max_pick
        self.on_change = on_change
        self.items: list[int] = list(init_order) if init_order else list(range(len(files)))
        self.picked: list[int] = []      # mode pick: chi so goc theo thu tu chon
        self.selected: int | None = None  # mode reorder: vi tri hien thi dang chon

        self.tile_w = thumb + 12
        self.tile_h = thumb + 30
        self.cell_w = self.tile_w + 8
        self.cell_h = self.tile_h + 8
        width = self.PAD * 2 + self.cols * self.cell_w
        height = self.PAD * 2 + rows_visible * self.cell_h

        self.canvas = tk.Canvas(self, width=width, height=height,
                                bg="#F2F2F2", highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

        ph = Image.new("RGB", (thumb, thumb), "#DDDDDD")
        self._ph = ImageTk.PhotoImage(ph)
        self._photos: dict[int, ImageTk.PhotoImage] = {}
        self._tiles: list[dict] = []
        self._pos_of: dict[int, int] = {}
        self._drag_from: int | None = None
        self._dragging = False
        self._stop = False
        self._q: queue.Queue = queue.Queue()

        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        self.bind("<Destroy>", self._on_destroy)

        self._draw_all()
        threading.Thread(target=self._loader, daemon=True).start()
        self.after(80, self._poll)

    # ------------------------------------------------------ nap thumbnail --
    def _loader(self):
        for k, f in enumerate(self._files):
            if self._stop:
                return
            try:
                img = Image.open(f)
                img.draft("RGB", (self.thumb * 2, self.thumb * 2))
                img = ImageOps.exif_transpose(img)
                img.thumbnail((self.thumb, self.thumb))
                self._q.put((k, img.convert("RGB")))
            except OSError:
                continue

    def _poll(self):
        if self._stop or not self.winfo_exists():
            return
        try:
            while True:
                k, img = self._q.get_nowait()
                self._photos[k] = ImageTk.PhotoImage(img)
                pos = self._pos_of.get(k)
                if pos is not None and pos < len(self._tiles):
                    self.canvas.itemconfigure(self._tiles[pos]["img"],
                                              image=self._photos[k])
        except queue.Empty:
            pass
        except tk.TclError:
            return
        self.after(80, self._poll)

    def _on_destroy(self, _e=None):
        self._stop = True
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass

    # -------------------------------------------------------------- ve --
    def _draw_all(self):
        c = self.canvas
        c.delete("all")
        self._tiles = []
        self._pos_of = {}
        for pos, k in enumerate(self.items):
            col, row = pos % self.cols, pos // self.cols
            x = self.PAD + col * self.cell_w
            y = self.PAD + row * self.cell_h
            sel = (self.mode == "reorder" and pos == self.selected) or \
                  (self.mode == "pick" and k in self.picked)
            c.create_rectangle(
                x, y, x + self.tile_w, y + self.tile_h,
                outline="#2563EB" if sel else "#C8C8C8",
                width=3 if sel else 1, fill="#FFFFFF")
            img_id = c.create_image(
                x + self.tile_w // 2, y + 5 + self.thumb // 2,
                image=self._photos.get(k, self._ph))
            name = self._files[k].name
            if len(name) > 17:
                name = name[:14] + "…"
            c.create_text(x + self.tile_w // 2, y + self.tile_h - 11,
                          text=name, font=("", 8), fill="#444444")
            if self.mode == "reorder":
                badge = str(pos + 1)
            else:
                badge = str(self.picked.index(k) + 1) if k in self.picked else ""
            if badge:
                r = 11 + 3 * (len(badge) - 1)
                c.create_oval(x + 4, y + 4, x + 4 + 2 * r, y + 26,
                              fill="#2563EB", outline="white")
                c.create_text(x + 4 + r, y + 15, text=badge,
                              fill="white", font=("", 9, "bold"))
            self._tiles.append({"img": img_id})
            self._pos_of[k] = pos
        rows = (len(self.items) + self.cols - 1) // self.cols
        c.configure(scrollregion=(
            0, 0, self.PAD * 2 + self.cols * self.cell_w,
            self.PAD * 2 + rows * self.cell_h))

    def _changed(self):
        self._draw_all()
        if self.on_change:
            self.on_change()

    # -------------------------------------------------------- su kien --
    def _hit(self, ex: int, ey: int) -> int | None:
        x = self.canvas.canvasx(ex)
        y = self.canvas.canvasy(ey)
        col = int((x - self.PAD) // self.cell_w)
        row = int((y - self.PAD) // self.cell_h)
        if col < 0 or col >= self.cols or row < 0:
            return None
        pos = row * self.cols + col
        return pos if 0 <= pos < len(self.items) else None

    def _on_wheel(self, e):
        try:
            self.canvas.yview_scroll(-e.delta // 120, "units")
        except tk.TclError:
            pass

    def _on_press(self, e):
        pos = self._hit(e.x, e.y)
        self._drag_from = pos
        self._dragging = False
        if pos is None:
            return
        if self.mode == "pick":
            k = self.items[pos]
            if k in self.picked:
                self.picked.remove(k)
            elif len(self.picked) < self.max_pick:
                self.picked.append(k)
            self._changed()
        else:
            self.selected = pos
            self._changed()

    def _on_motion(self, e):
        if self.mode != "reorder" or self._drag_from is None:
            return
        self._dragging = True
        x = self.canvas.canvasx(e.x)
        y = self.canvas.canvasy(e.y)
        self.canvas.delete("ghost")
        self.canvas.create_rectangle(
            x - self.tile_w // 2, y - self.tile_h // 2,
            x + self.tile_w // 2, y + self.tile_h // 2,
            outline="#2563EB", width=2, dash=(4, 3), tags="ghost")
        tgt = self._hit(e.x, e.y)
        if tgt is not None and tgt != self._drag_from:
            col, row = tgt % self.cols, tgt // self.cols
            gx = self.PAD + col * self.cell_w
            gy = self.PAD + row * self.cell_h
            self.canvas.create_rectangle(
                gx - 2, gy - 2, gx + self.tile_w + 2, gy + self.tile_h + 2,
                outline="#F59E0B", width=3, tags="ghost")
        # keo sat mep tren/duoi -> tu cuon
        h = self.canvas.winfo_height()
        if e.y > h - 24:
            self.canvas.yview_scroll(1, "units")
        elif e.y < 24:
            self.canvas.yview_scroll(-1, "units")

    def _on_release(self, e):
        self.canvas.delete("ghost")
        src = self._drag_from
        self._drag_from = None
        if self.mode != "reorder" or not self._dragging or src is None:
            return
        self._dragging = False
        dst = self._hit(e.x, e.y)
        if dst is None or dst == src:
            return
        k = self.items.pop(src)
        self.items.insert(dst, k)
        self.selected = dst
        self._changed()

    # ------------------------------------------------- thao tac ngoai --
    def move_selected(self, kind: str):
        """Di chuyen o dang chon: top | up | down | end."""
        if self.mode != "reorder" or self.selected is None:
            return
        src = self.selected
        dst = {"top": 0, "up": src - 1, "down": src + 1,
               "end": len(self.items) - 1}[kind]
        dst = max(0, min(len(self.items) - 1, dst))
        if dst == src:
            return
        k = self.items.pop(src)
        self.items.insert(dst, k)
        self.selected = dst
        self._changed()
        # giu o dang chon trong tam nhin
        rows = max(1, (len(self.items) + self.cols - 1) // self.cols)
        frac = (dst // self.cols) / rows
        self.canvas.yview_moveto(max(0.0, frac - 0.25))

    def order_names(self) -> list[str]:
        return [self._files[k].name for k in self.items]

    def picked_names(self) -> list[str]:
        return [self._files[k].name for k in self.picked]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ghép ảnh thông minh — Datpro09")
        self.resizable(True, True)
        self.minsize(980, 620)
        self.bg_color = "#FFFFFF"
        self._preview_photo = None  # giu tham chieu tranh bi thu hoi
        self._busy = False
        self._pv_img: Image.Image | None = None  # ban render preview gan nhat
        self._pv_zoom = 1.0                      # he so zoom (1 = vua khung)
        self._rs_job = None                      # debounce render lai khi keo cua so
        self.img_adjust: dict[str, dict] = {}    # chinh rieng tung anh (rot/zoom/dx/dy)
        self.extra_files: list[str] = []         # anh them tu ngoai thu muc
        self.excluded: list[str] = []            # anh bot khoi ban ghep
        self._adj_job = None                     # debounce khi lan-zoom tung anh
        self._pv_adj = None                      # keo doi vung cat dang dien ra
        self._pv_rmoved = False                  # phan biet keo xem / click phai
        self._pv_rpos = (0, 0)
        self._adj_cache: dict[str, tuple[int, Image.Image]] = {}  # anh goc cho live-edit
        self._adj_photo = None                   # PhotoImage cua o dang chinh
        self.tpl_files: list[str] = []           # anh cho tab Ghep nhanh 2-9
        self.tpl_var = tk.StringVar(value="")    # id bo cuc mau dang chon
        # kich thuoc khoi diem cua khung xem truoc: tu tinh theo man hinh
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.pv_w = max(PREVIEW_W, min(1100, sw - 500))
        self.pv_h = max(PREVIEW_H, min(800, sh - 300))
        self._build()

    # ------------------------------------------------------------- UI ----
    def _build(self):
        pad = {"padx": 8, "pady": 4}
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        root = ttk.Frame(self)
        root.grid(sticky="nsew", padx=12, pady=12)
        root.rowconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)

        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="nw")
        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew", padx=(14, 0))

        # --- 2 che do: ghep ca thu muc / ghep nhanh 2-9 anh theo mau ---
        nb = ttk.Notebook(left)
        nb.pack(fill="x", **pad)
        tab_auto = ttk.Frame(nb)
        tab_tpl = ttk.Frame(nb)
        nb.add(tab_auto, text="Ghép thư mục (tự xếp)")
        nb.add(tab_tpl, text="Ghép nhanh 2–9 ảnh")
        self.nb, self.tab_tpl = nb, tab_tpl
        nb.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_change())

        # --- Thu muc anh ---
        lf = ttk.LabelFrame(tab_auto, text="Thư mục ảnh")
        lf.pack(fill="x", **pad)
        self.folder_var = tk.StringVar()
        ttk.Entry(lf, textvariable=self.folder_var, width=40).grid(
            row=0, column=0, sticky="we", padx=6, pady=4)
        ttk.Button(lf, text="Chọn...", command=self.pick_folder).grid(
            row=0, column=1, padx=6)
        self.count_var = tk.StringVar(value="Chưa chọn thư mục")
        ttk.Label(lf, textvariable=self.count_var, foreground="#555").grid(
            row=1, column=0, sticky="w", padx=6, pady=(0, 4))
        fbtns = ttk.Frame(lf)
        fbtns.grid(row=1, column=1, padx=6, pady=(0, 4))
        ttk.Button(fbtns, text="Thêm ảnh…", command=self.add_images).pack(side="left")
        ttk.Button(fbtns, text="Bớt ảnh…",
                   command=self.remove_images_dialog).pack(side="left", padx=(4, 0))

        # --- Preset: tich chon theo nhom ---
        pf = ttk.LabelFrame(left, text="Kiểu đầu ra")
        pf.pack(fill="x", **pad)
        pf.columnconfigure(0, weight=1)
        pf.columnconfigure(1, weight=1)
        self.preset_var = tk.StringVar(value=DEFAULT_PRESET)
        short = {  # nhan gon (nhom da ghi nen tang)
            "fb-cover": "Ảnh bìa",
            "fb-post": "Vuông 1:1",
            "fb-post-doc": "Dọc 4:5",
            "fb-post-ngang": "Ngang 1.91:1",
            "fb-story": "Story / Reels 9:16",
            "ig-post": "Vuông 1:1",
            "ig-doc": "Dọc 4:5 (cả Threads)",
            "ig-story": "Story·Reels 9:16",
            "x-post": "X (Twitter) 16:9",
            "linkedin": "LinkedIn 1.91:1",
            "pinterest": "Pinterest 2:3",
            "youtube": "YouTube 16:9",
            "ppt": "16:9 Full HD",
            "ppt-4k": "16:9 4K",
            "ppt-43": "4:3",
            "ppt-zoom": "16:9 nét 3×",
            "ppt-zoom-4x": "16:9 8K (4×)",
            "ppt-zoom-43": "4:3 nét 3×",
        }
        r = 0
        for group, keys in PRESET_GROUPS.items():
            ttk.Label(pf, text=group, font=("", 9, "bold")).grid(
                row=r, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 0))
            r += 1
            for i, key in enumerate(keys):
                _, pw_, ph_ = PRESETS[key]
                ttk.Radiobutton(
                    pf, text=f"{short.get(key, key)} ({pw_}×{ph_})", value=key,
                    variable=self.preset_var, command=self.schedule_preview,
                ).grid(row=r + i // 2, column=i % 2, sticky="w", padx=(18, 4))
            r += (len(keys) + 1) // 2
        ttk.Frame(pf, height=4).grid(row=r, column=0)

        # --- Layout + Theme ---
        of = ttk.LabelFrame(tab_auto, text="Bố cục & Theme")
        of.pack(fill="x", **pad)

        ttk.Label(of, text="Kiểu xếp:").grid(row=0, column=0, sticky="w", padx=6, pady=3)
        self.layout_labels = {v: k for k, v in LAYOUT_STYLES.items()}
        self.layout_var = tk.StringVar(value=LAYOUT_STYLES["justified"])
        cb = ttk.Combobox(of, textvariable=self.layout_var, state="readonly",
                          width=32, values=list(LAYOUT_STYLES.values()))
        self._fit_combo_popup(cb)
        cb.grid(row=0, column=1, sticky="w", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._on_layout_change())

        ttk.Label(of, text="Ảnh chủ đạo:").grid(row=1, column=0, sticky="w", padx=6, pady=3)
        hf = ttk.Frame(of)
        hf.grid(row=1, column=1, sticky="w", padx=6)
        self.heroes_var = tk.IntVar(value=1)
        self.hero_files: list[str] = []
        self.hero_spin = ttk.Spinbox(hf, from_=1, to=6, textvariable=self.heroes_var,
                                     width=4, command=self.schedule_preview)
        self.hero_spin.pack(side="left")
        self.hero_btn = ttk.Button(hf, text="Chọn ảnh chủ…", command=self.choose_heroes)
        self.hero_btn.pack(side="left", padx=(6, 0))
        self.hero_sel_var = tk.StringVar(value="Tự động: ảnh đầu tiên")
        ttk.Label(hf, textvariable=self.hero_sel_var, foreground="#666666").pack(
            side="left", padx=(6, 0))

        ttk.Label(of, text="Xếp ảnh phụ:").grid(row=2, column=0, sticky="w", padx=6, pady=3)
        self.fill_labels = {"Hàng cân bằng": "justified", "Lưới đều": "grid",
                            "Masonry (Pinterest)": "masonry"}
        self.fill_var = tk.StringVar(value="Hàng cân bằng")
        self.fill_cb = ttk.Combobox(of, textvariable=self.fill_var, state="readonly",
                                    width=32, values=list(self.fill_labels))
        self._fit_combo_popup(self.fill_cb)
        self.fill_cb.grid(row=2, column=1, sticky="w", padx=6)
        self.fill_cb.bind("<<ComboboxSelected>>", lambda e: self.schedule_preview())

        ttk.Label(of, text="Theme:").grid(row=3, column=0, sticky="w", padx=6, pady=3)
        self.theme_labels = {v["label"]: k for k, v in THEMES.items()}
        self.theme_var = tk.StringVar(value=THEMES[DEFAULT_THEME]["label"])
        tb = ttk.Combobox(of, textvariable=self.theme_var, state="readonly",
                          width=32, values=[v["label"] for v in THEMES.values()])
        self._fit_combo_popup(tb)
        tb.grid(row=3, column=1, sticky="w", padx=6)
        tb.bind("<<ComboboxSelected>>", lambda e: self._on_theme_change())

        ttk.Label(of, text="Thứ tự ảnh:").grid(row=4, column=0, sticky="w", padx=6, pady=3)
        order_f = ttk.Frame(of)
        order_f.grid(row=4, column=1, sticky="w")
        self.order_var = tk.StringVar(value="name")
        self.custom_order: list[str] = []
        for val, label in [("name", "Theo tên"), ("aspect", "Ít cắt"),
                           ("random", "Ngẫu nhiên"), ("custom", "Tự chọn")]:
            ttk.Radiobutton(order_f, text=label, value=val, variable=self.order_var,
                            command=self._on_order_change).pack(side="left", padx=(0, 6))
        ttk.Button(order_f, text="Sắp xếp…", width=9,
                   command=self.arrange_order).pack(side="left")

        ttk.Label(of, text="Khoảng cách:").grid(row=5, column=0, sticky="w", padx=6, pady=3)
        mf = ttk.Frame(of)
        mf.grid(row=5, column=1, sticky="w")
        self.margin_var = tk.IntVar(value=THEMES[DEFAULT_THEME]["margin"])
        sp = ttk.Spinbox(mf, from_=0, to=40, textvariable=self.margin_var,
                         width=5, command=self.schedule_preview)
        sp.pack(side="left", padx=(6, 0))
        ttk.Label(mf, text="px    Màu nền:").pack(side="left")
        self.bg_btn = tk.Button(mf, text="     ", bg=self.bg_color,
                                command=self.pick_color, relief="ridge")
        self.bg_btn.pack(side="left", padx=6)

        # --- Chi tiet infographic (timeline, process, path...) ---
        ttk.Label(of, text="Chi tiết:").grid(row=6, column=0, sticky="w", padx=6, pady=3)
        inf = ttk.Frame(of)
        inf.grid(row=6, column=1, sticky="w", padx=6)
        self.num_on = tk.BooleanVar(value=True)
        self.cap_on = tk.BooleanVar(value=True)
        self.marker_on = tk.BooleanVar(value=True)
        self.info_checks = []
        for var, label in [(self.num_on, "Số thứ tự"),
                           (self.cap_on, "Tên ảnh"),
                           (self.marker_on, "Điểm đầu/cuối")]:
            cbx = ttk.Checkbutton(inf, text=label, variable=var,
                                  command=self.schedule_preview)
            cbx.pack(side="left", padx=(0, 8))
            self.info_checks.append(cbx)

        ttk.Label(of, text="Màu chi tiết:").grid(row=7, column=0, sticky="w", padx=6, pady=3)
        icf = ttk.Frame(of)
        icf.grid(row=7, column=1, sticky="w", padx=6)
        self.num_color: str | None = None
        self.line_color: str | None = None
        ttk.Label(icf, text="Số:").pack(side="left")
        self.num_color_btn = tk.Button(
            icf, text="Tự động", width=7, relief="ridge",
            command=lambda: self._pick_info_color("num"))
        self.num_color_btn.pack(side="left", padx=(2, 10))
        ttk.Label(icf, text="Trục:").pack(side="left")
        self.line_color_btn = tk.Button(
            icf, text="Tự động", width=7, relief="ridge",
            command=lambda: self._pick_info_color("line"))
        self.line_color_btn.pack(side="left", padx=(2, 10))
        self._auto_btn_bg = self.num_color_btn.cget("bg")
        self.info_reset_btn = ttk.Button(icf, text="Mặc định", width=9,
                                         command=self._reset_info_colors)
        self.info_reset_btn.pack(side="left")

        # --- Tab ghep nhanh 2-9 anh theo bo cuc mau ---
        self._build_tpl_tab(tab_tpl)

        # --- Nut hanh dong ---
        bf = ttk.Frame(left)
        bf.pack(fill="x", **pad)
        self.go_btn = ttk.Button(bf, text="GHÉP && LƯU FILE", command=self.start)
        self.go_btn.pack(fill="x")

        self.prog = ttk.Progressbar(left, maximum=100)
        self.prog.pack(fill="x", **pad)
        self.status_var = tk.StringVar(value="Sẵn sàng")
        ttk.Label(left, textvariable=self.status_var, wraplength=340).pack(
            anchor="w", padx=8)

        # --- Trinh chieu anh tu dong (Ken Burns) ---
        kf = ttk.LabelFrame(left, text="Trình chiếu tự động — zoom in/out (từ thư mục ảnh ở tab Ghép thư mục)")
        kf.pack(fill="x", **pad)
        krow = ttk.Frame(kf)
        krow.pack(fill="x", padx=6, pady=(4, 6))
        ttk.Label(krow, text="Giây/ảnh:").pack(side="left")
        self.show_dur_var = tk.DoubleVar(value=5.0)
        ttk.Spinbox(krow, from_=2, to=20, increment=0.5, width=5,
                    textvariable=self.show_dur_var).pack(side="left", padx=(4, 10))
        ttk.Button(krow, text="HTML tự chạy",
                   command=lambda: self.show_export("html")).pack(
            side="left", expand=True, fill="x")
        ttk.Button(krow, text="PowerPoint",
                   command=lambda: self.show_export("pptx")).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        ttk.Label(left, text="Ghép ảnh thông minh — © 2026 Datpro09",
                  foreground="#999", font=("", 8)).pack(anchor="e", padx=10)

        # --- Khung xem truoc (canvas keo tha + zoom + cuon + chinh anh) ---
        prf = ttk.LabelFrame(
            right, text="Xem trước (tự cập nhật) — kéo để đổi chỗ hoặc chỉnh ảnh trong ô")
        prf.pack(fill="both", expand=True)
        bar = ttk.Frame(prf)
        bar.pack(fill="x", padx=6, pady=(4, 0))
        ttk.Button(bar, text="−", width=3,
                   command=lambda: self._pv_zoom_step(1 / 1.25)).pack(side="left")
        ttk.Button(bar, text="+", width=3,
                   command=lambda: self._pv_zoom_step(1.25)).pack(side="left", padx=(4, 0))
        ttk.Button(bar, text="Vừa khung",
                   command=self._pv_zoom_fit).pack(side="left", padx=(4, 0))
        self._pv_zoom_lbl = ttk.Label(bar, text="100%", width=6, anchor="center")
        self._pv_zoom_lbl.pack(side="left", padx=(4, 0))
        self.pv_mode = tk.StringVar(value="swap")
        ttk.Radiobutton(bar, text="Đổi chỗ", value="swap",
                        variable=self.pv_mode).pack(side="left", padx=(14, 0))
        ttk.Radiobutton(bar, text="Chỉnh ảnh trong ô", value="adjust",
                        variable=self.pv_mode).pack(side="left", padx=(4, 0))
        ttk.Label(bar, text="Chuột phải lên ảnh: xoay / bớt ảnh · Ctrl+lăn: thu phóng",
                  foreground="#888", font=("", 8)).pack(side="right")
        wrap = ttk.Frame(prf)
        wrap.pack(fill="both", expand=True, padx=6, pady=6)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        self.preview_cv = tk.Canvas(wrap, width=self.pv_w, height=self.pv_h,
                                    bg="#2B2B2B", highlightthickness=0,
                                    xscrollincrement=20, yscrollincrement=20)
        self.preview_cv.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.preview_cv.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(wrap, orient="horizontal", command=self.preview_cv.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.preview_cv.configure(xscrollcommand=hsb.set, yscrollcommand=vsb.set)
        self._pv_hint = self.preview_cv.create_text(
            self.pv_w // 2, self.pv_h // 2,
            text="Chọn thư mục ảnh — bản xem trước sẽ tự hiện và tự làm mới",
            fill="#AAAAAA", font=("", 11))
        self._pv_meta: dict | None = None  # files + cells cua ban preview
        self._pv_k = 1.0                   # ti le render -> hien thi
        self._pv_ox = 0                    # do doi de can giua trong canvas
        self._pv_oy = 0
        self._pv_sel: int | None = None    # o dang keo
        self._pv_dragging = False
        self.preview_cv.bind("<Configure>", self._pv_resize)
        self.preview_cv.bind("<Motion>", self._pv_motion)
        self.preview_cv.bind("<Leave>", lambda e: self._pv_leave())
        self.preview_cv.bind("<Enter>", lambda e: self.bind_all(
            "<MouseWheel>", self._pv_wheel))
        self.preview_cv.bind("<Button-1>", self._pv_press)
        self.preview_cv.bind("<B1-Motion>", self._pv_drag)
        self.preview_cv.bind("<ButtonRelease-1>", self._pv_release)
        self.preview_cv.bind("<Button-3>", self._pv_rpress)
        self.preview_cv.bind("<B3-Motion>", self._pv_rdrag)
        self.preview_cv.bind("<ButtonRelease-3>", self._pv_rrelease)

        self._on_layout_change()  # trang thai ban dau cua o "Anh chu dao"

    # ------------------------------------------------------- helpers ----
    def _layout_key(self) -> str:
        return self.layout_labels[self.layout_var.get()]

    def _theme_key(self) -> str:
        return self.theme_labels[self.theme_var.get()]

    def _preset_key(self) -> str:
        return self.preset_var.get()

    @staticmethod
    def _fit_combo_popup(cb: ttk.Combobox):
        """Mo rong danh sach xo xuong cua combobox de khong bi cut chu."""
        try:
            pd = cb.tk.call("ttk::combobox::PopdownWindow", cb)
            w = max((len(str(v)) for v in cb.cget("values")), default=10)
            cb.tk.call(f"{pd}.f.l", "configure", "-width", w + 2)
        except tk.TclError:
            pass

    def _on_layout_change(self):
        lk = self._layout_key()
        # hero-center/golden cung dung "anh chu" (anh 1 = o noi bat)
        is_heroish = lk in ("hero", "hero-center", "golden")
        state = ["!disabled"] if is_heroish else ["disabled"]
        # so luong anh chu chi ap dung cho dai hero co dien
        self.hero_spin.state(["!disabled"] if lk == "hero" else ["disabled"])
        self.hero_btn.state(state)
        self.fill_cb.state(state)
        # tuy chon chi tiet chi co y nghia voi layout infographic
        is_info = self._layout_key() in INFO_LAYOUTS
        info_state = ["!disabled"] if is_info else ["disabled"]
        for w in self.info_checks:
            w.state(info_state)
        self.info_reset_btn.state(info_state)
        btn_state = "normal" if is_info else "disabled"
        self.num_color_btn.configure(state=btn_state)
        self.line_color_btn.configure(state=btn_state)
        self.schedule_preview()

    def _update_hero_label(self):
        if self.hero_files:
            names = ", ".join(Path(f).stem for f in self.hero_files[:2])
            extra = f" +{len(self.hero_files) - 2}" if len(self.hero_files) > 2 else ""
            self.hero_sel_var.set(f"Đã chọn: {names}{extra}")
        else:
            self.hero_sel_var.set("Tự động: ảnh đầu tiên")

    def _on_theme_change(self):
        # cap nhat khoang cach goi y theo theme
        self.margin_var.set(THEMES[self._theme_key()]["margin"])
        self.schedule_preview()

    def _on_order_change(self):
        # chon "Tu chon" khi chua sap xep -> mo ngay hop thoai keo tha
        if self.order_var.get() == "custom" and not self.custom_order:
            self.arrange_order()
        else:
            self.schedule_preview()

    def schedule_preview(self):
        """Tu dong lam moi xem truoc (neu du du lieu va khong ban)."""
        if self._busy:
            return
        if self._mode() == "tpl":
            if len(self.tpl_files) >= 2:
                self.after(150, self.do_preview)
        elif self.folder_var.get().strip():
            self.after(150, self.do_preview)

    # ----------------------------------- tab ghep nhanh 2-9 anh ----
    def _mode(self) -> str:
        """"tpl" khi dang o tab Ghep nhanh, nguoc lai "auto"."""
        if not hasattr(self, "nb"):
            return "auto"
        return "tpl" if self.nb.select() == str(self.tab_tpl) else "auto"

    def _on_tab_change(self):
        if self._mode() == "tpl":
            if len(self.tpl_files) >= 2:
                self.do_preview()
            else:
                self._tpl_hint()
        elif self.folder_var.get().strip():
            self.do_preview()

    def _build_tpl_tab(self, parent):
        pf = ttk.LabelFrame(parent, text="Ảnh đã chọn")
        pf.pack(fill="x", padx=8, pady=4)
        row = ttk.Frame(pf)
        row.pack(fill="x", padx=6, pady=4)
        ttk.Button(row, text="Chọn 2–9 ảnh…", command=self.tpl_pick).pack(side="left")
        ttk.Button(row, text="Thêm", command=self.tpl_add).pack(
            side="left", padx=(6, 0))
        ttk.Button(row, text="Xóa hết", command=self.tpl_clear).pack(
            side="left", padx=(6, 0))
        self.tpl_count_var = tk.StringVar(value="Chưa chọn ảnh (cần 2–9 ảnh)")
        ttk.Label(pf, textvariable=self.tpl_count_var, foreground="#555").pack(
            anchor="w", padx=6, pady=(0, 4))

        tf = ttk.LabelFrame(parent,
                            text="Bố cục mẫu — bấm để chọn (ô đậm là ảnh số 1)")
        tf.pack(fill="x", padx=8, pady=4)
        self.tpl_cv = tk.Canvas(tf, height=200, bg="#FAFAFA",
                                highlightthickness=0)
        self.tpl_cv.pack(fill="x", padx=6, pady=6)

        opt = ttk.Frame(parent)
        opt.pack(fill="x", padx=8, pady=(0, 2))
        ttk.Label(opt, text="Khoảng cách:").pack(side="left")
        ttk.Spinbox(opt, from_=0, to=40, textvariable=self.margin_var,
                    width=5, command=self.schedule_preview).pack(
            side="left", padx=(4, 2))
        ttk.Label(opt, text="px").pack(side="left")
        opt2 = ttk.Frame(parent)
        opt2.pack(fill="x", padx=8, pady=(2, 2))
        ttk.Label(opt2, text="Theme:").pack(side="left")
        tb2 = ttk.Combobox(opt2, textvariable=self.theme_var, state="readonly",
                           values=[v["label"] for v in THEMES.values()])
        tb2.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self._fit_combo_popup(tb2)
        tb2.bind("<<ComboboxSelected>>", lambda e: self._on_theme_change())
        ttk.Label(parent, text=("Xem trước bên phải: kéo ảnh để đổi chỗ, chọn "
                                "“Chỉnh ảnh trong ô” để dời/phóng vùng cắt, "
                                "chuột phải để xoay/bớt ảnh."),
                  foreground="#888", wraplength=330, justify="left").pack(
            anchor="w", padx=10, pady=(0, 4))
        self._tpl_refresh()

    def _tpl_refresh(self):
        """Ve luoi cac bo cuc mau cho so anh hien tai."""
        cv = self.tpl_cv
        cv.delete("all")
        n = len(self.tpl_files)
        tpls = TEMPLATES.get(n, [])
        if not tpls:
            cv.configure(height=90)
            cv.create_text(170, 45, text="Chọn 2–9 ảnh để hiện các bố cục mẫu",
                           fill="#999", font=("", 10))
            return
        ids = [t["id"] for t in tpls]
        if self.tpl_var.get() not in ids:
            self.tpl_var.set(ids[0])
        TW, TH, GAP, PER = 72, 58, 9, 4
        for k, t in enumerate(tpls):
            gx = GAP + (k % PER) * (TW + GAP)
            gy = GAP + (k // PER) * (TH + GAP + 14)
            sel = t["id"] == self.tpl_var.get()
            tag = f"tpl_{t['id']}"
            cv.create_rectangle(gx - 2, gy - 2, gx + TW + 2, gy + TH + 2,
                                outline="#3B82F6" if sel else "#CCCCCC",
                                width=2 if sel else 1,
                                fill="#EFF6FF" if sel else "#FFFFFF", tags=tag)
            for j, (x, y, w, h) in enumerate(t["cells"]):
                cv.create_rectangle(
                    gx + x * TW + 1.5, gy + y * TH + 1.5,
                    gx + (x + w) * TW - 1.5, gy + (y + h) * TH - 1.5,
                    fill="#93C5FD" if j == 0 else "#D7DDE6",
                    outline="", tags=tag)
            cv.create_text(gx + TW / 2, gy + TH + 8, text=t["name"],
                           fill="#2563EB" if sel else "#777",
                           font=("", 8), tags=tag)
            cv.tag_bind(tag, "<Button-1>",
                        lambda e, tid=t["id"]: self._tpl_select(tid))
        rows = (len(tpls) + PER - 1) // PER
        cv.configure(height=GAP + rows * (TH + GAP + 14))

    def _tpl_select(self, tid: str):
        self.tpl_var.set(tid)
        self._tpl_refresh()
        self.schedule_preview()

    _IMG_FILETYPES = [
        ("Ảnh", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif"),
        ("Tất cả", "*.*")]

    def tpl_pick(self):
        paths = filedialog.askopenfilenames(
            title="Chọn 2–9 ảnh để ghép nhanh", filetypes=self._IMG_FILETYPES)
        if paths:
            self._tpl_set(list(paths))

    def tpl_add(self):
        paths = filedialog.askopenfilenames(
            title="Thêm ảnh vào bản ghép nhanh", filetypes=self._IMG_FILETYPES)
        if paths:
            self._tpl_set(self.tpl_files + list(paths))

    def tpl_clear(self):
        self.tpl_files = []
        self._tpl_update_count()
        self._tpl_refresh()
        self._tpl_hint()

    def _tpl_set(self, paths: list[str]):
        out, seen = [], set()
        for p in paths:
            k = str(Path(p)).lower()
            if k not in seen:
                seen.add(k)
                out.append(p)
        if len(out) > 9:
            messagebox.showinfo("Tối đa 9 ảnh",
                                f"Đã chọn {len(out)} ảnh, chỉ dùng 9 ảnh đầu.")
            out = out[:9]
        self.tpl_files = out
        self._tpl_update_count()
        self._tpl_refresh()
        if len(out) >= 2:
            self.do_preview()
        else:
            self._tpl_hint()

    def _tpl_update_count(self):
        n = len(self.tpl_files)
        self.tpl_count_var.set("Chưa chọn ảnh (cần 2–9 ảnh)" if n == 0
                               else f"Đã chọn {n}/9 ảnh — ảnh 1 vào ô đậm")

    def _tpl_hint(self):
        """Xoa preview va hien huong dan khi chua du anh."""
        cv = self.preview_cv
        self._pv_img = None
        self._pv_meta = None
        cv.delete("all")
        cv.create_text(max(60, cv.winfo_width()) // 2,
                       max(60, cv.winfo_height()) // 2,
                       text="Chọn 2–9 ảnh — bản xem trước sẽ tự hiện",
                       fill="#AAAAAA", font=("", 11))

    def _tpl_args(self) -> dict:
        return dict(
            files=list(self.tpl_files),
            template=self.tpl_var.get(),
            preset=self._preset_key(),
            theme=self._theme_key(),
            margin=self.margin_var.get(),
            bg=self.bg_color,
            adjust={k: dict(v) for k, v in self.img_adjust.items()} or None,
        )

    def _tpl_preview_work(self, args: dict):
        try:
            meta: dict = {}
            pmax = min(3600, round(max(self.pv_w, self.pv_h)
                                   * max(1.0, self._pv_zoom) * 1.25))
            img, warnings = make_template_collage_image(
                preview_max=pmax, supersample=1, meta_out=meta, **args)
            self.after(0, self._preview_done, img, warnings, meta)
        except Exception as e:  # noqa: BLE001
            self.after(0, self._fail, str(e))

    def _tpl_work(self, args: dict):
        def progress(done: int, total: int):
            self.after(0, self._update_progress, done, total)

        try:
            out_path, warnings = make_template_collage(progress=progress, **args)
            self.after(0, self._done, out_path, warnings)
        except Exception as e:  # noqa: BLE001
            self.after(0, self._fail, str(e))

    def pick_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa ảnh")
        if folder:
            self.folder_var.set(folder)
            self.hero_files = []
            self._update_hero_label()
            self.custom_order = []
            self.img_adjust = {}
            self._adj_cache = {}
            self.extra_files = []
            self.excluded = []
            self._pv_zoom = 1.0
            if self.order_var.get() == "custom":
                self.order_var.set("name")
            if not self._update_count():
                return
            self.do_preview()

    def _update_count(self) -> bool:
        folder = self.folder_var.get().strip()
        if not folder:
            self.count_var.set("Chưa chọn thư mục")
            return False
        try:
            n = len(find_images(Path(folder)))
        except OSError:
            self.count_var.set("Không đọc được thư mục")
            return False
        txt = f"Tìm thấy {n} ảnh"
        if self.extra_files:
            txt += f" + {len(self.extra_files)} ảnh thêm"
        if self.excluded:
            txt += f" − {len(self.excluded)} ảnh bớt"
        self.count_var.set(txt)
        return True

    def add_images(self):
        """Them anh le (co the tu thu muc khac) vao ban ghep."""
        if not self.folder_var.get().strip():
            messagebox.showwarning(
                "Thiếu thông tin",
                "Hãy chọn thư mục ảnh trước, rồi thêm ảnh lẻ từ nơi khác.")
            return
        paths = filedialog.askopenfilenames(
            title="Thêm ảnh vào bản ghép (có thể từ thư mục khác)",
            filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif"),
                       ("Tất cả", "*.*")])
        if not paths:
            return
        for p in paths:
            name = Path(p).name.lower()
            self.excluded = [x for x in self.excluded if x.lower() != name]
            if all(p.lower() != q.lower() for q in self.extra_files):
                self.extra_files.append(p)
        self._update_count()
        self.do_preview()

    def remove_images_dialog(self):
        """Chon nhieu anh de bot khoi ban ghep tren luoi thumbnail."""
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Thiếu thông tin", "Hãy chọn thư mục ảnh trước.")
            return
        try:
            files = find_images(Path(folder))
        except OSError:
            messagebox.showerror("Lỗi", "Không đọc được thư mục ảnh.")
            return
        for p in self.extra_files:
            pp = Path(p)
            if pp.is_file() and all(str(pp).lower() != str(f).lower() for f in files):
                files.append(pp)
        files = files[:MAX_IMAGES]
        if not files:
            messagebox.showinfo("Trống", "Chưa có ảnh nào.")
            return

        dlg = tk.Toplevel(self)
        dlg.title("Bớt ảnh — bấm chọn những ảnh KHÔNG muốn ghép")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)
        body = ttk.Frame(dlg, padding=10)
        body.pack(fill="both", expand=True)

        pick_var = tk.StringVar()

        def on_change():
            pick_var.set(f"Sẽ bớt {len(gallery.picked)}/{len(files)} ảnh")

        gallery = ThumbGallery(body, files, mode="pick", max_pick=len(files),
                               on_change=on_change)
        gallery.grid(row=0, column=0, sticky="nsew")
        excl = {x.lower() for x in self.excluded}
        gallery.picked = [i for i, f in enumerate(files) if f.name.lower() in excl]
        gallery._draw_all()
        on_change()

        ttk.Label(body, textvariable=pick_var).grid(
            row=1, column=0, sticky="w", pady=(8, 0))
        btns = ttk.Frame(body)
        btns.grid(row=2, column=0, sticky="we", pady=(10, 0))

        def ok():
            names = gallery.picked_names()
            self.excluded = list(names)
            low = {n.lower() for n in names}
            self.custom_order = [x for x in self.custom_order
                                 if x.lower() not in low]
            if self.hero_files:
                nh = [x for x in self.hero_files if x.lower() not in low]
                if nh != self.hero_files:
                    self.hero_files = nh
                    self._update_hero_label()
            dlg.destroy()
            self._update_count()
            self.do_preview()

        def clear_all():
            gallery.picked = []
            gallery._draw_all()
            on_change()

        ttk.Button(btns, text="Áp dụng", command=ok).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(btns, text="Bỏ chọn hết", command=clear_all).pack(
            side="left", expand=True, fill="x", padx=4)
        ttk.Button(btns, text="Hủy", command=dlg.destroy).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

    def pick_color(self):
        color = colorchooser.askcolor(self.bg_color, title="Chọn màu nền")
        if color and color[1]:
            self.bg_color = color[1]
            self.bg_btn.configure(bg=self.bg_color)
            self.schedule_preview()

    def _pick_info_color(self, which: str):
        """Chon mau so/huy hieu hoac mau truc cho layout infographic."""
        cur = self.num_color if which == "num" else self.line_color
        color = colorchooser.askcolor(
            cur or "#2563EB",
            title="Chọn màu số/huy hiệu" if which == "num" else "Chọn màu trục")
        if color and color[1]:
            btn = self.num_color_btn if which == "num" else self.line_color_btn
            if which == "num":
                self.num_color = color[1]
            else:
                self.line_color = color[1]
            btn.configure(bg=color[1], text="     ")
            self.schedule_preview()

    def _reset_info_colors(self):
        self.num_color = None
        self.line_color = None
        for btn in (self.num_color_btn, self.line_color_btn):
            btn.configure(bg=self._auto_btn_bg, text="Tự động")
        self.schedule_preview()

    def _dialog_files(self) -> list[Path] | None:
        """Danh sach anh cua thu muc hien tai cho cac hop thoai (da cap 300)."""
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Thiếu thông tin", "Hãy chọn thư mục ảnh trước.")
            return None
        try:
            files = find_images(Path(folder))
        except OSError:
            messagebox.showerror("Lỗi", "Không đọc được thư mục ảnh.")
            return None
        for p in self.extra_files:
            pp = Path(p)
            if pp.is_file() and all(str(pp).lower() != str(f).lower() for f in files):
                files.append(pp)
        if self.excluded:
            excl = {x.lower() for x in self.excluded}
            files = [f for f in files if f.name.lower() not in excl]
        if not files:
            messagebox.showinfo("Trống", "Thư mục chưa có ảnh nào.")
            return None
        return files[:MAX_IMAGES]

    def choose_heroes(self):
        """Hop thoai chon dich danh anh chu (toi da 6) tren luoi thumbnail."""
        files = self._dialog_files()
        if not files:
            return

        dlg = tk.Toplevel(self)
        dlg.title("Chọn ảnh chủ đạo — bấm vào ảnh để chọn/bỏ (tối đa 6)")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        body = ttk.Frame(dlg, padding=10)
        body.pack(fill="both", expand=True)

        pick_var = tk.StringVar()

        def on_change():
            k = len(gallery.picked)
            pick_var.set(f"Đang chọn: {k}/6 ảnh — số trên ảnh là thứ tự ảnh chủ")

        gallery = ThumbGallery(body, files, mode="pick", max_pick=6,
                               on_change=on_change)
        gallery.grid(row=0, column=0, sticky="nsew")

        # danh dau lai lua chon cu
        cur = [n.lower() for n in self.hero_files]
        by_name = {f.name.lower(): i for i, f in enumerate(files)}
        gallery.picked = [by_name[n] for n in cur if n in by_name][:6]
        gallery._draw_all()
        on_change()

        ttk.Label(body, textvariable=pick_var).grid(
            row=1, column=0, sticky="w", pady=(8, 0))

        btns = ttk.Frame(body)
        btns.grid(row=2, column=0, sticky="we", pady=(10, 0))

        def ok():
            self.hero_files = gallery.picked_names()
            if self.hero_files:
                self.heroes_var.set(len(self.hero_files))
            self._update_hero_label()
            dlg.destroy()
            self.schedule_preview()

        def auto():
            self.hero_files = []
            self._update_hero_label()
            dlg.destroy()
            self.schedule_preview()

        ttk.Button(btns, text="Dùng ảnh đã chọn", command=ok).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(btns, text="Tự động (ảnh đầu)", command=auto).pack(
            side="left", expand=True, fill="x", padx=4)
        ttk.Button(btns, text="Hủy", command=dlg.destroy).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

    def arrange_order(self):
        """Hop thoai keo tha sap xep vi tri tung anh trong khung ghep."""
        files = self._dialog_files()
        if not files:
            return

        dlg = tk.Toplevel(self)
        dlg.title("Sắp xếp vị trí ảnh — kéo thả để di chuyển")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        body = ttk.Frame(dlg, padding=10)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=("Ảnh số 1 vào ô đầu tiên của bố cục (với kiểu "
                              "Ảnh chủ đạo, số 1 là ảnh chủ). Kéo thả hoặc "
                              "bấm chọn rồi dùng nút di chuyển."),
                  foreground="#555555", wraplength=640).grid(
            row=0, column=0, sticky="w", pady=(0, 6))

        # thu tu ban dau: ap lai thu tu tu chon cu (neu co)
        init = None
        if self.custom_order:
            by_name = {f.name.lower(): i for i, f in enumerate(files)}
            seq = [by_name[n.lower()] for n in self.custom_order
                   if n.lower() in by_name]
            init = seq + [i for i in range(len(files)) if i not in set(seq)]

        gallery = ThumbGallery(body, files, mode="reorder", init_order=init)
        gallery.grid(row=1, column=0, sticky="nsew")

        mv = ttk.Frame(body)
        mv.grid(row=2, column=0, sticky="we", pady=(8, 0))
        ttk.Label(mv, text="Di chuyển ảnh đang chọn:").pack(side="left")
        for kind, label in [("top", "Lên đầu"), ("up", "← Lên"),
                            ("down", "Xuống →"), ("end", "Về cuối")]:
            ttk.Button(mv, text=label, width=9,
                       command=lambda k=kind: gallery.move_selected(k)).pack(
                side="left", padx=(6, 0))

        btns = ttk.Frame(body)
        btns.grid(row=3, column=0, sticky="we", pady=(10, 0))

        def ok():
            self.custom_order = gallery.order_names()
            self.order_var.set("custom")
            dlg.destroy()
            self.schedule_preview()

        def reset():
            self.custom_order = []
            if self.order_var.get() == "custom":
                self.order_var.set("name")
            dlg.destroy()
            self.schedule_preview()

        ttk.Button(btns, text="Dùng thứ tự này", command=ok).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(btns, text="Đặt lại (theo tên)", command=reset).pack(
            side="left", expand=True, fill="x", padx=4)
        ttk.Button(btns, text="Hủy", command=dlg.destroy).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

    def _collect_args(self) -> dict:
        try:
            heroes = max(1, min(6, int(self.heroes_var.get())))
        except (tk.TclError, ValueError):
            heroes = 1
        return dict(
            preset=self._preset_key(),
            layout_style=self._layout_key(),
            theme=self._theme_key(),
            margin=self.margin_var.get(),
            bg=self.bg_color,
            order=self.order_var.get(),
            custom_order=list(self.custom_order) or None,
            hero_count=heroes,
            hero_files=list(self.hero_files) or None,
            hero_fill=self.fill_labels.get(self.fill_var.get(), "justified"),
            info_opts=dict(
                numbers=bool(self.num_on.get()),
                captions=bool(self.cap_on.get()),
                markers=bool(self.marker_on.get()),
                num_color=self.num_color,
                line_color=self.line_color,
            ),
            adjust={k: dict(v) for k, v in self.img_adjust.items()} or None,
            extra_files=list(self.extra_files) or None,
            exclude=list(self.excluded) or None,
        )

    # ------------------------------------------------------- preview ----
    def do_preview(self):
        if self._busy:
            return
        if self._mode() == "tpl":
            if len(self.tpl_files) < 2:
                return
            self._busy = True
            self.status_var.set("Đang tạo xem trước...")
            threading.Thread(target=self._tpl_preview_work,
                             args=(self._tpl_args(),), daemon=True).start()
            return
        folder = self.folder_var.get().strip()
        if not folder:
            return
        self._busy = True
        self.status_var.set("Đang tạo xem trước...")
        args = self._collect_args()
        threading.Thread(target=self._preview_work, args=(folder, args),
                         daemon=True).start()

    def _preview_work(self, folder: str, args: dict):
        try:
            meta: dict = {}
            pmax = min(3600, round(max(self.pv_w, self.pv_h)
                                   * max(1.0, self._pv_zoom) * 1.25))
            img, warnings = make_collage_image(
                folder, preview_max=pmax, supersample=1,
                meta_out=meta, **args,
            )
            self.after(0, self._preview_done, img, warnings, meta)
        except Exception as e:  # noqa: BLE001
            self.after(0, self._fail, str(e))

    def _preview_done(self, img: Image.Image, warnings: list, meta: dict):
        self._busy = False
        self._pv_img = img
        self._pv_meta = meta if meta.get("cells") else None
        self._pv_sel = None
        self._pv_dragging = False
        self._pv_redraw()
        note = f"Xem trước {img.width}×{img.height} (bản xuất sẽ nét hơn)."
        if warnings:
            note += "  Lưu ý: " + "; ".join(warnings)
        self.status_var.set(note)

    def _pv_redraw(self):
        """Ve lai anh preview theo zoom hien tai (can giua, co the cuon)."""
        img = self._pv_img
        if img is None:
            return
        cv = self.preview_cv
        cw = max(60, cv.winfo_width())
        ch = max(60, cv.winfo_height())
        k = min(cw / img.width, ch / img.height) * self._pv_zoom
        k = min(k, 4500 / max(img.width, img.height))  # chan bo nho
        resample = (Image.Resampling.LANCZOS if k <= 1.2
                    else Image.Resampling.BILINEAR)
        disp = img.resize((max(1, round(img.width * k)),
                           max(1, round(img.height * k))), resample)
        fx, fy = cv.xview()[0], cv.yview()[0]  # giu vi tri cuon
        self._preview_photo = ImageTk.PhotoImage(disp)
        self._pv_k = k
        self._pv_ox = max(0, (cw - disp.width) // 2)
        self._pv_oy = max(0, (ch - disp.height) // 2)
        self._pv_sw = max(disp.width, cw)
        self._pv_sh = max(disp.height, ch)
        cv.delete("all")
        cv.create_image(self._pv_ox, self._pv_oy, anchor="nw",
                        image=self._preview_photo)
        cv.configure(scrollregion=(0, 0, self._pv_sw, self._pv_sh))
        cv.xview_moveto(fx)
        cv.yview_moveto(fy)
        self._pv_zoom_lbl.configure(text=f"{round(self._pv_zoom * 100)}%")

    def _pv_resize(self, e):
        """Cua so doi kich thuoc -> ve lai ngay; neu can net hon thi render lai."""
        if e.width < 60 or e.height < 60:
            return
        self.pv_w, self.pv_h = e.width, e.height
        if self._pv_img is None:
            self.preview_cv.coords(self._pv_hint, e.width // 2, e.height // 2)
            return
        self._pv_redraw()
        self._pv_maybe_rerender()

    def _pv_maybe_rerender(self):
        """Neu anh nguon cua preview nho hon vung hien thi -> render lai net hon."""
        if self._pv_img is None or not self.folder_var.get().strip():
            return
        need = round(max(self.pv_w, self.pv_h) * self._pv_zoom * 1.25)
        have = max(self._pv_img.width, self._pv_img.height)
        if need > have * 1.08 and have < 3600:
            if self._rs_job:
                self.after_cancel(self._rs_job)
            self._rs_job = self.after(450, self._resize_rerender)

    def _resize_rerender(self):
        self._rs_job = None
        self.do_preview()

    # ---------------------------------------------- zoom & cuon preview ----
    def _pv_set_zoom(self, z: float, cx: float | None = None,
                     cy: float | None = None):
        """Dat zoom, giu diem (cx, cy - toa do widget) dung yen."""
        if self._pv_img is None:
            return
        z = max(1.0, min(8.0, z))
        if abs(z - self._pv_zoom) < 1e-9:
            return
        cv = self.preview_cv
        if cx is None:
            cx = max(60, cv.winfo_width()) / 2
            cy = max(60, cv.winfo_height()) / 2
        # diem anh (theo pixel ban preview) dang nam duoi (cx, cy)
        ix = (cv.canvasx(cx) - self._pv_ox) / self._pv_k
        iy = (cv.canvasy(cy) - self._pv_oy) / self._pv_k
        self._pv_zoom = z
        self._pv_redraw()
        cv.xview_moveto(max(0.0, (ix * self._pv_k + self._pv_ox - cx) / self._pv_sw))
        cv.yview_moveto(max(0.0, (iy * self._pv_k + self._pv_oy - cy) / self._pv_sh))
        self._pv_maybe_rerender()

    def _pv_zoom_step(self, factor: float):
        self._pv_set_zoom(self._pv_zoom * factor)

    def _pv_zoom_fit(self):
        if self._pv_img is None:
            return
        self._pv_zoom = 1.0
        self._pv_redraw()

    def _pv_wheel(self, e):
        cv = self.preview_cv
        if e.state & 0x0004:  # Ctrl -> zoom khung tai vi tri con tro
            cx = e.x_root - cv.winfo_rootx()
            cy = e.y_root - cv.winfo_rooty()
            self._pv_set_zoom(self._pv_zoom * (1.2 if e.delta > 0 else 1 / 1.2),
                              cx, cy)
        elif e.state & 0x0001:  # Shift -> cuon ngang
            cv.xview_scroll(-1 if e.delta > 0 else 1, "units")
        elif (self.pv_mode.get() == "adjust" and self._pv_meta
              and not self._busy):
            # che do chinh anh: lan tren o nao thi phong to/thu nho anh o do
            cx = e.x_root - cv.winfo_rootx()
            cy = e.y_root - cv.winfo_rooty()
            i = self._pv_hit(cv.canvasx(cx), cv.canvasy(cy))
            if i is None:
                cv.yview_scroll(-1 if e.delta > 0 else 1, "units")
            else:
                z = float(self._adj_of(i).get("zoom", 1.0))
                z = max(1.0, min(4.0, z * (1.1 if e.delta > 0 else 1 / 1.1)))
                self._set_adjust(i, zoom=z)
                self.status_var.set(f"Phóng ảnh trong ô: {round(z * 100)}%")
                self._adj_live_draw(i)
                self._schedule_adj_render(500)
        else:
            cv.yview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"

    def _adj_apply(self):
        self._adj_job = None
        if self._busy:
            self._schedule_adj_render(300)
            return
        self.do_preview()

    def _pv_leave(self):
        self.unbind_all("<MouseWheel>")
        self._pv_clear_hover()

    # ------------------------------------- chinh rieng tung anh trong o ----
    def _adj_of(self, i: int) -> dict:
        return dict(self.img_adjust.get(self._pv_meta["files"][i].name, {}))

    def _set_adjust(self, i: int, **kv):
        """Cap nhat chinh sua cua anh o o i; xoa muc neu ve mac dinh."""
        name = self._pv_meta["files"][i].name
        a = self.img_adjust.get(name, {})
        a.update(kv)
        if (int(a.get("rot", 0)) % 360 == 0
                and abs(float(a.get("zoom", 1.0)) - 1.0) < 1e-6
                and abs(float(a.get("dx", 0.0))) < 1e-6
                and abs(float(a.get("dy", 0.0))) < 1e-6):
            self.img_adjust.pop(name, None)
        else:
            self.img_adjust[name] = a

    def _adj_live_img(self, i: int) -> Image.Image | None:
        """Anh goc (da xoay) de xem truoc tuc thi khi chinh trong o.
        Chi dung cho layout dan anh phang; polaroid/stack/infographic thi thoi."""
        lk = self._layout_key()
        if self._mode() == "auto" and (lk in ("polaroid", "stack")
                                       or lk in INFO_LAYOUTS):
            return None
        path = self._pv_meta["files"][i]
        rot = int(self._adj_of(i).get("rot", 0)) % 360
        hit = self._adj_cache.get(path.name)
        if hit and hit[0] == rot:
            return hit[1]
        try:
            img = Image.open(path)
            if (img.format or "").upper() == "JPEG":
                img.draft("RGB", (2048, 2048))
            img = ImageOps.exif_transpose(img)
            if rot:
                img = img.transpose({90: Image.Transpose.ROTATE_270,
                                     180: Image.Transpose.ROTATE_180,
                                     270: Image.Transpose.ROTATE_90}[rot])
            img = img.convert("RGB")
            img.thumbnail((1600, 1600), Image.Resampling.BILINEAR)
        except Exception:  # noqa: BLE001
            return None
        if len(self._adj_cache) > 12:  # gioi han bo nho
            self._adj_cache.pop(next(iter(self._adj_cache)))
        self._adj_cache[path.name] = (rot, img)
        return img

    def _adj_live_draw(self, i: int, dx: float | None = None,
                       dy: float | None = None,
                       zoom: float | None = None) -> bool:
        """Ve lai NGAY o i voi thong so tam thoi -> keo/lan muot, khong cho render."""
        src = self._adj_live_img(i)
        if src is None:
            return False
        a = self._adj_of(i)
        z = max(1.0, float(zoom if zoom is not None else a.get("zoom", 1.0)))
        vdx = float(dx if dx is not None else a.get("dx", 0.0))
        vdy = float(dy if dy is not None else a.get("dy", 0.0))
        x0, y0, x1, y1 = self._pv_rect(i)
        cw = max(2, int(round(x1 - x0)))
        ch = max(2, int(round(y1 - y0)))
        sw, sh = src.size
        s0 = max(cw / sw, ch / sh) * z
        vw = min(sw, cw / s0)
        vh = min(sh, ch / s0)
        left = max(0.0, min(sw - vw, (sw - vw) * (0.5 + 0.5 * vdx)))
        top = max(0.0, min(sh - vh, (sh - vh) * (0.5 + 0.5 * vdy)))
        piece = src.crop((round(left), round(top),
                          round(left + vw), round(top + vh)))
        piece = piece.resize((cw, ch), Image.Resampling.BILINEAR)
        self._adj_photo = ImageTk.PhotoImage(piece)
        cv = self.preview_cv
        cv.delete("adjlive")
        cv.create_image(round(x0), round(y0), anchor="nw",
                        image=self._adj_photo, tags="adjlive")
        cv.tag_raise("sel")
        return True

    def _schedule_adj_render(self, delay: int = 500):
        """Render lai toan bo (co ne khi dang ban) sau khi nguoi dung ngung chinh."""
        if self._adj_job:
            self.after_cancel(self._adj_job)
        self._adj_job = self.after(delay, self._adj_apply)

    def _adj_rotate(self, i: int, delta: int):
        rot = (int(self._adj_of(i).get("rot", 0)) + delta) % 360
        self._set_adjust(i, rot=rot)
        self.do_preview()

    def _adj_zoom_step(self, i: int, factor: float):
        z = float(self._adj_of(i).get("zoom", 1.0))
        self._set_adjust(i, zoom=max(1.0, min(4.0, z * factor)))
        if self._adj_live_draw(i):
            self._schedule_adj_render(400)
        else:
            self.do_preview()

    def _adj_reset(self, i: int):
        self.img_adjust.pop(self._pv_meta["files"][i].name, None)
        self.do_preview()

    def _remove_image(self, i: int):
        if self._mode() == "tpl":
            if len(self.tpl_files) <= 2:
                messagebox.showinfo("Tối thiểu 2 ảnh",
                                    "Ghép nhanh cần ít nhất 2 ảnh.")
                return
            p = str(self._pv_meta["files"][i]).lower()
            self.tpl_files = [x for x in self.tpl_files
                              if str(Path(x)).lower() != p]
            self._tpl_update_count()
            self._tpl_refresh()
            self.do_preview()
            return
        name = self._pv_meta["files"][i].name
        self.excluded.append(name)
        self.custom_order = [x for x in self.custom_order
                             if x.lower() != name.lower()]
        if self.hero_files:
            nh = [x for x in self.hero_files if x.lower() != name.lower()]
            if nh != self.hero_files:
                self.hero_files = nh
                self._update_hero_label()
        self._update_count()
        self.do_preview()

    def _restore_images(self):
        self.excluded = []
        self._update_count()
        self.do_preview()

    # -------------------------------- chuot phai: keo xem / menu tung anh ----
    def _pv_rpress(self, e):
        self._pv_rmoved = False
        self._pv_rpos = (e.x, e.y)
        self.preview_cv.scan_mark(e.x, e.y)

    def _pv_rdrag(self, e):
        if (abs(e.x - self._pv_rpos[0]) > 3
                or abs(e.y - self._pv_rpos[1]) > 3):
            self._pv_rmoved = True
        self.preview_cv.scan_dragto(e.x, e.y, gain=1)

    def _pv_rrelease(self, e):
        if self._pv_rmoved or not self._pv_meta or self._busy:
            return
        cv = self.preview_cv
        i = self._pv_hit(cv.canvasx(e.x), cv.canvasy(e.y))
        if i is None:
            return
        name = self._pv_meta["files"][i].name
        m = tk.Menu(self, tearoff=0)
        m.add_command(label=f"↻ Xoay phải 90° — {name}",
                      command=lambda: self._adj_rotate(i, 90))
        m.add_command(label="↺ Xoay trái 90°",
                      command=lambda: self._adj_rotate(i, -90))
        m.add_command(label="Phóng to trong ô (+)",
                      command=lambda: self._adj_zoom_step(i, 1.15))
        m.add_command(label="Thu nhỏ trong ô (−)",
                      command=lambda: self._adj_zoom_step(i, 1 / 1.15))
        if name in self.img_adjust:
            m.add_command(label="Đặt lại chỉnh sửa ảnh này",
                          command=lambda: self._adj_reset(i))
        m.add_separator()
        m.add_command(label="Bớt ảnh này khỏi bản ghép",
                      command=lambda: self._remove_image(i))
        if self._mode() == "tpl":
            if len(self.tpl_files) < 9:
                m.add_command(label="Thêm ảnh…", command=self.tpl_add)
        else:
            m.add_command(label="Thêm ảnh…", command=self.add_images)
            if self.excluded:
                m.add_command(label=f"Khôi phục {len(self.excluded)} ảnh đã bớt",
                              command=self._restore_images)
        m.tk_popup(e.x_root, e.y_root)

    # ------------------------------------ keo tha tren khung xem truoc ----
    def _pv_rect(self, i: int) -> tuple[float, float, float, float]:
        x0, y0, x1, y1 = self._pv_meta["cells"][i]
        k = self._pv_k
        return (x0 * k + self._pv_ox, y0 * k + self._pv_oy,
                x1 * k + self._pv_ox, y1 * k + self._pv_oy)

    def _pv_hit(self, x: int, y: int) -> int | None:
        if not self._pv_meta:
            return None
        for i in range(len(self._pv_meta["cells"])):
            x0, y0, x1, y1 = self._pv_rect(i)
            if x0 <= x <= x1 and y0 <= y <= y1:
                return i
        return None

    def _pv_clear_hover(self):
        self.preview_cv.delete("hover")
        self.preview_cv.configure(cursor="")

    def _pv_motion(self, e):
        if self._pv_sel is not None or not self._pv_meta or self._busy:
            return
        cv = self.preview_cv
        cv.delete("hover")
        i = self._pv_hit(cv.canvasx(e.x), cv.canvasy(e.y))
        if i is None:
            cv.configure(cursor="")
            return
        cv.configure(cursor="hand2")
        x0, y0, x1, y1 = self._pv_rect(i)
        cv.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                            outline="#FFFFFF", dash=(4, 3), tags="hover")

    def _pv_press(self, e):
        if not self._pv_meta or self._busy:
            return
        cv = self.preview_cv
        cv.delete("hover")
        cv.delete("sel")
        self._pv_adj = None
        i = self._pv_hit(cv.canvasx(e.x), cv.canvasy(e.y))
        self._pv_dragging = False
        if i is not None and self.pv_mode.get() == "adjust":
            # keo de doi vung cat cua anh trong o
            if self._adj_job:
                self.after_cancel(self._adj_job)
                self._adj_job = None
            a = self._adj_of(i)
            self._pv_adj = (i, cv.canvasx(e.x), cv.canvasy(e.y),
                            float(a.get("dx", 0.0)), float(a.get("dy", 0.0)))
            self._adj_live_img(i)  # nap san anh goc de keo muot
            x0, y0, x1, y1 = self._pv_rect(i)
            cv.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                                outline="#22C55E", width=3, tags="sel")
            return
        self._pv_sel = i
        if self._pv_sel is None:
            return
        x0, y0, x1, y1 = self._pv_rect(self._pv_sel)
        cv.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                            outline="#3B82F6", width=3, tags="sel")

    def _pv_drag(self, e):
        cv = self.preview_cv
        if self._pv_adj is not None:
            # keo -> anh trong o di chuyen theo TUC THI (live)
            i, sx, sy, dx0, dy0 = self._pv_adj
            ex, ey = cv.canvasx(e.x), cv.canvasy(e.y)
            x0, y0, x1, y1 = self._pv_rect(i)
            ddx = -2.0 * (ex - sx) / max(1.0, x1 - x0)
            ddy = -2.0 * (ey - sy) / max(1.0, y1 - y0)
            dx = max(-1.0, min(1.0, dx0 + ddx))
            dy = max(-1.0, min(1.0, dy0 + ddy))
            cv.delete("drag")
            if not self._adj_live_draw(i, dx=dx, dy=dy):
                # layout co the/khung (polaroid...) -> chi ve mui ten dinh huong
                cv.create_line(sx, sy, ex, ey, fill="#22C55E", width=3,
                               arrow="last", tags="drag")
            return
        if self._pv_sel is None:
            return
        self._pv_dragging = True
        cv.delete("drag")
        ex, ey = cv.canvasx(e.x), cv.canvasy(e.y)
        j = self._pv_hit(ex, ey)
        if j is not None and j != self._pv_sel:
            x0, y0, x1, y1 = self._pv_rect(j)
            cv.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                                outline="#F59E0B", width=3, tags="drag")
        sx0, sy0, sx1, sy1 = self._pv_rect(self._pv_sel)
        w = max(24.0, min(90.0, sx1 - sx0)) / 2
        h = max(24.0, min(90.0, sy1 - sy0)) / 2
        cv.create_rectangle(ex - w, ey - h, ex + w, ey + h,
                            outline="#3B82F6", dash=(4, 3), width=2, tags="drag")

    def _pv_release(self, e):
        cv = self.preview_cv
        cv.delete("drag")
        if self._pv_adj is not None:
            # tha chuot -> chot dx/dy; anh da o dung vi tri (live), render nen sau
            i, sx, sy, dx0, dy0 = self._pv_adj
            self._pv_adj = None
            cv.delete("sel")
            ex, ey = cv.canvasx(e.x), cv.canvasy(e.y)
            if abs(ex - sx) < 3 and abs(ey - sy) < 3:
                cv.delete("adjlive")
                return  # chi la click
            x0, y0, x1, y1 = self._pv_rect(i)
            ddx = -2.0 * (ex - sx) / max(1.0, x1 - x0)
            ddy = -2.0 * (ey - sy) / max(1.0, y1 - y0)
            self._set_adjust(i,
                             dx=max(-1.0, min(1.0, dx0 + ddx)),
                             dy=max(-1.0, min(1.0, dy0 + ddy)))
            if self._adj_live_draw(i):
                self._schedule_adj_render(500)
            else:
                self.do_preview()
            return
        src = self._pv_sel
        dragging = self._pv_dragging
        self._pv_sel = None
        self._pv_dragging = False
        if src is None or not self._pv_meta:
            return
        dst = self._pv_hit(cv.canvasx(e.x), cv.canvasy(e.y))
        if not dragging or dst is None or dst == src:
            cv.delete("sel")
            return
        cv.delete("sel")
        files = list(self._pv_meta["files"])
        files[src], files[dst] = files[dst], files[src]
        if self._mode() == "tpl":
            # doi cho truc tiep trong danh sach anh ghep nhanh
            self.tpl_files = [str(f) for f in files]
            self.do_preview()
            return
        self.custom_order = [f.name for f in files]
        self.order_var.set("custom")
        # vi tri anh chu da nam trong thu tu tu chon -> bo chon dich danh
        if self.hero_files:
            self.hero_files = []
            self._update_hero_label()
        self.do_preview()

    # --------------------------------------------------------- export ----
    def start(self):
        if self._busy:
            return
        if self._mode() == "tpl":
            if len(self.tpl_files) < 2:
                messagebox.showwarning(
                    "Thiếu thông tin",
                    "Hãy chọn 2–9 ảnh ở tab Ghép nhanh trước.")
                return
            self._busy = True
            self.go_btn.state(["disabled"])
            self.prog["value"] = 0
            self.status_var.set("Đang ghép bản chất lượng cao...")
            threading.Thread(target=self._tpl_work,
                             args=(self._tpl_args(),), daemon=True).start()
            return
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Thiếu thông tin", "Hãy chọn thư mục ảnh trước.")
            return
        self._busy = True
        self.go_btn.state(["disabled"])
        self.prog["value"] = 0
        self.status_var.set("Đang ghép bản chất lượng cao...")
        args = self._collect_args()
        threading.Thread(target=self._work, args=(folder, args), daemon=True).start()

    def _work(self, folder: str, args: dict):
        def progress(done: int, total: int):
            self.after(0, self._update_progress, done, total)

        try:
            out_path, warnings = make_collage(folder, progress=progress, **args)
            self.after(0, self._done, out_path, warnings)
        except Exception as e:  # noqa: BLE001
            self.after(0, self._fail, str(e))

    def _update_progress(self, done: int, total: int):
        self.prog["value"] = done * 100 / total
        self.status_var.set(f"Đang ghép {done}/{total} ảnh...")

    def _done(self, out_path: Path, warnings: list):
        self._busy = False
        self.go_btn.state(["!disabled"])
        self.prog["value"] = 100
        self.status_var.set(f"Xong: {out_path.name}")
        msg = f"Đã lưu:\n{out_path}"
        if warnings:
            msg += "\n\nLưu ý:\n- " + "\n- ".join(warnings)
        if messagebox.askyesno("Hoàn tất", msg + "\n\nMở ảnh ngay?"):
            os.startfile(out_path)  # noqa: S606 - mo file local do user tao

    def _fail(self, err: str):
        self._busy = False
        self.go_btn.state(["!disabled"])
        self.status_var.set("Lỗi")
        messagebox.showerror("Lỗi", err)

    # ------------------------------------------- trinh chieu tu dong ----
    def show_export(self, kind: str):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Hãy chọn thư mục ảnh ở khung trên cùng trước.")
            return
        if self._busy:
            return
        self._busy = True
        self.status_var.set("Đang tạo trình chiếu...")
        args = dict(
            theme=self._theme_key(),
            duration=max(1.5, float(self.show_dur_var.get() or 5.0)),
            title=Path(folder).name,
            order="random" if self.order_var.get() == "random" else "name",
        )
        threading.Thread(target=self._show_work, args=(folder, kind, args),
                         daemon=True).start()

    def _show_work(self, folder: str, kind: str, args: dict):
        def status(msg: str):
            self.after(0, self.status_var.set, msg)

        try:
            if kind == "html":
                from .slideshow import export_slideshow_html
                out, warnings = export_slideshow_html(
                    folder, status=status, **args)
            else:
                from .slideshow import export_slideshow_pptx
                out, warnings = export_slideshow_pptx(
                    folder, status=status, **args)
            self.after(0, self._md_done, out, warnings)
        except Exception as e:  # noqa: BLE001
            self.after(0, self._fail, str(e))


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
