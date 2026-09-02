"""Giao dien do hoa cho Windows: dieu khien ben trai, xem truoc ben phai."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .core import CollageError, make_collage, make_collage_image
from .layout import LAYOUT_STYLES
from .presets import DEFAULT_PRESET, PRESET_GROUPS, PRESETS
from .renderer import INFO_LAYOUTS, find_images
from .themes import DEFAULT_THEME, THEMES

PREVIEW_W = 640
PREVIEW_H = 480


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ghép ảnh thông minh — Prodat09")
        self.resizable(False, False)
        self.bg_color = "#FFFFFF"
        self._preview_photo = None  # giu tham chieu tranh bi thu hoi
        self._busy = False
        self._build()

    # ------------------------------------------------------------- UI ----
    def _build(self):
        pad = {"padx": 8, "pady": 4}
        root = ttk.Frame(self)
        root.grid(sticky="nsew", padx=12, pady=12)

        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="nw")
        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="n", padx=(14, 0))

        # --- Thu muc anh ---
        lf = ttk.LabelFrame(left, text="Thư mục ảnh")
        lf.pack(fill="x", **pad)
        self.folder_var = tk.StringVar()
        ttk.Entry(lf, textvariable=self.folder_var, width=40).grid(
            row=0, column=0, sticky="we", padx=6, pady=4)
        ttk.Button(lf, text="Chọn...", command=self.pick_folder).grid(
            row=0, column=1, padx=6)
        self.count_var = tk.StringVar(value="Chưa chọn thư mục")
        ttk.Label(lf, textvariable=self.count_var, foreground="#555").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))

        # --- Preset theo nhom ---
        pf = ttk.LabelFrame(left, text="Kiểu đầu ra")
        pf.pack(fill="x", **pad)
        self.preset_var = tk.StringVar(value=DEFAULT_PRESET)
        for group, keys in PRESET_GROUPS.items():
            ttk.Label(pf, text=group, font=("", 9, "bold")).pack(
                anchor="w", padx=6, pady=(4, 0))
            for key in keys:
                ttk.Radiobutton(
                    pf, text=PRESETS[key][0], value=key,
                    variable=self.preset_var, command=self.schedule_preview,
                ).pack(anchor="w", padx=18)

        # --- Layout + Theme ---
        of = ttk.LabelFrame(left, text="Bố cục & Theme")
        of.pack(fill="x", **pad)

        ttk.Label(of, text="Kiểu xếp:").grid(row=0, column=0, sticky="w", padx=6, pady=3)
        self.layout_labels = {v: k for k, v in LAYOUT_STYLES.items()}
        self.layout_var = tk.StringVar(value=LAYOUT_STYLES["justified"])
        cb = ttk.Combobox(of, textvariable=self.layout_var, state="readonly",
                          width=32, values=list(LAYOUT_STYLES.values()))
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
        self.fill_cb.grid(row=2, column=1, sticky="w", padx=6)
        self.fill_cb.bind("<<ComboboxSelected>>", lambda e: self.schedule_preview())

        ttk.Label(of, text="Theme:").grid(row=3, column=0, sticky="w", padx=6, pady=3)
        self.theme_labels = {v["label"]: k for k, v in THEMES.items()}
        self.theme_var = tk.StringVar(value=THEMES[DEFAULT_THEME]["label"])
        tb = ttk.Combobox(of, textvariable=self.theme_var, state="readonly",
                          width=32, values=[v["label"] for v in THEMES.values()])
        tb.grid(row=3, column=1, sticky="w", padx=6)
        tb.bind("<<ComboboxSelected>>", lambda e: self._on_theme_change())

        ttk.Label(of, text="Thứ tự ảnh:").grid(row=4, column=0, sticky="w", padx=6, pady=3)
        order_f = ttk.Frame(of)
        order_f.grid(row=4, column=1, sticky="w")
        self.order_var = tk.StringVar(value="name")
        for val, label in [("name", "Theo tên"), ("aspect", "Ít cắt"),
                           ("random", "Ngẫu nhiên")]:
            ttk.Radiobutton(order_f, text=label, value=val, variable=self.order_var,
                            command=self.schedule_preview).pack(side="left", padx=(0, 8))

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

        # --- Nut hanh dong ---
        bf = ttk.Frame(left)
        bf.pack(fill="x", **pad)
        self.preview_btn = ttk.Button(bf, text="XEM TRƯỚC", command=self.do_preview)
        self.preview_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.go_btn = ttk.Button(bf, text="GHÉP && LƯU FILE", command=self.start)
        self.go_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.prog = ttk.Progressbar(left, maximum=100)
        self.prog.pack(fill="x", **pad)
        self.status_var = tk.StringVar(value="Sẵn sàng")
        ttk.Label(left, textvariable=self.status_var, wraplength=340).pack(
            anchor="w", padx=8)

        # --- Trinh chieu anh tu dong (Ken Burns) ---
        kf = ttk.LabelFrame(left, text="Trình chiếu tự động — zoom in/out (từ thư mục ảnh ở trên)")
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

        ttk.Label(left, text="Ghép ảnh thông minh — © 2026 Prodat09",
                  foreground="#999", font=("", 8)).pack(anchor="e", padx=10)

        # --- Khung xem truoc ---
        prf = ttk.LabelFrame(right, text="Xem trước")
        prf.pack()
        placeholder = Image.new("RGB", (PREVIEW_W, PREVIEW_H), "#2B2B2B")
        self._preview_photo = ImageTk.PhotoImage(placeholder)
        self.preview_lbl = tk.Label(
            prf, image=self._preview_photo, compound="center",
            text="Chọn thư mục ảnh rồi bấm XEM TRƯỚC", fg="#AAAAAA",
            font=("", 11), bg="#2B2B2B",
        )
        self.preview_lbl.pack(padx=6, pady=6)

        self._on_layout_change()  # trang thai ban dau cua o "Anh chu dao"

    # ------------------------------------------------------- helpers ----
    def _layout_key(self) -> str:
        return self.layout_labels[self.layout_var.get()]

    def _theme_key(self) -> str:
        return self.theme_labels[self.theme_var.get()]

    def _on_layout_change(self):
        is_hero = self._layout_key() == "hero"
        state = ["!disabled"] if is_hero else ["disabled"]
        self.hero_spin.state(state)
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

    def schedule_preview(self):
        """Tu dong lam moi xem truoc (neu da co thu muc va khong ban)."""
        if self.folder_var.get().strip() and not self._busy:
            self.after(150, self.do_preview)

    def pick_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa ảnh")
        if folder:
            self.folder_var.set(folder)
            self.hero_files = []
            self._update_hero_label()
            try:
                n = len(find_images(Path(folder)))
                self.count_var.set(f"Tìm thấy {n} ảnh")
            except OSError:
                self.count_var.set("Không đọc được thư mục")
                return
            self.do_preview()

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

    def choose_heroes(self):
        """Hop thoai chon dich danh anh chu (toi da 6), co xem thumbnail."""
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Thiếu thông tin", "Hãy chọn thư mục ảnh trước.")
            return
        try:
            files = find_images(Path(folder))
        except OSError:
            messagebox.showerror("Lỗi", "Không đọc được thư mục ảnh.")
            return
        if not files:
            messagebox.showinfo("Trống", "Thư mục chưa có ảnh nào.")
            return

        dlg = tk.Toplevel(self)
        dlg.title("Chọn ảnh chủ đạo (1–6 ảnh, giữ Ctrl để chọn nhiều)")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        body = ttk.Frame(dlg, padding=10)
        body.pack(fill="both", expand=True)

        lbf = ttk.Frame(body)
        lbf.grid(row=0, column=0, sticky="ns")
        sb = ttk.Scrollbar(lbf, orient="vertical")
        lb = tk.Listbox(lbf, selectmode="extended", width=38, height=18,
                        yscrollcommand=sb.set, exportselection=False)
        sb.configure(command=lb.yview)
        lb.pack(side="left", fill="y")
        sb.pack(side="left", fill="y")
        names = [f.name for f in files]
        for name in names:
            lb.insert("end", name)
        # danh dau lai lua chon cu
        cur = {n.lower() for n in self.hero_files}
        for i, name in enumerate(names):
            if name.lower() in cur:
                lb.selection_set(i)

        THUMB = 220
        ph = Image.new("RGB", (THUMB, THUMB), "#E8E8E8")
        dlg._photo = ImageTk.PhotoImage(ph)  # giu tham chieu
        thumb_lbl = tk.Label(body, image=dlg._photo, bg="#E8E8E8",
                             text="Bấm vào tên ảnh\nđể xem thử", fg="#777",
                             compound="center", font=("", 10))
        thumb_lbl.grid(row=0, column=1, sticky="n", padx=(12, 0))
        pick_var = tk.StringVar(value="Đang chọn: 0 ảnh")
        ttk.Label(body, textvariable=pick_var).grid(
            row=1, column=0, sticky="w", pady=(8, 0))

        def on_select(_e=None):
            sel = lb.curselection()
            pick_var.set(f"Đang chọn: {len(sel)} ảnh"
                         + ("  (chỉ lấy 6 ảnh đầu)" if len(sel) > 6 else ""))
            if not sel:
                return
            try:
                img = Image.open(files[sel[-1]])
                img.thumbnail((THUMB, THUMB))
                dlg._photo = ImageTk.PhotoImage(img.convert("RGB"))
                thumb_lbl.configure(image=dlg._photo, text="")
            except OSError:
                thumb_lbl.configure(text="Không đọc được ảnh", image="")

        lb.bind("<<ListboxSelect>>", on_select)
        on_select()

        btns = ttk.Frame(body)
        btns.grid(row=2, column=0, columnspan=2, sticky="we", pady=(10, 0))

        def ok():
            sel = list(lb.curselection())[:6]
            self.hero_files = [names[i] for i in sel]
            if sel:
                self.heroes_var.set(len(sel))
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

    def _collect_args(self) -> dict:
        try:
            heroes = max(1, min(6, int(self.heroes_var.get())))
        except (tk.TclError, ValueError):
            heroes = 1
        return dict(
            preset=self.preset_var.get(),
            layout_style=self._layout_key(),
            theme=self._theme_key(),
            margin=self.margin_var.get(),
            bg=self.bg_color,
            order=self.order_var.get(),
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
        )

    # ------------------------------------------------------- preview ----
    def do_preview(self):
        folder = self.folder_var.get().strip()
        if not folder or self._busy:
            return
        self._busy = True
        self.status_var.set("Đang tạo xem trước...")
        args = self._collect_args()
        threading.Thread(target=self._preview_work, args=(folder, args),
                         daemon=True).start()

    def _preview_work(self, folder: str, args: dict):
        try:
            img, warnings = make_collage_image(
                folder, preview_max=PREVIEW_W, supersample=1, **args,
            )
            self.after(0, self._preview_done, img, warnings)
        except Exception as e:  # noqa: BLE001
            self.after(0, self._fail, str(e))

    def _preview_done(self, img: Image.Image, warnings: list):
        self._busy = False
        # dat vua khung xem truoc, giu ti le
        k = min(PREVIEW_W / img.width, PREVIEW_H / img.height, 1.0)
        disp = img.resize((round(img.width * k), round(img.height * k)),
                          Image.Resampling.LANCZOS)
        self._preview_photo = ImageTk.PhotoImage(disp)
        self.preview_lbl.configure(
            image=self._preview_photo, text="",
            width=disp.width, height=disp.height,
        )
        note = f"Xem trước {img.width}×{img.height} (bản xuất sẽ nét hơn)."
        if warnings:
            note += "  Lưu ý: " + "; ".join(warnings)
        self.status_var.set(note)

    # --------------------------------------------------------- export ----
    def start(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Thiếu thông tin", "Hãy chọn thư mục ảnh trước.")
            return
        if self._busy:
            return
        self._busy = True
        self.go_btn.state(["disabled"])
        self.preview_btn.state(["disabled"])
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
        self.preview_btn.state(["!disabled"])
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
        self.preview_btn.state(["!disabled"])
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
