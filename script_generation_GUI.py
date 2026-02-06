import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from pathlib import Path
import script_generation_func

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
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.title("Occultation Script GUI")
        self.geometry(f"{screen_width}x{screen_height}")

        self.events_path = tk.StringVar()
        self.pre_path = tk.StringVar(value="pre174.txt")
        self.post_path = tk.StringVar(value="post571.txt")
        self.out_path = tk.StringVar()

        self.telescope = tk.StringVar(value="c14")

        self.df_all = None
        self._build_ui()

    def _configure_row_tags(self, tree):
        tree.tag_configure("close4", background="#fff4cc")
        tree.tag_configure("highprob",  background="#d4e8d3")

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Button(top, text="Upload events.txt", command=self.pick_events).grid(row=0, column=0, padx=6)
        ttk.Label(top, textvariable=self.events_path, width=70).grid(row=0, column=1, sticky="w")

        ttk.Label(top, text="pre path:").grid(row=1, column=0, sticky="e")
        ttk.Entry(top, textvariable=self.pre_path, width=40).grid(row=1, column=1, sticky="we", padx=(8, 2))
        ttk.Button(top, text="Browse", command=self.pick_pre).grid(row=1, column=2, padx=(2, 0))

        ttk.Label(top, text="post path:").grid(row=2, column=0, sticky="e")
        ttk.Entry(top, textvariable=self.post_path, width=40).grid(row=2, column=1, sticky="we",padx=(8, 2))
        ttk.Button(top, text="Browse", command=self.pick_post).grid(row=2, column=2, padx=(2, 0))

        ttk.Label(top, text="output .scs path:").grid(row=3, column=0, sticky="e")
        ttk.Entry(top, textvariable=self.out_path, width=40).grid(row=3, column=1, sticky="we", padx=(8, 2))
        ttk.Button(top, text="Browse", command=self.pick_out).grid(row=3, column=2, padx=(2, 0))


        tel_frame = ttk.LabelFrame(top, text="Telescope")
        tel_frame.grid(row=0, column=3, rowspan=4, padx=12, pady=2, sticky="ns")

        for i, tel in enumerate(["c11", "c14", "hubble24"]): #CHANGE AS TELESCOPES ARE ADDED
            ttk.Radiobutton(
                tel_frame, text=tel, value=tel, variable=self.telescope,
                command=self.on_telescope_changed
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

        btns = ttk.Frame(mid)
        btns.grid(row=0, column=1, sticky="ns")
        ttk.Button(btns, text="← Move to Accepted", command=self.move_to_accepted).pack(pady=(180, 10))
        ttk.Button(btns, text="→ Move to Rejected", command=self.move_to_rejected).pack(pady=10)

        # bottom generate
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bottom, text="Generate SCS from Accepted", command=self.on_generate).pack(side="right")

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

    def pick_events(self):
        p = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not p:
            return
        self.events_path.set(p)

        # automatic path name
        stem = Path(p).name[:8]
        self.out_path.set(str(Path(p).with_name(f"{stem}_174_script.scs")))

        self.load_events_into_tables()

    def pick_pre(self):
        p = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if p:
            self.pre_path.set(p)

    def pick_post(self):
        p = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if p:
            self.post_path.set(p)

    def pick_out(self):
        p = filedialog.asksaveasfilename(defaultextension=".scs", filetypes=[("SCS files", "*.scs"), ("All files", "*.*")])
        if p:
            self.out_path.set(p)

    def load_events_into_tables(self):
        path = self.events_path.get().strip()
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
        df["_uid"] = range(len(df))
        df["accepted"] = script_generation_func.telescope_accept_mask(df, self.telescope.get())

        df = df.sort_values("utc_dt", kind="mergesort").reset_index(drop=True)
        self.df_all = df

        self.render_tables()

    def on_telescope_changed(self):
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
        uids = self.bad_tree.selection()
        self._set_acceptance(uids, True)

    def move_to_rejected(self):
        uids = self.good_tree.selection()
        self._set_acceptance(uids, False)

    def on_generate(self):
        if self.df_all is None:
            messagebox.showerror("No data", "Upload an events.txt file first.")
            return
        if not Path(self.pre_path.get()).exists() or not Path(self.post_path.get()).exists():
            messagebox.showerror("Missing pre/post", "Select valid pre and post files.")
            return
        if not self.out_path.get().strip():
            messagebox.showerror("Missing output", "Select an output .scs path.")
            return

        df_good = self.df_all[self.df_all["accepted"] == True].copy()
        if df_good.empty:
            messagebox.showerror("No accepted events", "Accepted table is empty.")
            return

        records = df_good[DISPLAY_COLS].to_dict("records")
        try:
            events = [script_generation_func.extract_event(rec) for rec in records]  # <-- adapt event_from_row to accept dict
            script_generation_func.generate_scs(events, self.out_path.get(), self.pre_path.get(), self.post_path.get())
        except Exception as e:
            messagebox.showerror("Generate error", str(e))
            return

        messagebox.showinfo("Done", f"Generated:\n{self.out_path.get()}")

if __name__ == "__main__":
    app = DualTableApp()
    app.mainloop()