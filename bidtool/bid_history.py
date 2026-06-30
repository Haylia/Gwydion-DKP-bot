"""Local record of resolved bid rounds, so the weekly per-pool cap can be
enforced without any per-item dates on the Loot sheet.

You *commit* a round once it's final; each winning line is appended with a
timestamp. The cap check then counts a bidder's wins per pool inside a rolling
7-day window. Stored as JSON next to the tool (gitignored runtime state, like the
bot's bids.json).
"""

import json
import os
import time

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bid_history.json")
WEEK_SECONDS = 7 * 24 * 3600


def _load(path):
    if not os.path.isfile(path):
        return {"wins": []}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if "wins" not in data:
            data["wins"] = []
        return data
    except (OSError, ValueError):
        return {"wins": []}


def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def commit_winners(winners, path=HISTORY_FILE, now=None):
    """Append a list of winning lines to history.

    `winners` items are dicts with at least: bidder, kp, item, amount, for_player.
    `now` is an epoch seconds override (for tests); defaults to wall clock.
    Returns how many lines were recorded.
    """
    now = time.time() if now is None else now
    data = _load(path)
    for w in winners:
        data["wins"].append({
            "ts": now,
            "bidder": w.get("bidder", ""),
            "kp": str(w.get("kp", "")).upper(),
            "item": w.get("item", ""),
            "amount": w.get("amount"),
            "for_player": w.get("for_player", ""),
        })
    _save(path, data)
    return len(winners)


def week_counts(path=HISTORY_FILE, now=None, window=WEEK_SECONDS):
    """Return {(bidder_lower, POOL): count} for wins inside the trailing window.

    Keyed to match the resolver's cap counter. Bidder names are lower-cased so
    casing differences don't split a player's tally.
    """
    now = time.time() if now is None else now
    data = _load(path)
    counts = {}
    for w in data["wins"]:
        try:
            ts = float(w.get("ts", 0))
        except (TypeError, ValueError):
            continue
        if now - ts > window:
            continue
        key = (str(w.get("bidder", "")).strip().lower(), str(w.get("kp", "")).upper())
        counts[key] = counts.get(key, 0) + 1
    return counts


def prune(path=HISTORY_FILE, now=None, window=WEEK_SECONDS):
    """Drop wins older than the window so the file doesn't grow forever."""
    now = time.time() if now is None else now
    data = _load(path)
    keep = [w for w in data["wins"] if now - float(w.get("ts", 0) or 0) <= window]
    removed = len(data["wins"]) - len(keep)
    if removed:
        data["wins"] = keep
        _save(path, data)
    return removed
