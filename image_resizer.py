"""
Image Resizer Pro - bulk image resizer with custom resolution.
Requires: Python 3.9+, Pillow   (pip install pillow)
"""
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image

SUPPORTED = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tga", ".tif", ".tiff", ".gif", ".dds")

RESAMPLE = {
    "Lanczos (best quality)": Image.LANCZOS,
    "Bicubic": Image.BICUBIC,
    "Bilinear": Image.BILINEAR,
    "Nearest (pixel art)": Image.NEAREST,
}

PRESETS = [256, 512, 1000, 1024, 2048, 4096]

# ---- colours ----
BG = "#14171c"
PANEL = "#1c2128"
CARD = "#232a33"
ACCENT = "#3d8bfd"
ACCENT_HOVER = "#5a9dff"
TEXT = "#e6edf3"
MUTED = "#8b97a5"
OK = "#3fb950"
ERR = "#f85149"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Resizer Pro")
        self.geometry("980x640")
        self.minsize(900, 580)
        self.configure(bg=BG)

        self.files = []          # list of full paths
        self.running = False

        self.width_var = tk.StringVar(value="1000")
        self.height_var = tk.StringVar(value="1000")
        self.keep_ratio = tk.BooleanVar(value=False)
        self.resample_var = tk.StringVar(value="Lanczos (best quality)")
        self.out_var = tk.StringVar(value="")
        self.same_name = tk.BooleanVar(value=True)
        self.suffix_var = tk.StringVar(value="_resized")
        self.status_var = tk.StringVar(value="Ready")

        self._style()
        self._build()

    # ------------------------------------------------------------------ style
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, fieldbackground=CARD,
                    font=("Segoe UI", 10))
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("Card.TLabelframe", background=PANEL, foreground=TEXT,
                    bordercolor=CARD, relief="solid")
        s.configure("Card.TLabelframe.Label", background=PANEL, foreground=ACCENT,
                    font=("Segoe UI Semibold", 10))
        s.configure("TLabel", background=PANEL, foreground=TEXT)
        s.configure("Muted.TLabel", background=PANEL, foreground=MUTED)
        s.configure("Title.TLabel", background=BG, foreground=TEXT,
                    font=("Segoe UI Semibold", 18))
        s.configure("Sub.TLabel", background=BG, foreground=MUTED)
        s.configure("Status.TLabel", background=BG, foreground=MUTED)
        s.configure("TCheckbutton", background=PANEL, foreground=TEXT)
        s.map("TCheckbutton", background=[("active", PANEL)])
        s.configure("TEntry", fieldbackground=CARD, foreground=TEXT,
                    bordercolor=CARD, insertcolor=TEXT, padding=6)
        s.configure("TCombobox", fieldbackground=CARD, background=CARD,
                    foreground=TEXT, arrowcolor=TEXT, padding=5)
        s.map("TCombobox", fieldbackground=[("readonly", CARD)],
              foreground=[("readonly", TEXT)])
        s.configure("TButton", background=CARD, foreground=TEXT, padding=(12, 7),
                    borderwidth=0)
        s.map("TButton", background=[("active", "#2d3641")])
        s.configure("Accent.TButton", background=ACCENT, foreground="white",
                    font=("Segoe UI Semibold", 11), padding=(16, 10))
        s.map("Accent.TButton", background=[("active", ACCENT_HOVER),
                                            ("disabled", "#2a3a52")])
        s.configure("Preset.TButton", padding=(8, 4), font=("Segoe UI", 9))
        s.configure("Treeview", background=CARD, fieldbackground=CARD,
                    foreground=TEXT, rowheight=28, borderwidth=0)
        s.configure("Treeview.Heading", background=PANEL, foreground=MUTED,
                    font=("Segoe UI Semibold", 9), borderwidth=0)
        s.map("Treeview", background=[("selected", ACCENT)])
        s.configure("Horizontal.TProgressbar", troughcolor=CARD,
                    background=ACCENT, bordercolor=CARD, thickness=10)
        self.option_add("*TCombobox*Listbox.background", CARD)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)

    # ----------------------------------------------------------------- layout
    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(16, 8))
        ttk.Label(header, text="Image Resizer Pro", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Bulk resize images to any custom resolution",
                  style="Sub.TLabel").pack(anchor="w")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=20, pady=6)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # ---------- left: file list ----------
        left = ttk.LabelFrame(body, text="  Images  ", style="Card.TLabelframe", padding=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        bar = ttk.Frame(left, style="Panel.TFrame")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(bar, text="＋ Add Files", command=self.add_files).pack(side="left")
        ttk.Button(bar, text="📁 Add Folder", command=self.add_folder).pack(side="left", padx=6)
        ttk.Button(bar, text="Remove", command=self.remove_selected).pack(side="left")
        ttk.Button(bar, text="Clear", command=self.clear_files).pack(side="left", padx=6)

        cols = ("name", "size", "status")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("name", text="File name")
        self.tree.heading("size", text="Original size")
        self.tree.heading("status", text="Status")
        self.tree.column("name", width=280, anchor="w")
        self.tree.column("size", width=110, anchor="center")
        self.tree.column("status", width=110, anchor="center")
        self.tree.tag_configure("ok", foreground=OK)
        self.tree.tag_configure("err", foreground=ERR)
        self.tree.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)

        self.count_lbl = ttk.Label(left, text="0 images", style="Muted.TLabel")
        self.count_lbl.grid(row=2, column=0, sticky="w", pady=(8, 0))

        # ---------- right: settings ----------
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        # resolution
        res = ttk.LabelFrame(right, text="  Resolution  ", style="Card.TLabelframe", padding=12)
        res.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        row = ttk.Frame(res, style="Panel.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="Width").grid(row=0, column=0, sticky="w")
        ttk.Label(row, text="Height").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(row, textvariable=self.width_var, width=9, justify="center").grid(row=1, column=0)
        ttk.Label(row, text="×").grid(row=1, column=1, padx=8)
        ttk.Entry(row, textvariable=self.height_var, width=9, justify="center").grid(row=1, column=2, padx=(12, 0))
        ttk.Label(row, text="px", style="Muted.TLabel").grid(row=1, column=3, padx=6)

        pr = ttk.Frame(res, style="Panel.TFrame")
        pr.pack(fill="x", pady=(10, 0))
        ttk.Label(pr, text="Presets:", style="Muted.TLabel").pack(side="left", padx=(0, 6))
        for p in PRESETS:
            ttk.Button(pr, text=str(p), style="Preset.TButton",
                       command=lambda v=p: self.set_preset(v)).pack(side="left", padx=2)

        ttk.Checkbutton(res, text="Keep aspect ratio (fit inside width × height)",
                        variable=self.keep_ratio).pack(anchor="w", pady=(10, 0))

        ttk.Label(res, text="Quality / method").pack(anchor="w", pady=(10, 2))
        ttk.Combobox(res, textvariable=self.resample_var, values=list(RESAMPLE),
                     state="readonly").pack(fill="x")

        # output
        out = ttk.LabelFrame(right, text="  Output  ", style="Card.TLabelframe", padding=12)
        out.grid(row=1, column=0, sticky="ew")
        ttk.Label(out, text="Output folder").pack(anchor="w")
        orow = ttk.Frame(out, style="Panel.TFrame")
        orow.pack(fill="x", pady=(2, 8))
        ttk.Entry(orow, textvariable=self.out_var).pack(side="left", fill="x", expand=True)
        ttk.Button(orow, text="Browse…", command=self.pick_output).pack(side="left", padx=(6, 0))

        ttk.Checkbutton(out, text="Keep original file name exactly",
                        variable=self.same_name, command=self._toggle_suffix).pack(anchor="w")
        srow = ttk.Frame(out, style="Panel.TFrame")
        srow.pack(fill="x", pady=(6, 0))
        ttk.Label(srow, text="Suffix if not keeping name:", style="Muted.TLabel").pack(side="left")
        self.suffix_entry = ttk.Entry(srow, textvariable=self.suffix_var, width=14, state="disabled")
        self.suffix_entry.pack(side="left", padx=6)

        # footer
        foot = ttk.Frame(self)
        foot.pack(fill="x", padx=20, pady=(8, 14))
        foot.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(foot, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        self.start_btn = ttk.Button(foot, text="▶  Start Resize", style="Accent.TButton",
                                    command=self.start)
        self.start_btn.grid(row=0, column=1, rowspan=2)
        ttk.Label(foot, textvariable=self.status_var, style="Status.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 0))

    # ---------------------------------------------------------------- actions
    def set_preset(self, v):
        self.width_var.set(str(v))
        self.height_var.set(str(v))

    def _toggle_suffix(self):
        self.suffix_entry.configure(state="disabled" if self.same_name.get() else "normal")

    def _add_paths(self, paths):
        existing = set(self.files)
        for p in paths:
            if p in existing or not p.lower().endswith(SUPPORTED):
                continue
            try:
                with Image.open(p) as im:
                    size = f"{im.width} × {im.height}"
            except Exception:
                size = "?"
            self.files.append(p)
            self.tree.insert("", "end", iid=p, values=(os.path.basename(p), size, "Pending"))
            existing.add(p)
        self._update_count()

    def add_files(self):
        exts = " ".join(f"*{e}" for e in SUPPORTED)
        paths = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[("Images", exts), ("All files", "*.*")])
        if paths:
            self._add_paths(paths)
            if not self.out_var.get():
                self.out_var.set(os.path.join(os.path.dirname(paths[0]), "resized"))

    def add_folder(self):
        d = filedialog.askdirectory(title="Select folder with images")
        if not d:
            return
        paths = [os.path.join(d, f) for f in sorted(os.listdir(d))]
        self._add_paths([p for p in paths if os.path.isfile(p)])
        if not self.out_var.get():
            self.out_var.set(os.path.join(d, "resized"))

    def remove_selected(self):
        for iid in self.tree.selection():
            self.tree.delete(iid)
            self.files.remove(iid)
        self._update_count()

    def clear_files(self):
        if self.running:
            return
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        self.progress["value"] = 0
        self._update_count()

    def pick_output(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.out_var.set(d)

    def _update_count(self):
        n = len(self.files)
        self.count_lbl.configure(text=f"{n} image{'s' if n != 1 else ''}")

    # ---------------------------------------------------------------- resize
    def start(self):
        if self.running:
            return
        if not self.files:
            messagebox.showwarning("No images", "Please add at least one image.")
            return
        try:
            w, h = int(self.width_var.get()), int(self.height_var.get())
            if not (1 <= w <= 20000 and 1 <= h <= 20000):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid size", "Width and height must be whole numbers (1–20000).")
            return
        out = self.out_var.get().strip()
        if not out:
            messagebox.showwarning("Output folder", "Please select an output folder.")
            return
        try:
            os.makedirs(out, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Output folder", f"Cannot create folder:\n{e}")
            return

        # overwrite safety
        if self.same_name.get():
            clash = [p for p in self.files
                     if os.path.normcase(os.path.dirname(p)) == os.path.normcase(os.path.abspath(out))]
            if clash and not messagebox.askyesno(
                    "Overwrite originals?",
                    f"{len(clash)} file(s) are in the output folder and will be OVERWRITTEN.\n\nContinue?"):
                return

        self.running = True
        self.start_btn.configure(state="disabled")
        self.progress.configure(maximum=len(self.files), value=0)
        for iid in self.tree.get_children():
            self.tree.set(iid, "status", "Pending")
            self.tree.item(iid, tags=())
        threading.Thread(target=self._worker,
                         args=(list(self.files), w, h, out), daemon=True).start()

    def _worker(self, files, w, h, out):
        method = RESAMPLE[self.resample_var.get()]
        keep = self.keep_ratio.get()
        same = self.same_name.get()
        suffix = self.suffix_var.get()
        ok = fail = 0
        for i, path in enumerate(files, 1):
            try:
                with Image.open(path) as im:
                    im.load()
                    if keep:
                        r = min(w / im.width, h / im.height)
                        size = (max(1, round(im.width * r)), max(1, round(im.height * r)))
                    else:
                        size = (w, h)
                    res = im.resize(size, method)
                    base, ext = os.path.splitext(os.path.basename(path))
                    name = base + ext if same else base + suffix + ext
                    dest = os.path.join(out, name)
                    if ext.lower() in (".jpg", ".jpeg") and res.mode != "RGB":
                        res = res.convert("RGB")
                    res.save(dest)
                ok += 1
                self.after(0, self._mark, path, "✔ Done", "ok", i, len(files))
            except Exception as e:
                fail += 1
                self.after(0, self._mark, path, "✖ Failed", "err", i, len(files))
                print("Error:", path, e)
        self.after(0, self._finish, ok, fail, out)

    def _mark(self, path, text, tag, i, total):
        if self.tree.exists(path):
            self.tree.set(path, "status", text)
            self.tree.item(path, tags=(tag,))
        self.progress["value"] = i
        self.status_var.set(f"Processing {i} / {total}…")

    def _finish(self, ok, fail, out):
        self.running = False
        self.start_btn.configure(state="normal")
        self.status_var.set(f"Finished — {ok} done, {fail} failed")
        if messagebox.askyesno("Completed",
                               f"{ok} image(s) resized, {fail} failed.\n\nOpen output folder?"):
            try:
                os.startfile(out)  # Windows
            except AttributeError:
                pass


if __name__ == "__main__":
    App().mainloop()
