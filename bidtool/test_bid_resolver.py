"""Tests for the pure bid-resolution logic.

Run directly (no deps):   python bidtool/test_bid_resolver.py
Or via pytest:            pytest bidtool/test_bid_resolver.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bid_resolver import resolve_bids, format_results
from gear_rules import GearRules

ALL_POOLS = ["VKP", "GKP", "PKP", "AKP", "RBPPUNOX", "DPKP", "RBPP"]


def player(balances=None, level=250, is_main=True, main_name=None,
           rbpp_pct=1.0, rbpp_earned=99999):
    """A toon with everything maxed by default, so gates pass unless a test
    lowers a specific field."""
    if balances is None:
        balances = {p: 99999 for p in ALL_POOLS}
    return {"balances": balances, "level": level, "is_main": is_main,
            "main_name": main_name, "rbpp_pct": rbpp_pct, "rbpp_earned": rbpp_earned}


def make_lookup(players):
    by_lower = {n.lower(): n for n in players}

    def lookup(pool, name):
        canon = by_lower.get(name.strip().lower())
        if canon is None:
            return {"canonical": None, "suggestions": []}
        p = players[canon]
        return {
            "canonical": canon, "suggestions": [],
            "balance": p["balances"].get(pool.upper()),
            "level": p["level"], "is_main": p["is_main"], "main_name": p["main_name"],
            "rbpp_pct": p["rbpp_pct"], "rbpp_earned": p["rbpp_earned"],
        }

    return lookup


def bid(item, kp, bidder, amount, qty=1, for_player="", **over):
    d = {"item": item, "kp": kp, "qty": qty, "bidder": bidder,
         "for_player": for_player, "amount": amount}
    d.update(over)
    return d


def item_named(res, name):
    for it in res["items"]:
        if it["item"] == name:
            return it
    raise AssertionError(f"no item {name!r} in results")


# ── core resolution ─────────────────────────────────────────────────────────
def test_uncontested_single():
    lk = make_lookup({"Chich1": player()})
    res = resolve_bids([bid("Fetter", "VKP", "Chich1", 200)], lookup=lk)
    it = item_named(res, "Fetter")
    assert it["status"] == "resolved"
    assert [w["bidder"] for w in it["winners"]] == ["Chich1"]


def test_contested_single_highest_wins():
    lk = make_lookup({"A": player(), "B": player()})
    res = resolve_bids([bid("X", "VKP", "A", 100), bid("X", "VKP", "B", 250)], lookup=lk)
    it = item_named(res, "X")
    assert [w["bidder"] for w in it["winners"]] == ["B"]
    assert [l["bidder"] for l in it["losers"]] == ["A"]


def test_single_item_tie_flagged():
    lk = make_lookup({"A": player(), "B": player()})
    res = resolve_bids([bid("X", "VKP", "A", 200), bid("X", "VKP", "B", 200)], lookup=lk)
    it = item_named(res, "X")
    assert it["status"] == "tie"
    assert it["open_slots"] == 1
    assert sorted(t["bidder"] for t in it["tied"]) == ["A", "B"]
    assert it["winners"] == []


# ── affordability gate ──────────────────────────────────────────────────────
def test_afford_block_promotes_next():
    lk = make_lookup({"A": player(balances={"VKP": 100}), "B": player()})
    res = resolve_bids([bid("X", "VKP", "A", 300), bid("X", "VKP", "B", 250)], lookup=lk)
    it = item_named(res, "X")
    assert [w["bidder"] for w in it["winners"]] == ["B"]
    assert [d["bidder"] for d in it["blocked"]] == ["A"]
    assert "afford" in it["blocked"][0]["reason"]


# ── level gate ──────────────────────────────────────────────────────────────
def test_level_gate_blocks():
    rules = GearRules([{"match": ["exalted"], "min_level": 205}])
    lk = make_lookup({"Low": player(level=200), "Hi": player(level=210)})
    res = resolve_bids([bid("Exalted Boots", "AKP", "Low", 300),
                        bid("Exalted Boots", "AKP", "Hi", 100)], lookup=lk, rules=rules)
    it = item_named(res, "Exalted Boots")
    assert [w["bidder"] for w in it["winners"]] == ["Hi"]
    assert any("level 200" in d["reason"] for d in it["blocked"])


# ── RBPP %% gate ─────────────────────────────────────────────────────────────
def test_rbpp_pct_gate_blocks():
    rules = GearRules([{"match": ["defiled"], "min_rbpp_pct": 25}])
    lk = make_lookup({"Low": player(rbpp_pct=0.10), "Ok": player(rbpp_pct=0.30)})
    res = resolve_bids([bid("Defiled Ring", "VKP", "Low", 300),
                        bid("Defiled Ring", "VKP", "Ok", 100)], lookup=lk, rules=rules)
    it = item_named(res, "Defiled Ring")
    assert [w["bidder"] for w in it["winners"]] == ["Ok"]
    assert any("RBPP" in d["reason"] for d in it["blocked"])


# ── lifetime RBPP gate ──────────────────────────────────────────────────────
def test_rbpp_earned_gate_blocks():
    rules = GearRules([{"match": ["void"], "min_rbpp_earned": 250}])
    lk = make_lookup({"Poor": player(rbpp_earned=100), "Rich": player(rbpp_earned=500)})
    res = resolve_bids([bid("Voidsworn Hammer", "DPKP", "Poor", 800),
                        bid("Voidsworn Hammer", "DPKP", "Rich", 400)], lookup=lk, rules=rules)
    it = item_named(res, "Voidsworn Hammer")
    assert [w["bidder"] for w in it["winners"]] == ["Rich"]
    assert any("lifetime RBPP" in d["reason"] for d in it["blocked"])


# ── weekly cap gate ─────────────────────────────────────────────────────────
def test_weekly_cap_blocks_when_at_limit():
    lk = make_lookup({"A": player(), "B": player()})
    # A already won 4 VKP items this week -> A is blocked, B wins.
    wc = {("a", "VKP"): 4}
    res = resolve_bids([bid("X", "VKP", "A", 300), bid("X", "VKP", "B", 100)],
                       lookup=lk, week_counts=wc, cap_limit=4)
    it = item_named(res, "X")
    assert [w["bidder"] for w in it["winners"]] == ["B"]
    assert any("weekly cap" in d["reason"] for d in it["blocked"])


def test_weekly_cap_counts_this_round():
    lk = make_lookup({"A": player()})
    # A has 3 prior wins; wins item1, hitting 4; item2 should be capped.
    wc = {("a", "VKP"): 3}
    res = resolve_bids([bid("Item1", "VKP", "A", 300),
                        bid("Item2", "VKP", "A", 200)],
                       lookup=lk, week_counts=wc, cap_limit=4)
    # Item1 (higher bid) processed first -> A wins; Item2 -> capped, no winner.
    assert [w["bidder"] for w in item_named(res, "Item1")["winners"]] == ["A"]
    assert item_named(res, "Item2")["status"] == "no_valid_bids"


def test_cap_disabled_without_week_counts():
    lk = make_lookup({"A": player()})
    res = resolve_bids([bid("Item1", "VKP", "A", 300),
                        bid("Item2", "VKP", "A", 200)], lookup=lk)  # no week_counts
    assert item_named(res, "Item1")["winners"][0]["bidder"] == "A"
    assert item_named(res, "Item2")["winners"][0]["bidder"] == "A"


# ── quantity ────────────────────────────────────────────────────────────────
def test_x2_contested_top_two_each_own_bid():
    lk = make_lookup({"A": player(), "B": player(), "C": player()})
    res = resolve_bids([bid("N", "DPKP", "A", 300, qty=2),
                        bid("N", "DPKP", "B", 200, qty=2),
                        bid("N", "DPKP", "C", 100, qty=2)], lookup=lk)
    it = item_named(res, "N")
    winners = {w["bidder"]: w["amount"] for w in it["winners"]}
    assert winners == {"A": 300, "B": 200}
    assert [l["bidder"] for l in it["losers"]] == ["C"]


def test_x2_tie_at_cutoff():
    lk = make_lookup({"A": player(), "B": player(), "C": player()})
    res = resolve_bids([bid("N", "DPKP", "A", 300, qty=2),
                        bid("N", "DPKP", "B", 200, qty=2),
                        bid("N", "DPKP", "C", 200, qty=2)], lookup=lk)
    it = item_named(res, "N")
    assert it["status"] == "tie"
    assert [w["bidder"] for w in it["winners"]] == ["A"]
    assert it["open_slots"] == 1
    assert sorted(t["bidder"] for t in it["tied"]) == ["B", "C"]


# ── flags (not blocks) ──────────────────────────────────────────────────────
def test_main_alt_flag():
    lk = make_lookup({"AltGuy": player(is_main=False, main_name="MainGuy"),
                      "MainGuy": player(is_main=True)})
    res = resolve_bids([bid("X", "VKP", "AltGuy", 300),
                        bid("X", "VKP", "MainGuy", 100)], lookup=lk)
    it = item_named(res, "X")
    assert [w["bidder"] for w in it["winners"]] == ["AltGuy"]  # alt still wins (flag, not block)
    assert any("alt AltGuy won over main" in f for f in it["flags"])


def test_cumulative_overrun_flag():
    lk = make_lookup({"Chich1": player(balances={"DPKP": 800})})
    res = resolve_bids([bid("Hammer", "DPKP", "Chich1", 750),
                        bid("Necklace", "DPKP", "Chich1", 200)], lookup=lk)
    assert any("OVERRUN" in f for f in item_named(res, "Hammer")["flags"])
    assert any("OVERRUN" in f for f in item_named(res, "Necklace")["flags"])


# ── validity ────────────────────────────────────────────────────────────────
def test_unknown_player_is_invalid():
    lk = make_lookup({"Real": player()})
    res = resolve_bids([bid("X", "VKP", "Ghost", 100)], lookup=lk)
    it = item_named(res, "X")
    assert it["status"] == "no_valid_bids"
    assert it["invalid"][0]["bidder"] == "Ghost"


def test_no_pool_record_is_invalid():
    lk = make_lookup({"A": player(balances={"VKP": 500})})  # no DPKP balance
    res = resolve_bids([bid("X", "DPKP", "A", 100)], lookup=lk)
    it = item_named(res, "X")
    assert it["status"] == "no_valid_bids"
    assert "no DPKP record" in it["invalid"][0]["reason"]


# ── offline / overrides / formatting ────────────────────────────────────────
def test_offline_mode_raw_highest_no_checks():
    res = resolve_bids([bid("X", "VKP", "A", 9999), bid("X", "VKP", "B", 100)], lookup=None)
    it = item_named(res, "X")
    assert [w["bidder"] for w in it["winners"]] == ["A"]
    assert it["blocked"] == []


def test_per_item_override_sets_requirement():
    # No matching gear rule, but the CSV/GUI override forces a level gate.
    rules = GearRules([])
    lk = make_lookup({"Low": player(level=200), "Hi": player(level=230)})
    res = resolve_bids([bid("Mystery Boots", "AKP", "Low", 300, min_level=225),
                        bid("Mystery Boots", "AKP", "Hi", 100, min_level=225)],
                       lookup=lk, rules=rules)
    it = item_named(res, "Mystery Boots")
    assert [w["bidder"] for w in it["winners"]] == ["Hi"]


def test_unclassified_item_note():
    rules = GearRules([])  # nothing matches
    lk = make_lookup({"A": player()})
    res = resolve_bids([bid("Random Trinket", "VKP", "A", 100)], lookup=lk, rules=rules)
    out = format_results(res)
    assert "no gear rule matched" in out


def test_for_recipient_carried_to_output():
    lk = make_lookup({"Chich1": player()})
    res = resolve_bids([bid("Hammer", "DPKP", "Chich1", 750, for_player="CarlosOrtis")], lookup=lk)
    out = format_results(res)
    assert "Chich1 for CarlosOrtis - Hammer" in out
    assert "(750 DPKP)" in out


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"ok   {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa
            import traceback
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
