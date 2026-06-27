"""Unit tests for the bidding / auction store inlined in 'gwydion dkp.py'.

Runs against the real shipped source via the shared `test_support.load` harness
(see that module for how/why the bot file can't just be imported). Test-only;
never deployed.

Run from the repo root:  python test_bid_store.py
"""
import os
import logging
import tempfile
from test_support import load

# The bid helpers + their constants and the shared atomic writer they call.
_NAMES = [
    "BIDS_FILE", "BID_CLOSE_AGE", "BID_HISTORY_AGE", "_atomic_write_json",
    "_bid_empty", "_load_bids", "_save_bids", "_bid_get_auction",
    "_bid_new_auction", "_bid_add", "_bid_cancel", "_bid_user_bids",
    "_bid_close_due", "_bid_prune", "_bid_results", "_bid_is_first_bid",
]
# logger is referenced by _load_bids' corrupt-file branch.
BS = load(_NAMES, logger=logging.getLogger("test"))


def _point_at_temp():
    """Redirect the helpers' BIDS_FILE global at a fresh temp path."""
    BS["BIDS_FILE"] = os.path.join(tempfile.mkdtemp(), "bids.json")


def test_missing_file_is_empty():
    _point_at_temp()
    assert BS["_load_bids"]() == {"_meta": {"next_id": 1}, "auctions": {}}
    print("ok: missing file -> empty seeded store")


def test_full_lifecycle():
    _point_at_temp()
    t0 = 1_000_000.0
    close_age = BS["BID_CLOSE_AGE"]
    history_age = BS["BID_HISTORY_AGE"]

    # --- startbid ---
    data = BS["_load_bids"]()
    aid = BS["_bid_new_auction"](data, "Sword of Foo", "DPKP", "user_a", "Alice", 100, t0)
    BS["_save_bids"](data)
    assert aid == 1 and data["_meta"]["next_id"] == 2

    # round-trips through disk (and proves the atomic write produced valid JSON)
    data = BS["_load_bids"]()
    auc = BS["_bid_get_auction"](data, 1)
    assert auc and auc["status"] == "Open"
    assert auc["bids"][0]["price"] == 100 and auc["bids"][0]["toon"] == "Alice"

    # second auction gets the next id (no reuse/gaps)
    assert BS["_bid_new_auction"](data, "Helm of Bar", "GKP", "user_x", "Xander", 5, t0) == 2
    BS["_save_bids"](data)

    # --- sendbid: two more bids on auction 1 ---
    data = BS["_load_bids"]()
    auc = BS["_bid_get_auction"](data, 1)
    BS["_bid_add"](auc, "user_b", "Bob", 150, t0 + 60)
    BS["_bid_add"](auc, "user_c", "Carol", 130, t0 + 120)
    BS["_save_bids"](data)

    # results ordering: highest first, opening bid included
    data = BS["_load_bids"]()
    ranked = BS["_bid_results"](BS["_bid_get_auction"](data, 1))
    assert ranked == [("Bob", 150), ("Carol", 130), ("Alice", 100)], ranked
    print("ok: results sorted high->low incl. the opening bid")

    # mybids lookup by discord user id
    assert len(BS["_bid_user_bids"](data, "user_b")) == 1
    assert len(BS["_bid_user_bids"](data, "user_z")) == 0

    # --- cancelbid: Carol cancels, auction stays open ---
    auc = BS["_bid_get_auction"](data, 1)
    removed, closed = BS["_bid_cancel"](auc, "user_c", "Carol", 130, t0 + 200)
    assert removed and not closed and len(auc["bids"]) == 2
    BS["_save_bids"](data)

    # cancel with a non-matching price -> no-op
    removed, closed = BS["_bid_cancel"](auc, "user_b", "Bob", 999, t0 + 200)
    assert not removed and not closed

    # cancel that empties an auction closes it
    data = BS["_load_bids"]()
    a2 = BS["_bid_get_auction"](data, 2)
    removed, closed = BS["_bid_cancel"](a2, "user_x", "Xander", 5, t0 + 300)
    assert removed and closed and a2["status"] == "Closed" and a2["close_time"] == t0 + 300
    BS["_save_bids"](data)
    print("ok: cancel removes a bid; emptying closes the auction")

    # --- bidloop close: nothing due within 12h, auction 1 closes just past it ---
    data = BS["_load_bids"]()
    assert BS["_bid_close_due"](data, t0 + close_age - 1) == []
    due = BS["_bid_close_due"](data, t0 + close_age + 1)
    assert len(due) == 1 and due[0]["id"] == 1
    assert BS["_bid_get_auction"](data, 1)["status"] == "Closed"
    BS["_save_bids"](data)
    print("ok: bidloop closes auctions past the 12h window")

    # --- prune: closed auctions vanish after 7 days; next_id preserved ---
    data = BS["_load_bids"]()
    assert BS["_bid_prune"](data, t0 + close_age + 2) == 0          # too early
    assert BS["_bid_prune"](data, t0 + close_age + history_age + 10) == 2
    assert data["auctions"] == {} and data["_meta"]["next_id"] == 3
    BS["_save_bids"](data)
    assert BS["_load_bids"]()["_meta"]["next_id"] == 3
    print("ok: prune drops 7-day-old closed auctions, next_id preserved")


def test_corrupt_file_recovers():
    _point_at_temp()
    with open(BS["BIDS_FILE"], "w", encoding="utf-8") as f:
        f.write("{not valid json")
    assert BS["_load_bids"]() == {"_meta": {"next_id": 1}, "auctions": {}}
    print("ok: corrupt file treated as empty")


def test_interested_notice_helpers():
    _point_at_temp()
    data = BS["_load_bids"]()
    # the originating channel/thread id is recorded on the auction
    BS["_bid_new_auction"](data, "Cape", "VKP", "u1", "Alice", 10, 1.0, channel_id=4242)
    auc = BS["_bid_get_auction"](data, 1)
    assert auc["channel_id"] == 4242
    # the opening bidder counts as already-bid (no 'interested' notice for them)
    assert BS["_bid_is_first_bid"](auc, "Alice") is False
    # a different toon is first-time until they actually bid
    assert BS["_bid_is_first_bid"](auc, "Bob") is True
    BS["_bid_add"](auc, "u2", "Bob", 20, 2.0)
    assert BS["_bid_is_first_bid"](auc, "Bob") is False
    # channel_id defaults to None when $startbid had no channel
    BS["_bid_new_auction"](data, "Ring", "GKP", "u3", "Carol", 5, 3.0)
    assert BS["_bid_get_auction"](data, 2)["channel_id"] is None
    print("ok: channel_id stored; _bid_is_first_bid tracks first bid per toon")


_TESTS = [
    test_missing_file_is_empty,
    test_full_lifecycle,
    test_corrupt_file_recovers,
    test_interested_notice_helpers,
]


if __name__ == "__main__":
    for t in _TESTS:
        t()
    print(f"\nALL {len(_TESTS)} BID-STORE TESTS PASSED")
