"""Gwydion Bid Tool — standalone GUI for resolving DKP bids.

Run it:
    python bidtool/bidtool_gui.py

Add items, add each item's bidders + bids, then hit Resolve. With "Validate
against live sheet" ticked it reads the same master spreadsheet the bot uses
(read-only) to confirm each bidder can afford their bid; unticked it just picks
the raw highest bidder so you can compute winners with no credentials.

A headless mode is included for quick checks / scripting:
    python bidtool/bidtool_gui.py resolve mybids.csv            # validate live
    python bidtool/bidtool_gui.py resolve mybids.csv --offline  # no validation
    python bidtool/bidtool_gui.py template blank.csv            # write a template
"""

import os
import sys

# Allow running as a loose script (python bidtool/bidtool_gui.py) by making the
# folder importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bid_io
import bid_history
from bid_resolver import resolve_bids, format_results, collect_winners
from gear_rules import GearRules

POOLS = ["VKP", "GKP", "PKP", "AKP", "RBPPUNOX", "DPKP", "RBPP"]


# ── Shared: turn the GUI/CSV model into resolver input ──────────────────────
def items_to_bids(items):
    """items: list of {item, kp, qty, bids:[{bidder, for_player, amount}]}."""
    flat = []
    for it in items:
        for b in it["bids"]:
            flat.append({
                "item": it["item"], "kp": it["kp"], "qty": it["qty"],
                "bidder": b["bidder"], "for_player": b.get("for_player", ""),
                "amount": b["amount"],
            })
    return flat


def bids_to_items(bids):
    """Inverse of items_to_bids: group flat CSV rows back into items (first-seen
    order), so loading a CSV repopulates the GUI."""
    order, by_key = [], {}
    for b in bids:
        key = " ".join(str(b["item"]).split()).lower()
        if key not in by_key:
            order.append(key)
            by_key[key] = {
                "item": b["item"], "kp": (b.get("kp") or "VKP").upper(),
                "qty": int(b.get("qty") or 1), "bids": [],
            }
        by_key[key]["bids"].append({
            "bidder": b["bidder"],
            "for_player": b.get("for_player", ""),
            "amount": b["amount"],
        })
    return [by_key[k] for k in order]


def build_lookup(validate):
    """Return (lookup_callable_or_None, error_message_or_None)."""
    if not validate:
        return None, None
    try:
        from sheet_reader import SheetReader, SheetUnavailable
    except ImportError as e:
        return None, f"Could not import sheet reader: {e}"
    try:
        reader = SheetReader()
    except Exception as e:  # SheetUnavailable or auth/network failure
        return None, str(e)
    return reader.lookup, None


# ── Headless mode ───────────────────────────────────────────────────────────
def _cli(argv):
    cmd = argv[0]
    if cmd == "template":
        path = argv[1] if len(argv) > 1 else "bids_template.csv"
        bid_io.write_template(path)
        print(f"Wrote template to {path}")
        return 0
    if cmd == "resolve":
        if len(argv) < 2:
            print("usage: resolve <csv> [--offline] [--no-cap] [--commit]")
            return 2
        path = argv[1]
        flags = argv[2:]
        offline = "--offline" in flags
        no_cap = "--no-cap" in flags
        commit = "--commit" in flags
        bids = bid_io.load_csv(path)
        lookup, err = build_lookup(not offline)
        if err and not offline:
            print(f"[!] Live validation unavailable: {err}")
            print("[!] Falling back to offline resolution (no balance/eligibility checks).\n")
        rules = GearRules.load()
        week_counts = None
        if lookup is not None and not no_cap:
            week_counts = bid_history.week_counts()
        resolved = resolve_bids(bids, lookup=lookup, rules=rules, week_counts=week_counts)
        print(format_results(resolved))
        if commit:
            n = bid_history.commit_winners(collect_winners(resolved))
            print(f"\n[committed {n} winning line(s) to {bid_history.HISTORY_FILE}]")
        return 0
    print(f"unknown command: {cmd}")
    return 2


# ── GUI ─────────────────────────────────────────────────────────────────────
def _run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, simpledialog

    class BidApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Gwydion Bid Tool")
            self.geometry("980x560")
            self.items = []          # the model
            self.current_path = None
            self.validate_var = tk.BooleanVar(value=True)
            self._build()
            self._refresh_items()

        # ----- layout -----
        def _build(self):
            top = ttk.Frame(self, padding=6)
            top.pack(fill="x")
            ttk.Button(top, text="New", command=self.new).pack(side="left")
            ttk.Button(top, text="Open CSV…", command=self.open_csv).pack(side="left", padx=4)
            ttk.Button(top, text="Save CSV…", command=self.save_csv).pack(side="left")
            ttk.Checkbutton(top, text="Validate against live sheet",
                            variable=self.validate_var).pack(side="left", padx=16)
            ttk.Button(top, text="Resolve ▶", command=self.resolve).pack(side="right")

            panes = ttk.Panedwindow(self, orient="horizontal")
            panes.pack(fill="both", expand=True, padx=6, pady=6)

            # Items pane
            left = ttk.Frame(panes)
            ttk.Label(left, text="Items").pack(anchor="w")
            self.items_tv = ttk.Treeview(left, columns=("kp", "qty"), height=16)
            self.items_tv.heading("#0", text="Item")
            self.items_tv.heading("kp", text="KP")
            self.items_tv.heading("qty", text="Qty")
            self.items_tv.column("#0", width=260)
            self.items_tv.column("kp", width=80, anchor="center")
            self.items_tv.column("qty", width=50, anchor="center")
            self.items_tv.pack(fill="both", expand=True)
            self.items_tv.bind("<<TreeviewSelect>>", lambda e: self._refresh_bids())
            ib = ttk.Frame(left)
            ib.pack(fill="x", pady=4)
            ttk.Button(ib, text="Add item", command=self.add_item).pack(side="left")
            ttk.Button(ib, text="Edit", command=self.edit_item).pack(side="left", padx=4)
            ttk.Button(ib, text="Remove", command=self.remove_item).pack(side="left")
            panes.add(left, weight=1)

            # Bids pane
            right = ttk.Frame(panes)
            ttk.Label(right, text="Bids for selected item").pack(anchor="w")
            self.bids_tv = ttk.Treeview(right, columns=("for", "amount"), height=16)
            self.bids_tv.heading("#0", text="Bidder")
            self.bids_tv.heading("for", text="For (recipient)")
            self.bids_tv.heading("amount", text="Amount")
            self.bids_tv.column("#0", width=180)
            self.bids_tv.column("for", width=160)
            self.bids_tv.column("amount", width=90, anchor="e")
            self.bids_tv.pack(fill="both", expand=True)
            bb = ttk.Frame(right)
            bb.pack(fill="x", pady=4)
            ttk.Button(bb, text="Add bid", command=self.add_bid).pack(side="left")
            ttk.Button(bb, text="Edit", command=self.edit_bid).pack(side="left", padx=4)
            ttk.Button(bb, text="Remove", command=self.remove_bid).pack(side="left")
            panes.add(right, weight=1)

        # ----- helpers -----
        def _sel_item_index(self):
            sel = self.items_tv.selection()
            if not sel:
                return None
            return int(sel[0])

        def _refresh_items(self):
            self.items_tv.delete(*self.items_tv.get_children())
            for i, it in enumerate(self.items):
                self.items_tv.insert("", "end", iid=str(i), text=it["item"],
                                     values=(it["kp"], it["qty"]))
            self._refresh_bids()

        def _refresh_bids(self):
            self.bids_tv.delete(*self.bids_tv.get_children())
            idx = self._sel_item_index()
            if idx is None:
                return
            for j, b in enumerate(self.items[idx]["bids"]):
                self.bids_tv.insert("", "end", iid=str(j), text=b["bidder"],
                                    values=(b.get("for_player", ""), b["amount"]))

        # ----- item ops -----
        def add_item(self):
            data = _item_dialog(self, "Add item")
            if data:
                data["bids"] = []
                self.items.append(data)
                self._refresh_items()
                self.items_tv.selection_set(str(len(self.items) - 1))

        def edit_item(self):
            idx = self._sel_item_index()
            if idx is None:
                return
            data = _item_dialog(self, "Edit item", self.items[idx])
            if data:
                self.items[idx].update(data)
                self._refresh_items()
                self.items_tv.selection_set(str(idx))

        def remove_item(self):
            idx = self._sel_item_index()
            if idx is None:
                return
            del self.items[idx]
            self._refresh_items()

        # ----- bid ops -----
        def add_bid(self):
            idx = self._sel_item_index()
            if idx is None:
                messagebox.showinfo("No item", "Select an item first.")
                return
            data = _bid_dialog(self, "Add bid")
            if data:
                self.items[idx]["bids"].append(data)
                self._refresh_bids()

        def edit_bid(self):
            idx = self._sel_item_index()
            if idx is None:
                return
            sel = self.bids_tv.selection()
            if not sel:
                return
            j = int(sel[0])
            data = _bid_dialog(self, "Edit bid", self.items[idx]["bids"][j])
            if data:
                self.items[idx]["bids"][j] = data
                self._refresh_bids()

        def remove_bid(self):
            idx = self._sel_item_index()
            if idx is None:
                return
            sel = self.bids_tv.selection()
            if not sel:
                return
            del self.items[idx]["bids"][int(sel[0])]
            self._refresh_bids()

        # ----- file ops -----
        def new(self):
            if self.items and not messagebox.askyesno("New", "Discard current bids?"):
                return
            self.items = []
            self.current_path = None
            self._refresh_items()

        def open_csv(self):
            path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*.*")])
            if not path:
                return
            try:
                bids = bid_io.load_csv(path)
            except Exception as e:
                messagebox.showerror("Open failed", str(e))
                return
            self.items = bids_to_items(bids)
            self.current_path = path
            self._refresh_items()

        def save_csv(self):
            path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV", "*.csv")])
            if not path:
                return
            bid_io.save_csv(path, items_to_bids(self.items))
            self.current_path = path
            messagebox.showinfo("Saved", f"Saved {len(items_to_bids(self.items))} bids to\n{path}")

        # ----- resolve -----
        def resolve(self):
            if not self.items:
                messagebox.showinfo("Nothing to resolve", "Add some items and bids first.")
                return
            lookup, err = build_lookup(self.validate_var.get())
            if err and self.validate_var.get():
                if not messagebox.askyesno(
                    "Live validation unavailable",
                    f"{err}\n\nResolve offline (no balance checks) instead?",
                ):
                    return
                lookup = None
            self.config(cursor="watch")
            self.update()
            try:
                resolved = resolve_bids(items_to_bids(self.items), lookup=lookup)
                text = format_results(resolved)
            except Exception as e:
                self.config(cursor="")
                messagebox.showerror("Resolve failed", str(e))
                return
            self.config(cursor="")
            _show_results(self, text, validated=lookup is not None)

    def _item_dialog(parent, title, initial=None):
        initial = initial or {}
        dlg = tk.Toplevel(parent)
        dlg.title(title)
        dlg.transient(parent)
        dlg.grab_set()
        out = {}
        ttk.Label(dlg, text="Item name").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        name_e = ttk.Entry(dlg, width=40)
        name_e.grid(row=0, column=1, padx=6, pady=4)
        name_e.insert(0, initial.get("item", ""))
        ttk.Label(dlg, text="KP pool").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        kp_v = tk.StringVar(value=initial.get("kp", "VKP"))
        ttk.Combobox(dlg, textvariable=kp_v, values=POOLS, state="readonly",
                     width=12).grid(row=1, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(dlg, text="Quantity").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        qty_e = ttk.Entry(dlg, width=6)
        qty_e.grid(row=2, column=1, sticky="w", padx=6, pady=4)
        qty_e.insert(0, str(initial.get("qty", 1)))

        def ok():
            name = name_e.get().strip()
            if not name:
                messagebox.showinfo("Item name", "Enter an item name.", parent=dlg)
                return
            try:
                qty = max(1, int(qty_e.get().strip() or "1"))
            except ValueError:
                messagebox.showinfo("Quantity", "Quantity must be a whole number.", parent=dlg)
                return
            out.update({"item": name, "kp": kp_v.get(), "qty": qty})
            dlg.destroy()

        bar = ttk.Frame(dlg)
        bar.grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(bar, text="OK", command=ok).pack(side="left", padx=4)
        ttk.Button(bar, text="Cancel", command=dlg.destroy).pack(side="left")
        name_e.focus_set()
        parent.wait_window(dlg)
        return out or None

    def _bid_dialog(parent, title, initial=None):
        initial = initial or {}
        dlg = tk.Toplevel(parent)
        dlg.title(title)
        dlg.transient(parent)
        dlg.grab_set()
        out = {}
        ttk.Label(dlg, text="Bidder (pays)").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        bidder_e = ttk.Entry(dlg, width=28)
        bidder_e.grid(row=0, column=1, padx=6, pady=4)
        bidder_e.insert(0, initial.get("bidder", ""))
        ttk.Label(dlg, text="For (recipient, optional)").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        for_e = ttk.Entry(dlg, width=28)
        for_e.grid(row=1, column=1, padx=6, pady=4)
        for_e.insert(0, initial.get("for_player", ""))
        ttk.Label(dlg, text="Amount").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        amt_e = ttk.Entry(dlg, width=10)
        amt_e.grid(row=2, column=1, sticky="w", padx=6, pady=4)
        amt_e.insert(0, str(initial.get("amount", "")))

        def ok():
            bidder = bidder_e.get().strip()
            if not bidder:
                messagebox.showinfo("Bidder", "Enter a bidder name.", parent=dlg)
                return
            try:
                amount = int(round(float(amt_e.get().strip())))
            except ValueError:
                messagebox.showinfo("Amount", "Amount must be a number.", parent=dlg)
                return
            out.update({"bidder": bidder, "for_player": for_e.get().strip(), "amount": amount})
            dlg.destroy()

        bar = ttk.Frame(dlg)
        bar.grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(bar, text="OK", command=ok).pack(side="left", padx=4)
        ttk.Button(bar, text="Cancel", command=dlg.destroy).pack(side="left")
        bidder_e.focus_set()
        parent.wait_window(dlg)
        return out or None

    def _show_results(parent, text, validated):
        win = tk.Toplevel(parent)
        win.title("Results" + ("" if validated else "  (offline — not validated)"))
        win.geometry("640x520")
        txt = tk.Text(win, wrap="word", font=("Consolas", 10))
        txt.pack(fill="both", expand=True, padx=6, pady=6)
        txt.insert("1.0", text)
        txt.config(state="disabled")
        bar = ttk.Frame(win)
        bar.pack(fill="x", pady=4)

        def copy():
            parent.clipboard_clear()
            parent.clipboard_append(text)

        def save():
            path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                filetypes=[("Text", "*.txt")])
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)

        ttk.Button(bar, text="Copy", command=copy).pack(side="left", padx=6)
        ttk.Button(bar, text="Save…", command=save).pack(side="left")
        ttk.Button(bar, text="Close", command=win.destroy).pack(side="right", padx=6)

    BidApp().mainloop()


def main():
    # The result text uses ⚠ / ✗; the default Windows console is cp1252 and
    # would crash on them. Force UTF-8 (replace on the off chance it can't).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if len(sys.argv) > 1:
        sys.exit(_cli(sys.argv[1:]))
    _run_gui()


if __name__ == "__main__":
    main()
