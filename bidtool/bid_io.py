"""CSV load/save for the bid tool. One row per bid.

Columns (header row required):
    item, kp, qty, bidder, for_player, amount
Optional per-item override columns (leave blank to use the gear_rules.json
auto-tagging): min_level, min_rbpp_pct, min_rbpp_earned, is_helm

Example:
    item,kp,qty,bidder,for_player,amount
    Defiled Fetter of the poisoner,VKP,1,Chich1,,200
    Voidsworn hammer of Ashes,DPKP,1,Chich1,CarlosOrtis,750
"""

import csv

CORE_FIELDS = ["item", "kp", "qty", "bidder", "for_player", "amount"]
OVERRIDE_FIELDS = ["min_level", "min_rbpp_pct", "min_rbpp_earned", "is_helm"]
FIELDS = CORE_FIELDS + OVERRIDE_FIELDS


def load_csv(path):
    """Read a bids CSV into a list of bid dicts. Tolerates extra/missing columns
    and blank lines. Raises ValueError if the header is unrecognisable."""
    bids = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return bids
        present = {(h or "").strip().lower() for h in reader.fieldnames}
        if "item" not in present or "bidder" not in present or "amount" not in present:
            raise ValueError(
                "CSV must have at least 'item', 'bidder' and 'amount' columns. "
                f"Found: {reader.fieldnames}"
            )
        for row in reader:
            norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            if not norm.get("item") and not norm.get("bidder"):
                continue  # blank line
            bid = {
                "item": norm.get("item", ""),
                "kp": norm.get("kp", ""),
                "qty": norm.get("qty", "1") or "1",
                "bidder": norm.get("bidder", ""),
                "for_player": norm.get("for_player", ""),
                "amount": norm.get("amount", ""),
            }
            for k in OVERRIDE_FIELDS:
                if norm.get(k):
                    bid[k] = norm[k]
            bids.append(bid)
    return bids


def save_csv(path, bids):
    """Write a list of bid dicts back to CSV."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for b in bids:
            writer.writerow({k: b.get(k, "") for k in FIELDS})


def write_template(path):
    """Write a blank template (header + one commented example) to fill in."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerow(["Defiled Fetter of the poisoner", "VKP", "1", "Chich1", "", "200"])
        writer.writerow(["Voidsworn hammer of Ashes", "DPKP", "1", "Chich1", "CarlosOrtis", "750"])
        writer.writerow(["Imperial Eidolic Necklace Of Brawlers", "DPKP", "2", "Chich1", "", "200"])
