"""Unit tests for the pure helper functions in 'gwydion dkp.py'.

These run against the real shipped source via the shared `test_support.load`
harness (see that module for how/why). Data dicts (CH_WORLDS, BOSS_NAMES,
BOSS_ALIASES, the OCR regexes) are real literals lifted straight from the file;
only a couple of derived constants are injected as fixtures. Test-only; never
deployed.

Run from the repo root:  python test_helpers.py
"""
from datetime import date, timedelta
from test_support import load


# ─── numeric / cell helpers ────────────────────────────────────────────────

def test_safe_float_and_int():
    ns = load(["safe_float", "safe_int"])
    sf, si = ns["safe_float"], ns["safe_int"]
    assert sf("12.5") == 12.5
    assert sf("50%") == 50.0
    assert sf("") == 0.0
    assert sf(None) == 0.0
    assert sf("#DIV/0!") == 0.0
    assert sf("junk") == 0.0
    assert sf("junk", default=-1) == -1
    assert sf("  7 ") == 7.0
    assert si("12.9") == 12
    assert si("") == 0
    assert si(None) == 0
    assert si("abc") == 0
    assert si("3") == 3
    print("ok: safe_float / safe_int tolerate blanks, %, # errors, junk")


def test_pad_row():
    ns = load(["pad_row"])
    pad = ns["pad_row"]
    assert pad(["a", "b"], 4) == ["a", "b", "", ""]
    assert pad(["a", "b", "c"], 2) == ["a", "b", "c"]  # already long enough
    src = ["x"]
    out = pad(src, 3)
    assert out == ["x", "", ""] and src == ["x"]       # does not mutate input
    print("ok: pad_row right-pads to length without mutating input")


def test_sanitize_cell():
    ns = load(["sanitize_cell"])
    sc = ns["sanitize_cell"]
    for bad in ("=SUM(A1)", "+1", "-1", "@x"):
        assert sc(bad) == "'" + bad
    assert sc("Liaa") == "Liaa"
    assert sc("") == ""
    assert sc(123) == 123          # non-str passes through untouched
    print("ok: sanitize_cell neutralises =+-@ formula injection only")


def test_tobool_and_time_to_seconds():
    ns = load(["toBool", "time_to_seconds"])
    tb, tts = ns["toBool"], ns["time_to_seconds"]
    assert tb("true") is True
    assert tb("TRUE") is True
    assert tb("tRuE") is True
    assert tb("false") is False
    assert tb("yes") is False
    assert tts("01:02:03") == 3723
    assert tts("00:00:00") == 0
    assert tts("10:00:00") == 36000
    print("ok: toBool / time_to_seconds")


# ─── OCR row parsing ───────────────────────────────────────────────────────

def test_parse_text():
    ns = load(["parse_text", "time_to_seconds", "DURATION_REGEX", "ROW_REGEX", "BLACKLIST"])
    text = (
        "Boss fight 01:00:00\n"
        "1 Alice 1,234,567\n"
        "2 Bob 50000\n"
        "Total 9,999,999\n"        # blacklisted name -> skipped
        "Health 88,888\n"          # blacklisted name -> skipped
    )
    duration, players = ns["parse_text"](text)
    assert duration == 3600, duration
    assert players == [("Alice", 1234567), ("Bob", 50000)], players
    print("ok: parse_text reads duration, strips commas, drops blacklist rows")


# ─── fuzzy name matching ───────────────────────────────────────────────────

def test_find_name():
    ns = load(["find_name"])
    fn = ns["find_name"]
    roster = ["Liaa", "Bob Smith", "Bobby", "Carol", "Alexander", "Zoe"]

    # exact, case-insensitive
    assert fn("liaa", roster) == ("Liaa", True, False, [])
    # exact ignoring spaces
    name, caps, spaces, sugg = fn("bobsmith", roster)
    assert name == "Bob Smith" and spaces is True and sugg == []
    # unique prefix
    assert fn("car", roster)[0] == "Carol"
    # ambiguous prefix -> no match, both suggested
    name, _, _, sugg = fn("bob", roster)
    assert name is None and set(sugg) == {"Bob Smith", "Bobby"}
    # unique substring (not a prefix)
    assert fn("mith", roster)[0] == "Bob Smith"
    # fuzzy edit-distance (clear winner, big gap over runner-up)
    assert fn("alexsnder", roster)[0] == "Alexander"
    # no match at all
    assert fn("zzzzzz", roster) == (None, False, False, [])
    # empty / degenerate inputs
    assert fn("", roster) == (None, False, False, [])
    assert fn("x", []) == (None, False, False, [])
    print("ok: find_name exact / spaces / prefix / ambiguous / substring / fuzzy / miss")


def test_not_found_message():
    ns = load(["not_found_message"])
    nfm = ns["not_found_message"]
    assert nfm("Xyz", []) == "Could not find player 'Xyz'."
    assert nfm("Bob", ["Bob Smith", "Bobby"]) == \
        "Could not find player 'Bob'. Did you mean: Bob Smith, Bobby?"
    print("ok: not_found_message with and without suggestions")


# ─── loot / deduct parsing ─────────────────────────────────────────────────

def test_parse_deduct_args():
    ns = load(["parse_deduct_args"])
    pda = ns["parse_deduct_args"]
    assert pda('"Liaa" "Sword of Foo" 100 dpkp') == ("Liaa", "Sword of Foo", 100.0, "DPKP")
    assert pda('$deduct "Liaa" "Item" 50 vkp') == ("Liaa", "Item", 50.0, "VKP")
    assert pda('"a" "b" notanumber KP') == (None, None, None, None)
    assert pda('"a" "b" 0 KP') == (None, None, None, None)      # number must be > 0
    assert pda('"a" "b" -5 KP') == (None, None, None, None)
    assert pda(123) == (None, None, None, None)                 # non-string
    print("ok: parse_deduct_args handles quotes, $deduct prefix, bad/zero numbers")


def test_loot_next_col():
    ns = load(["_loot_next_col"])
    nc = ns["_loot_next_col"]
    # three filled cells (col0 = name) -> next free column is 4
    assert nc(["Name", "ItemA", "ItemB"], ["Name", "10", "20"]) == 4
    # a gap at index 1 is reused
    assert nc(["Name", "", "ItemB"], ["Name", "", "20"]) == 2
    # trailing blanks (gspread padding) are ignored
    assert nc(["Name", "ItemA", "", ""], ["Name", "10", "", ""]) == 3
    # only the name cell -> first item column is 2
    assert nc(["Name"], ["Name"]) == 2
    print("ok: _loot_next_col appends, reuses gaps, ignores trailing blanks")


# ─── world name resolution (real CH_WORLDS data) ───────────────────────────

def test_world_helpers():
    ns = load(["normalize_world_name", "resolve_world", "display_world", "CH_WORLDS"])
    norm, resolve, disp = ns["normalize_world_name"], ns["resolve_world"], ns["display_world"]
    assert norm("Crom's") == "croms"
    assert norm("") == "" and norm(None) == ""
    assert resolve("gwydion") == (15, "gwydion")
    assert resolve("  GWYDION ") == (15, "gwydion")
    assert resolve("8") == (8, None)            # raw id passes through
    assert resolve("99999") == (99999, None)
    assert resolve("notaworld") == (None, None)
    assert resolve("") == (None, None)
    assert resolve(None) == (None, None)
    assert disp(15) == "Gwydion"
    assert disp(8) == "Crom"
    assert disp(99999) == "World 99999"
    assert disp("abc") == "World abc"
    print("ok: normalize/resolve/display world against real CH_WORLDS")


# ─── boss name + window + date parsing (real BOSS_* data) ───────────────────

def test_boss_name_helpers():
    ns = load(["boss_normalize_name", "parse_boss_input", "boss_display_name",
               "BOSS_NAMES", "BOSS_ALIASES"])
    bnn, pbi, bdn = ns["boss_normalize_name"], ns["parse_boss_input"], ns["boss_display_name"]
    assert bnn("Proteus Prime!") == "proteusprime"
    assert pbi("prime") == 103028
    assert pbi("Bloodthorn") == 141966
    assert pbi("Gele") == 102982
    assert pbi("103027") == 103027          # numeric id passes through
    assert pbi("unknownboss") is None
    assert bdn(102982) == "Gelebron"
    assert bdn(999) == "BossId 999"
    assert bdn("abc") == "BossId 0"         # non-int coerced to 0
    print("ok: boss normalize / alias resolve / display against real BOSS_* data")


def test_boss_window_parsing():
    ns = load(["_boss_parse_window", "_boss_extract_window", "_BOSS_WINDOW_RE"])
    pw, ew = ns["_boss_parse_window"], ns["_boss_extract_window"]
    assert pw("7d") == timedelta(days=7)
    assert pw("4w") == timedelta(weeks=4)
    assert pw("6m") == timedelta(days=180)
    assert pw("1y") == timedelta(days=365)
    assert pw("all") is None
    assert pw("") is None
    assert pw("3x") is None
    assert ew("7d crom") == ("7d", "crom")
    assert ew("crom 7d") == ("7d", "crom")
    assert ew("crom danu 4w") == ("4w", "crom danu")
    assert ew("crom") == (None, "crom")
    assert ew("") == (None, "")
    print("ok: _boss_parse_window / _boss_extract_window")


def test_boss_date_parsing():
    ranges = [(date(2026, 2, 9), date(2026, 2, 12))]
    ns = load(["_boss_parse_kill_date", "_boss_is_excluded_date"],
              _BOSS_EXCLUDED_DATE_RANGES_PARSED=ranges)
    pkd, excl = ns["_boss_parse_kill_date"], ns["_boss_is_excluded_date"]
    assert pkd("2026-02-10") == date(2026, 2, 10)
    assert pkd("2026-02-10T12:30:00") == date(2026, 2, 10)
    assert pkd("2026-02-10 12:30") == date(2026, 2, 10)
    assert pkd("garbage") is None
    assert pkd("") is None
    assert excl("2026-02-10") is True       # inside the excluded range
    assert excl("2026-02-12") is True       # inclusive end
    assert excl("2026-02-13") is False      # just outside
    assert excl("2026-01-01") is False
    assert excl("garbage") is False
    print("ok: _boss_parse_kill_date / _boss_is_excluded_date")


# ─── A1 cell-reference parsing ─────────────────────────────────────────────

def test_parse_a1():
    ns = load(["_parse_a1"])
    pa = ns["_parse_a1"]
    assert pa("A1") == (1, 1)
    assert pa("G5") == (5, 7)
    assert pa("Z9") == (9, 26)
    assert pa("AA12") == (12, 27)
    assert pa("AB100") == (100, 28)
    print("ok: _parse_a1 maps A1 notation to (row, col)")


# ─── role / setup authorization (fake member objects) ──────────────────────

class _FakeRole:
    def __init__(self, name):
        self.name = name


class _FakePerms:
    def __init__(self, administrator=False):
        self.administrator = administrator


class _FakeMember:
    def __init__(self, role_names=(), administrator=False):
        self.roles = [_FakeRole(n) for n in role_names]
        self.guild_permissions = _FakePerms(administrator)


def test_role_and_setup_auth():
    ns = load(["_member_has_role_named", "is_server_setup_authorized"])
    has_role, authorized = ns["_member_has_role_named"], ns["is_server_setup_authorized"]

    assert has_role(_FakeMember(["General", "Guardian"]), "general") is True   # case-insensitive
    assert has_role(_FakeMember(["General"]), "Winston Admin") is False
    assert has_role(None, "General") is False
    assert has_role(_FakeMember(["General"]), "") is False

    # admin permission alone authorizes
    assert authorized(_FakeMember(administrator=True), None) is True
    # named admin roles authorize
    assert authorized(_FakeMember(["Winston Admin"]), None) is True
    assert authorized(_FakeMember(["REDALiCE"]), None) is True
    # the guild's configured setup_role authorizes
    assert authorized(_FakeMember(["Officer"]), {"setup_role": "Officer"}) is True
    # a plain member with no matching role / entry is denied
    assert authorized(_FakeMember(["Member"]), {"setup_role": "Officer"}) is False
    assert authorized(_FakeMember(["Member"]), None) is False
    assert authorized(None, None) is False
    print("ok: _member_has_role_named / is_server_setup_authorized")


_TESTS = [
    test_safe_float_and_int,
    test_pad_row,
    test_sanitize_cell,
    test_tobool_and_time_to_seconds,
    test_parse_text,
    test_find_name,
    test_not_found_message,
    test_parse_deduct_args,
    test_loot_next_col,
    test_world_helpers,
    test_boss_name_helpers,
    test_boss_window_parsing,
    test_boss_date_parsing,
    test_parse_a1,
    test_role_and_setup_auth,
]


if __name__ == "__main__":
    for t in _TESTS:
        t()
    print(f"\nALL {len(_TESTS)} HELPER TESTS PASSED")
