"""Live read-only access to the same master spreadsheet the bot uses.

Reuses account 4's service-account credentials (the bot's read-only
"lia-leaderboard-bot") and the same pool -> worksheet-index mapping. The only
thing this module does is answer: "for this KP pool and this typed name, what is
the real roster name and how much KP do they currently have?" — which is exactly
the affordability check $sendbid / $deduct perform (Current = column 7).

It deliberately does NOT import the bot ("gwydion dkp.py"): the bot opens every
sheet across five accounts at import time. We open one account, read-only.

If gspread or the credentials file are missing this raises SheetUnavailable with
a clear message, so the GUI can fall back to offline (no-validation) resolving.
"""

import os
import difflib

# Pool -> worksheet index in the master spreadsheet (mirrors KP_WORKSHEETS /
# the "Google Sheets Structure" table in CLAUDE.md). Roster is index 0.
POOL_WS_INDEX = {
    "VKP": 1, "GKP": 2, "PKP": 3, "AKP": 4,
    "RBPPUNOX": 5, "DPKP": 6, "RBPP": 7,
}
ROSTER_WS_INDEX = 0

# Same master sheet + account-4 (read-only) creds the bot uses.
MAIN_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Izu2wSmi0aEQCWTvfLAXX0ucXR2223ILzFxTiQXcl80/edit#gid=0"
READ_CREDS_FILENAME = "paranoid-kp-bot-b724a91cd608.json"

# Column layout (1-based) of every KP worksheet: name in col 1, Current in col 7.
NAME_COL = 1
ATTENDANCE_COL = 3   # "Attendance %" — RBPP 30-day % (returned as a fraction)
EARNED_COL = 4       # "Earned" — used as lifetime RBPP
CURRENT_COL = 7

# Roster worksheet columns (0-based, matches the live header).
ROS_NAME = 0
ROS_MAIN = 2         # boolean: is this toon a main?
ROS_LEVEL = 3
ROS_MAIN_CHAR = 6    # the player's main toon name


class SheetUnavailable(RuntimeError):
    """Raised when gspread isn't installed or the creds file can't be found."""


def _find_creds():
    """Locate the account-4 creds JSON. Checks (in order): an explicit
    BIDTOOL_CREDS env var, the repo root (parent of this folder), and the cwd."""
    env = os.getenv("BIDTOOL_CREDS")
    if env and os.path.isfile(env):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(here), READ_CREDS_FILENAME),  # repo root
        os.path.join(here, READ_CREDS_FILENAME),                   # bidtool/
        os.path.join(os.getcwd(), READ_CREDS_FILENAME),            # cwd
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    raise SheetUnavailable(
        "Could not find the read-only credentials file "
        f"'{READ_CREDS_FILENAME}'. Put it in the project root next to "
        "'gwydion dkp.py', or set the BIDTOOL_CREDS environment variable to its "
        "full path."
    )


# ── find_name: copied verbatim from the bot so name matching is identical ───
# (Keeping a copy avoids importing the bot, which opens Sheets at import time.)
def find_name(name, namelist):
    namelist = list(set(namelist))
    if not name or not namelist:
        return None, False, False, []

    name_lower = name.lower()
    name_compact = name_lower.replace(" ", "")

    for candidate in namelist:
        if name_lower == candidate.lower():
            return candidate, True, False, []

    for candidate in namelist:
        if name_compact == candidate.lower().replace(" ", ""):
            return candidate, True, True, []

    prefix_matches = [c for c in namelist if c.lower().replace(" ", "").startswith(name_compact)]
    if len(prefix_matches) == 1:
        return prefix_matches[0], False, True, []
    if prefix_matches:
        return None, False, False, prefix_matches

    substr_matches = [c for c in namelist if name_compact in c.lower().replace(" ", "")]
    if len(substr_matches) == 1:
        return substr_matches[0], False, True, []
    if substr_matches:
        return None, False, False, substr_matches

    if len(name_compact) >= 3:
        scored = []
        for candidate in namelist:
            ratio = difflib.SequenceMatcher(None, name_compact, candidate.lower().replace(" ", "")).ratio()
            scored.append((candidate, ratio))
        scored.sort(key=lambda x: x[1], reverse=True)

        if len(scored) >= 2:
            best_name, best_score = scored[0]
            second_score = scored[1][1]
            if best_score >= 0.75 and (best_score - second_score) >= 0.10:
                return best_name, False, True, []
        elif len(scored) == 1 and scored[0][1] >= 0.75:
            return scored[0][0], False, True, []

    return None, False, False, []


def _safe_float(value):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _as_bool(value):
    """The roster 'Main' column comes back as a real bool (unformatted) or a
    TRUE/FALSE string. Returns True/False, or None if it's blank/unrecognised."""
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


class SheetReader:
    """Opens the master sheet once and serves cached per-pool balance lookups."""

    def __init__(self, creds_path=None):
        try:
            import gspread  # noqa: F401  (imported lazily so offline mode needs no install)
        except ImportError as e:
            raise SheetUnavailable(
                "The 'gspread' package isn't installed. Install it with "
                "'pip install gspread' to validate bids against the live sheet, "
                "or resolve offline (uncheck 'validate against live sheet')."
            ) from e
        import gspread

        self._creds_path = creds_path or _find_creds()
        gc = gspread.service_account(filename=self._creds_path)
        self._sheet = gc.open_by_url(MAIN_SHEET_URL)
        self._worksheets = self._sheet.worksheets()
        self._values_cache = {}   # ws_index -> list[list[str]]
        self._roster_names = None
        self._roster_index = None     # name_lower -> roster row
        self._rbpp_index = None       # name_lower -> RBPP row

    def _values(self, ws_index):
        if ws_index not in self._values_cache:
            ws = self._worksheets[ws_index]
            # UNFORMATTED so "Current" comes back as a number, not "1,234".
            self._values_cache[ws_index] = ws.get_all_values(
                value_render_option="UNFORMATTED_VALUE"
            )
        return self._values_cache[ws_index]

    def roster_names(self):
        if self._roster_names is None:
            rows = self._values(ROSTER_WS_INDEX)
            self._roster_names = [
                str(r[0]).strip() for r in rows[1:] if r and str(r[0]).strip()
            ]
        return self._roster_names

    def _roster_row(self, name_lower):
        if self._roster_index is None:
            self._roster_index = {}
            for row in self._values(ROSTER_WS_INDEX)[1:]:
                if row and str(row[ROS_NAME]).strip():
                    self._roster_index[str(row[ROS_NAME]).strip().lower()] = row
        return self._roster_index.get(name_lower)

    def _rbpp_row(self, name_lower):
        if self._rbpp_index is None:
            self._rbpp_index = {}
            for row in self._values(POOL_WS_INDEX["RBPP"])[1:]:
                if row and str(row[NAME_COL - 1]).strip():
                    self._rbpp_index[str(row[NAME_COL - 1]).strip().lower()] = row
        return self._rbpp_index.get(name_lower)

    def lookup(self, pool, name):
        """Full toon profile for use as the resolver's `lookup` callable.

        Returns a dict (see bid_resolver for the contract). canonical is None for
        an unknown name; balance is None when the toon has no row in `pool`.
        """
        pool = pool.upper()
        canonical, _caps, _spaces, suggestions = find_name(name, self.roster_names())
        if canonical is None:
            return {"canonical": None, "suggestions": suggestions}

        target = canonical.strip().lower()

        # Balance in the requested pool.
        balance = None
        ws_index = POOL_WS_INDEX.get(pool)
        if ws_index is not None:
            for row in self._values(ws_index)[1:]:
                if row and str(row[NAME_COL - 1]).strip().lower() == target:
                    balance = _safe_float(row[CURRENT_COL - 1]) if len(row) >= CURRENT_COL else 0.0
                    break

        # Roster profile (level + main/alt).
        level = is_main = main_name = None
        ros = self._roster_row(target)
        if ros:
            if len(ros) > ROS_LEVEL:
                try:
                    level = int(float(ros[ROS_LEVEL]))
                except (TypeError, ValueError):
                    level = None
            if len(ros) > ROS_MAIN:
                is_main = _as_bool(ros[ROS_MAIN])
            if len(ros) > ROS_MAIN_CHAR:
                main_name = str(ros[ROS_MAIN_CHAR]).strip() or None

        # RBPP profile (30-day % + lifetime Earned).
        rbpp_pct = rbpp_earned = None
        rb = self._rbpp_row(target)
        if rb:
            if len(rb) >= ATTENDANCE_COL:
                rbpp_pct = _safe_float(rb[ATTENDANCE_COL - 1])
            if len(rb) >= EARNED_COL:
                rbpp_earned = _safe_float(rb[EARNED_COL - 1])

        return {
            "canonical": canonical, "suggestions": [], "balance": balance,
            "level": level, "is_main": is_main, "main_name": main_name,
            "rbpp_pct": rbpp_pct, "rbpp_earned": rbpp_earned,
        }
