import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from pathlib import Path
import script_generation_func
import inspect
import ctypes
from ctypes import wintypes

REQUIRED_INPUT_COLS = ["date","ut","durn","star_mag","mag_drop","star_no",
                       "asteroid","alt","az","probability","ra","dec"]
DISPLAY_COLS = ["date","ut_str","asteroid","star_mag","durn","probability","mag_drop","altaz"]

HEADER_LABELS = {
    "date": "Date",
    "ut_str": "UTC",
    "asteroid": "Asteroid",
    "star_mag": "Star Mag",
    "durn": "Duration",
    "probability": "Prob",
    "mag_drop": "Mag Drop",
    "altaz": "Alt Az",
}
def mark_close_events(df_slice: pd.DataFrame, time_col="utc_dt", window_sec=240) -> pd.DataFrame:
    if df_slice.empty:
        out = df_slice.copy()
        out["_close4"] = False
        return out

    out = df_slice.sort_values(time_col, kind="mergesort").copy()
    dt = out[time_col]

    dprev = dt.diff().dt.total_seconds()
    dnext = dt.shift(-1).diff().dt.total_seconds()

    close_prev = (dprev <= window_sec)
    close_next = (dnext.abs() <= window_sec)

    out["_close4"] = close_prev.fillna(False) | close_next.fillna(False)
    return out

class DualTableApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # screen_width = self.winfo_screenwidth()
        # screen_height = self.winfo_screenheight()
        self.title("Occultation Script GUI")
        self.maximize_keep_taskbar()

        self.events_fullpath = ""
        self.events_path = tk.StringVar()
        self.pre_path = tk.StringVar(value="pre_path_general.txt")
        self.post_path = tk.StringVar(value="post_path_general.txt")
        self.out_path = tk.StringVar()
        self.day_var = tk.IntVar(value=1)
        self.day_text = tk.StringVar(value="Day: —")

        self.telescope = tk.StringVar(value="Hubble")
        self.camera = tk.StringVar(value="zwo")

        self.df_all = None
        self._load_prepost_paths()
        self._build_ui()

    def _configure_row_tags(self, tree):
        tree.tag_configure("close4", background="#edd28c") #change colors as needed! shows up different on different screens
        tree.tag_configure("highprob",  background="#8eed8c")
    def maximize_keep_taskbar(self):
        def _do():
            # 1) Try the normal maximize approaches
            try:
                self.state("zoomed")
                return
            except Exception:
                pass
            try:
                self.attributes("-zoomed", True)
                return
            except Exception:
                pass

            # 2) Windows fallback: size to "work area" (screen minus taskbar)
            try:
                SPI_GETWORKAREA = 0x0030
                rect = wintypes.RECT()
                ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)

                x = rect.left
                y = rect.top
                w = rect.right - rect.left
                h = rect.bottom - rect.top

                self.geometry(f"{w}x{h}+{x}+{y}")
            except Exception:
                # last resort: just use screen size
                self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.after(0, _do)

    def _app_dir(self) -> Path:
        return Path(__file__).resolve().parent

    def _settings_path(self) -> Path:
        return self._app_dir() / "prepost_paths.txt"

    def _clean_path_text(self, value: str) -> str:
        return value.strip().strip('"').strip("'")

    def _resolve_path(self, value: str) -> Path:
        cleaned = self._clean_path_text(value)
        path = Path(cleaned).expanduser()
        if not path.is_absolute():
            path = self._app_dir() / path
        return path.resolve(strict=False)

    def _valid_txt_file(self, value: str) -> bool:
        path = self._resolve_path(value)
        return path.is_file() and path.suffix.lower() == ".txt"

    def _show_prepost_error(self, pre_valid: bool, post_valid: bool):
        if not pre_valid and not post_valid:
            msg = "Invalid pre and post files."
        elif not pre_valid:
            msg = "Invalid pre file."
        else:
            msg = "Invalid post file."
        messagebox.showerror("Invalid file", msg)

    def _load_prepost_paths(self):
        settings = self._settings_path()
        default_pre = "pre_path_general.txt"
        default_post = "post_path_general.txt"

        if not settings.exists():
            settings.write_text(f"{default_pre}\n{default_post}\n", encoding="utf-8")
            self.pre_path.set(str(self._app_dir() / default_pre))
            self.post_path.set(str(self._app_dir() / default_post))
            return

        lines = settings.read_text(encoding="utf-8", errors="replace").splitlines()
        pre = lines[0].strip() if len(lines) > 0 else default_pre
        post = lines[1].strip() if len(lines) > 1 else default_post

        pre_path = self._resolve_path(pre)
        post_path = self._resolve_path(post)

        self.pre_path.set(str(pre_path))
        self.post_path.set(str(post_path))

    def _save_prepost_paths(self):
        settings = self._settings_path()
        pre = self.pre_path.get().strip()
        post = self.post_path.get().strip()

        # store absolute paths
        pre_abs = str(self._resolve_path(pre)) if pre else ""
        post_abs = str(self._resolve_path(post)) if post else ""

        settings.write_text(pre_abs + "\n" + post_abs + "\n", encoding="utf-8")

    def _camera_name_for_filename(self) -> str:
        camera_names = {"qhy": "QHY", "zwo": "ZWO", "playerone": "PlayerOne"} #CHANGE HERE TO CHANGE CAMERA LIST
        camera_key = self.camera.get().lower().strip()
        return camera_names.get(camera_key, self.camera.get().strip())

    def _telescope_name_for_filename(self) -> str:
        telescope_names = {
            "hubble": "Hubble",
            "hubble-24": "Hubble",
            "c14": "C14",
            "c-14": "C14",
            "c11": "C11",
            "c-11": "C11",
        } #CHANGE HERE TO UPDATE TELESCOPES
        telescope_key = self.telescope.get().lower().strip()
        return telescope_names.get(telescope_key, self.telescope.get().replace("-", "").strip())

    def _refresh_output_path(self):
        if not self.events_fullpath:
            return

        date_part = Path(self.events_fullpath).name[:8]
        script_dir = Path(inspect.getfile(script_generation_func)).resolve().parent
        filename = f"{date_part}_{self._camera_name_for_filename()}_{self._telescope_name_for_filename()}_script.scs"
        self.out_path.set(str(script_dir / filename))

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Button(top, text="Upload events.txt", command=self.pick_events).grid(row=0, column=0, padx=6)
        ttk.Label(top, textvariable=self.events_path, width=50).grid(row=0, column=1, sticky="w")
        ttk.Label(top, textvariable=self.day_text, width=15).grid(row=0, column=2, sticky="w", padx=6)

        ttk.Label(top, text="pre path:").grid(row=1, column=0, sticky="e")
        ttk.Entry(top, textvariable=self.pre_path, width=40).grid(row=1, column=1, sticky="we", padx=(8, 2))
        ttk.Button(top, text="Browse", command=self.pick_pre).grid(row=1, column=2, padx=(2, 0))

        ttk.Label(top, text="post path:").grid(row=2, column=0, sticky="e")
        ttk.Entry(top, textvariable=self.post_path, width=40).grid(row=2, column=1, sticky="we", padx=(8, 2))
        ttk.Button(top, text="Browse", command=self.pick_post).grid(row=2, column=2, padx=(2, 0))

        ttk.Label(top, text="output .scs path:").grid(row=3, column=0, sticky="e")
        ttk.Entry(top, textvariable=self.out_path, width=40).grid(row=3, column=1, sticky="we", padx=(8, 2))
        ttk.Button(top, text="Browse", command=self.pick_out).grid(row=3, column=2, padx=(2, 0))


        tel_frame = ttk.LabelFrame(top, text="Telescope")
        tel_frame.grid(row=0, column=3, rowspan=4, padx=12, pady=2, sticky="ns")

        for i, tel in enumerate(["Hubble", "C14", "C11"]): #CHANGE AS TELESCOPES ARE ADDED
            ttk.Radiobutton(
                tel_frame, text=tel, value=tel, variable=self.telescope,
                command=self.on_telescope_changed
            ).grid(row=i, column=0, sticky="w", padx=8, pady=4)

        camera_frame = ttk.LabelFrame(top, text="Camera")
        camera_frame.grid(row=0, column=4, rowspan=4, padx=12, pady=2, sticky="ns")

        for i, (label, value) in enumerate([("QHY", "qhy"), ("ZWO", "zwo"), ("PlayerOne", "playerone")]): #CHANGE HERE TO UPDATE CAMERAS
            ttk.Radiobutton(
                camera_frame, text=label, value=value, variable=self.camera,
                command=self.on_camera_changed
            ).grid(row=i, column=0, sticky="w", padx=8, pady=4)

        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, padx=10, pady=8)
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(2, weight=1)
        mid.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(mid, text="Accepted")
        right = ttk.LabelFrame(mid, text="Rejected")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        left.rowconfigure(0, weight=1); left.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1); right.columnconfigure(0, weight=1)

        self.good_tree = self._make_tree(left)
        self.bad_tree  = self._make_tree(right)
        self._configure_row_tags(self.good_tree)
        self._configure_row_tags(self.bad_tree)

        self.active_tree = self.good_tree

        def _set_active(tree):
            self.active_tree = tree


        self.good_tree.bind("<Button-1>", lambda e: _set_active(self.good_tree))
        self.bad_tree.bind("<Button-1>",  lambda e: _set_active(self.bad_tree))
        self.good_tree.bind("<FocusIn>", lambda e: setattr(self, "active_tree", self.good_tree))
        self.bad_tree.bind("<FocusIn>",  lambda e: setattr(self, "active_tree", self.bad_tree))
        self.good_tree.bind("<<TreeviewSelect>>", lambda e: setattr(self, "active_tree", self.good_tree))
        self.bad_tree.bind("<<TreeviewSelect>>",  lambda e: setattr(self, "active_tree", self.bad_tree))


        # space moves between tables; enter moves down
        for i in (self.good_tree, self.bad_tree):
            i.bind("<space>", self._on_space)
            i.bind("<Return>", self._on_enter)

        btns = ttk.Frame(mid)
        btns.grid(row=0, column=1, sticky="ns")
        ttk.Button(btns, text="← Move to Accepted", command=self.move_to_accepted).pack(pady=(180, 10))
        ttk.Button(btns, text="→ Move to Rejected", command=self.move_to_rejected).pack(pady=10)

        # bottom generate
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bottom, text="Generate SCS from Accepted", command=self.on_generate).pack(side="right")

    def _on_space(self, event):
        tree = event.widget
        self.active_tree = tree
        if tree == self.good_tree:
            self.move_to_rejected()
        else:
            self.move_to_accepted()
        return "break"

    def _on_enter(self, event):
        tree = event.widget
        self.active_tree = tree
        self._move_selection_down(tree)
        return "break"


    def _make_tree(self, parent):
        tree = ttk.Treeview(parent, columns=DISPLAY_COLS, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        for col in DISPLAY_COLS:
            tree.heading(col, text=HEADER_LABELS.get(col, col))
            tree.column(col, width=120, stretch=tk.YES, anchor="center")

        return tree
    def _select_first_event(self, tree: ttk.Treeview):
        kids = tree.get_children()
        if not kids:
            return
        tree.selection_set(kids[0])
        tree.focus(kids[0])
        tree.see(kids[0])

    def _select_next_after_move(self, src_tree, accepted_value: bool):
        kids_before = list(src_tree.get_children())
        moved = list(src_tree.selection())
        if not moved:
            return

        try:
            anchor_idx = max(kids_before.index(i) for i in moved if i in kids_before)
        except ValueError:
            anchor_idx = 0

        self._set_acceptance(moved, accepted_value)

        kids_after = list(src_tree.get_children())
        if not kids_after:
            return

        pick_idx = min(anchor_idx, len(kids_after) - 1)
        pick = kids_after[pick_idx]

        src_tree.selection_set(pick)
        src_tree.focus(pick)
        src_tree.see(pick)
        src_tree.focus_set()


    def _move_selection_down(self, tree: ttk.Treeview):
        kids = list(tree.get_children())
        if not kids:
            return

        sel = list(tree.selection())
        if not sel:
            self._select_first_event(tree)
            return

        try:
            idxs = [kids.index(i) for i in sel if i in kids]
        except ValueError:
            idxs = []
        if not idxs:
            self._select_first_event(tree)
            return

        idx = max(idxs)
        nxt = idx + 1
        if nxt >= len(kids):
            nxt = len(kids) - 1

        pick = kids[nxt]
        tree.selection_set(pick)
        tree.focus(pick)
        tree.see(pick)


    def _apply_camera_to_prepost_files(self, show_errors=False):
        pre = self.pre_path.get().strip()
        post = self.post_path.get().strip()
        if not pre or not post:
            return

        pre_path = self._resolve_path(pre)
        post_path = self._resolve_path(post)

        pre_valid = self._valid_txt_file(str(pre_path))
        post_valid = self._valid_txt_file(str(post_path))
        if not pre_valid or not post_valid:
            if show_errors:
                self._show_prepost_error(pre_valid, post_valid)
            return

        self.pre_path.set(str(pre_path))
        self.post_path.set(str(post_path))

        try:
            script_generation_func.update_prepost_files_for_camera(str(pre_path), str(post_path), self.camera.get())
        except Exception as e:
            if show_errors:
                messagebox.showerror("Camera template update error", str(e))

    def on_camera_changed(self):
        self._apply_camera_to_prepost_files(show_errors=False)
        self._refresh_output_path()

    def pick_events(self):
        p = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not p:
            return
        self.events_fullpath = p
        self.events_path.set(Path(p).name)
        d = script_generation_func.infer_day_from_filename(p)
        self.day_var.set(d)
        self.day_text.set(f"Day: {d:02d}")
        if d is None:
            messagebox.showerror("Bad filename", "Expected filename like YYYYMMDD_events.txt")
            return
        self.day_var.set(d)

        self._refresh_output_path()
        self.load_events_into_tables()

    def pick_pre(self):
        p = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if p:
            self.pre_path.set(str(self._resolve_path(p)))
            self._save_prepost_paths()
            self._apply_camera_to_prepost_files(show_errors=False)

    def pick_post(self):
        p = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if p:
            self.post_path.set(str(self._resolve_path(p)))
            self._save_prepost_paths()
            self._apply_camera_to_prepost_files(show_errors=False)

    def pick_out(self):
        p = filedialog.asksaveasfilename(defaultextension=".scs", filetypes=[("SCS files", "*.scs"), ("All files", "*.*")])
        if p:
            self.out_path.set(p)

    def load_events_into_tables(self):
        path = self.events_fullpath
        if not path:
            return

        try:
            df = script_generation_func.events_to_dataframe(path)
        except Exception as e:
            messagebox.showerror("Parse error", str(e))
            return


        missing = [c for c in REQUIRED_INPUT_COLS if c not in df.columns]
        if missing:
            messagebox.showerror("DF missing columns", f"Missing columns: {missing}")
            return

        df["altaz"] = df.apply(lambda r: f"{int(r['alt']):>3} {int(r['az']):>3}" if pd.notna(r["alt"]) and pd.notna(r["az"]) else "", axis=1)
        df["utc_dt"] = pd.to_datetime(df["utc_dt"], errors="coerce")
        df["ut_str"] = df["utc_dt"].dt.strftime("%H:%M:%S")
        day_filter = int(self.day_var.get())
        df = df[script_generation_func.night_window_filter(df, day_filter)].copy()
        df["_uid"] = range(len(df))
        df["accepted"] = script_generation_func.telescope_accept_mask(df, self.telescope.get())

        df = df.sort_values("utc_dt", kind="mergesort").reset_index(drop=True)
        self.df_all = df

        self.render_tables()

    def on_telescope_changed(self):
        self._refresh_output_path()
        if self.df_all is None:
            return

        self.df_all["accepted"] = script_generation_func.telescope_accept_mask(self.df_all, self.telescope.get())
        self.df_all = self.df_all.sort_values("utc_dt", kind="mergesort").reset_index(drop=True)
        self.render_tables()

    def render_tables(self):
        if self.df_all is None:
            return

        good = self.df_all[self.df_all["accepted"] == True]
        bad  = self.df_all[self.df_all["accepted"] == False]

        good = mark_close_events(good, time_col="utc_dt", window_sec=240)
        bad  = mark_close_events(bad,  time_col="utc_dt", window_sec=240)

        self._fill_tree(self.good_tree, good)
        self._fill_tree(self.bad_tree, bad)

    def _fill_tree(self, tree, df_slice):
        tree.delete(*tree.get_children())
        for _, row in df_slice.iterrows():
            iid = str(int(row["_uid"]))
            values = [row[c] for c in DISPLAY_COLS]
            prob = row.get("probability", 0)
            try:
                prob_val = float(prob)
            except Exception:
                prob_val = 0.0
            close4 = bool(row.get("_close4", False))

            if close4:
                tags = ("close4",)
            elif prob_val >= 15:
                tags = ("highprob",)
            else:
                tags = ()
            tree.insert("", "end", iid=iid, values=values, tags=tags)

    def _set_acceptance(self, uids, accepted: bool):
        if self.df_all is None or not uids:
            return
        uid_ints = [int(x) for x in uids]
        self.df_all.loc[self.df_all["_uid"].isin(uid_ints), "accepted"] = accepted
        self.df_all = self.df_all.sort_values("utc_dt", kind="mergesort").reset_index(drop=True)
        self.render_tables()

    def move_to_accepted(self):
        self.active_tree = self.bad_tree
        self._select_next_after_move(self.bad_tree, True)


    def move_to_rejected(self):
        self.active_tree = self.good_tree
        self._select_next_after_move(self.good_tree, False)

    def on_generate(self):
        if self.df_all is None:
            messagebox.showerror("No data", "Upload an events.txt file first.")
            return
        pre_path = self._resolve_path(self.pre_path.get())
        post_path = self._resolve_path(self.post_path.get())
        pre_valid = self._valid_txt_file(str(pre_path))
        post_valid = self._valid_txt_file(str(post_path))
        if not pre_valid or not post_valid:
            self._show_prepost_error(pre_valid, post_valid)
            return
        self.pre_path.set(str(pre_path))
        self.post_path.set(str(post_path))
        self._apply_camera_to_prepost_files(show_errors=True)
        if not self.out_path.get().strip():
            messagebox.showerror("Missing output", "Select an output .scs path.")
            return

        df_good = self.df_all[self.df_all["accepted"] == True].copy()
        if df_good.empty:
            messagebox.showerror("No accepted events", "Accepted table is empty.")
            return

        NEEDED = ["date","ut","durn","star_mag","mag_drop","star_no",
                  "asteroid","alt","az","probability","ra","dec"]

        records = df_good[NEEDED].to_dict("records")
        try:
            events = [script_generation_func.extract_event(rec) for rec in records]  # <-- adapt event_from_row to accept dict
            script_generation_func.generate_scs(events, self.out_path.get(), str(pre_path), str(post_path), self.camera.get())
        except Exception as e:
            messagebox.showerror("Generate error", str(e))
            return

        messagebox.showinfo("Done", f"Generated:\n{self.out_path.get()}")

if __name__ == "__main__":
    app = DualTableApp()
    app.mainloop()