"""Unit tests for the local JSON state files in 'gwydion dkp.py':
  - the tiebreaks / gen-posts / pending-gens stores (now atomic writes)
  - the per-guild server_config helpers

Runs against the real shipped source via `test_support.load`. Test-only; never
deployed.

Run from the repo root:  python test_state.py
"""
import os
import json
import logging
import tempfile
from test_support import load

_LOG = logging.getLogger("test")


def _temp(name):
    return os.path.join(tempfile.mkdtemp(), name)


# ─── tiebreaks / gen-posts / pending-gens: identical load/save shape ────────

def _check_state_store(load_fn, save_fn, file_const, default_filename):
    """Exercise one of the three structurally-identical JSON state stores."""
    path = _temp(default_filename)
    ns = load([load_fn, save_fn, file_const, "_atomic_write_json"], logger=_LOG)
    ns[file_const] = path
    loader, saver = ns[load_fn], ns[save_fn]

    # missing file -> empty dict
    assert loader() == {}

    # save then load round-trips
    payload = {"123": {"status": "open", "rolls": {"u1": 42}}, "456": {"status": "closed"}}
    saver(payload)
    assert os.path.exists(path)
    assert loader() == payload

    # the on-disk file is valid JSON (atomic write completed, no .tmp left behind)
    with open(path, "r", encoding="utf-8") as f:
        assert json.load(f) == payload
    assert not os.path.exists(path + ".tmp")

    # corrupt file is treated as empty, not raised
    with open(path, "w", encoding="utf-8") as f:
        f.write("{ broken")
    assert loader() == {}


def test_tiebreaks_store():
    _check_state_store("_load_tiebreaks", "_save_tiebreaks", "TIEBREAKS_FILE", "tiebreaks.json")
    print("ok: tiebreaks store round-trips atomically + tolerates corrupt/missing")


def test_gen_posts_store():
    _check_state_store("_load_gen_posts", "_save_gen_posts", "GEN_POSTS_FILE", "gen_posts.json")
    print("ok: gen_posts store round-trips atomically + tolerates corrupt/missing")


def test_pending_gens_store():
    _check_state_store("_load_pending_gens", "_save_pending_gens", "PENDING_GENS_FILE", "pending_gens.json")
    print("ok: pending_gens store round-trips atomically + tolerates corrupt/missing")


# ─── per-guild server_config helpers ───────────────────────────────────────

_SERVER_FNS = [
    "load_server_config", "save_server_config", "get_server_entry",
    "set_server_entry", "remove_server_entry",
    "get_world_id_for_guild", "get_channel_id_for_guild",
    "SERVER_CONFIG_VERSION",
]


def _server_ns():
    path = _temp("server_config.json")
    ns = load(_SERVER_FNS, logger=_LOG)
    ns["SERVER_CONFIG_FILE"] = path
    return ns


def test_server_config_crud():
    ns = _server_ns()
    get_entry = ns["get_server_entry"]
    set_entry = ns["set_server_entry"]
    remove = ns["remove_server_entry"]
    world_of = ns["get_world_id_for_guild"]
    channel_of = ns["get_channel_id_for_guild"]

    # unconfigured guild
    assert get_entry(123) is None
    assert world_of(123) is None and channel_of(123) is None

    # create
    entry = set_entry(123, world_id=15, channel_id=999, setup_role="Officer")
    assert entry["world_id"] == 15 and entry["channel_id"] == 999 and entry["setup_role"] == "Officer"
    assert "added_at" in entry
    assert world_of(123) == 15 and channel_of(123) == 999
    assert get_entry("123")["setup_role"] == "Officer"   # int / str guild_id both work

    # partial update preserves other fields; channel_id=0 clears it
    set_entry(123, world_id=20)
    assert world_of(123) == 20 and get_entry(123)["setup_role"] == "Officer"
    set_entry(123, channel_id=0)
    assert channel_of(123) is None

    # _meta is preserved with the schema version
    cfg = ns["load_server_config"]()
    assert cfg["_meta"]["version"] == ns["SERVER_CONFIG_VERSION"]

    # remove
    assert remove(123) is True
    assert remove(123) is False
    assert get_entry(123) is None
    print("ok: server_config create / read / partial-update / clear / remove")


def test_server_config_missing_guild_id():
    ns = _server_ns()
    assert ns["get_server_entry"](None) is None
    assert ns["remove_server_entry"](None) is False
    assert ns["get_world_id_for_guild"](None) is None
    print("ok: server_config helpers handle None guild_id")


_TESTS = [
    test_tiebreaks_store,
    test_gen_posts_store,
    test_pending_gens_store,
    test_server_config_crud,
    test_server_config_missing_guild_id,
]


if __name__ == "__main__":
    for t in _TESTS:
        t()
    print(f"\nALL {len(_TESTS)} STATE TESTS PASSED")
