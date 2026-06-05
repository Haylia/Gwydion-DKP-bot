import uuid
import discord
import random
import os
import glob
import gspread
import pandas as pd
from datetime import datetime as dt, timezone, timedelta, time as dtime
import time
import ast
import pytesseract
from PIL import Image
import requests
import aiohttp
from io import BytesIO
import re
import difflib
import cv2
import numpy as np
import asyncio
import threading
import traceback
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

import logging
# Toggle debug logging by setting environment variable DEBUG=1 or DEBUG=true
DEBUG = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO, format="%(asctime)s %(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("gwydion")
from discord.ext import commands, tasks
from discord import guild, embeds, Embed, InteractionResponse
from discord.utils import get
intents = discord.Intents.all()
client = commands.Bot(command_prefix = '$', intents = intents, case_insensitive = True)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─── Service-account spreadsheet access (opened concurrently) ──────────────
# Five independent service accounts (each its own creds + gspread Client) share
# the master spreadsheet; accounts 3 and 4 also open secondary sheets. gspread
# is blocking, so we open every account on its own thread — the dozen-odd HTTP
# round-trips happen concurrently instead of serially. Within an account we pull
# every tab in ONE metadata call via .worksheets() instead of one
# get_worksheet(i) per tab (each of which re-fetches the whole sheet's metadata).
from concurrent.futures import ThreadPoolExecutor
from gspread.exceptions import APIError

_MAIN_SHEET = "https://docs.google.com/spreadsheets/d/1Izu2wSmi0aEQCWTvfLAXX0ucXR2223ILzFxTiQXcl80/edit#gid=0"

# (creds filename, [spreadsheet urls]) per account, in account order 1..5.
_ACCOUNT_SPECS = [
    ("paranoid-kp-bot-43a1e7152411.json", [_MAIN_SHEET]),  # 1 general kp use (lia-paranoid)
    ("paranoid-kp-bot-513a901effbc.json", [_MAIN_SHEET]),  # 2 rbpp (lia-bkp-bot)
    ("paranoid-kp-bot-29090cc5a87a.json", [                # 3 loot and logging (lia-dkp-bot)
        _MAIN_SHEET,
        "https://docs.google.com/spreadsheets/d/1GFWWkCs5jJNbgt8b_rizyOv8qIGdKh4550B5EaDtM_k/edit#gid=0",
    ]),
    ("paranoid-kp-bot-b724a91cd608.json", [                # 4 clan member reads (lia-leaderboard-bot)
        _MAIN_SHEET,
        "https://docs.google.com/spreadsheets/d/1EjAlbyeN5RnddzXNtP0X3-agTN7v4levuqoEGPujiEI/edit?gid=286347323#gid=286347323",
        "https://docs.google.com/spreadsheets/d/1FbfNkF9SkD0A8a61ChoKvcG88yC2vpaHL8ffm37TSb8/edit#gid=0",
    ]),
    ("paranoid-kp-bot-410d8c0e26d1.json", [_MAIN_SHEET]),  # 5 admin use (lia-reaping-bot)
]

def _open_account(spec):
    """Authenticate one service account and open its spreadsheet(s), pulling every
    worksheet per sheet in a single metadata call. Runs in its own thread.
    Returns (client, [(spreadsheet, [worksheet, ...]), ...])."""
    filename, urls = spec
    gc = gspread.service_account(filename=filename)
    opened = []
    for url in urls:
        sh = gc.open_by_url(url)
        opened.append((sh, sh.worksheets()))
    return gc, opened

print("opening service-account spreadsheets in parallel...")
with ThreadPoolExecutor(max_workers=len(_ACCOUNT_SPECS)) as _pool:
    # map() preserves input order and re-raises any worker exception here, so a
    # bad creds file / unshared sheet still aborts startup with a clear trace.
    _accounts = list(_pool.map(_open_account, _ACCOUNT_SPECS))
for _n in range(len(_accounts)):
    print("accessing the spreadsheet for account " + str(_n + 1))

# Bind clients, spreadsheets and worksheet handles to the names the rest of the
# file expects. worksheets()[i] is the same tab get_worksheet(i) returned.
googleacc1, _open1 = _accounts[0]
googleacc2, _open2 = _accounts[1]
googleacc3, _open3 = _accounts[2]
googleacc4, _open4 = _accounts[3]
googleacc5, _open5 = _accounts[4]

bot1sheet, _ws1 = _open1[0]
bot2sheet, _ws2 = _open2[0]
bot3sheet, _ws3 = _open3[0]
bot3sheet2, _ws3b = _open3[1]
bot4sheet, _ws4 = _open4[0]
bot4sheet2, _ws4b = _open4[1]
bot4sheet3, _ws4c = _open4[2]
bot5sheet, _ws5 = _open5[0]

bot1ws1, bot1ws2, bot1ws3, bot1ws4, bot1ws5, bot1ws6, bot1ws7, bot1ws8, bot1ws9, bot1ws10, bot1ws11 = _ws1[:11]
bot2ws1, bot2ws2, bot2ws3, bot2ws4, bot2ws5, bot2ws6, bot2ws7, bot2ws8, bot2ws9, bot2ws10, bot2ws11 = _ws2[:11]
bot3ws1, bot3ws2, bot3ws3, bot3ws4, bot3ws5, bot3ws6, bot3ws7, bot3ws8, bot3ws9, bot3ws10, bot3ws11 = _ws3[:11]
bot3ws12, bot3ws13 = _ws3b[0], _ws3b[1]
bot4ws1, bot4ws2, bot4ws3, bot4ws4, bot4ws5, bot4ws6, bot4ws7, bot4ws8, bot4ws9, bot4ws10, bot4ws11 = _ws4[:11]
bot4ws12, bot4ws13 = _ws4b[0], _ws4b[1]
bot4ws14 = _ws4c[0]
bot5ws1, bot5ws2, bot5ws3, bot5ws4, bot5ws5, bot5ws6, bot5ws7, bot5ws8, bot5ws9, bot5ws10, bot5ws11, bot5ws12, bot5ws13 = _ws5[:13]
print("accessing the spreadsheet for all accounts complete")

# Pool of raw worksheets per sheet index (same data, different service accounts),
# reused straight from each account's worksheet list — no extra metadata fetches.
# CachingWorksheet skips the sibling that is its own underlying worksheet (`is`).
_WS_POOL = {}
for _idx in range(11):
    _WS_POOL[_idx] = [_ws1[_idx], _ws2[_idx], _ws3[_idx], _ws4[_idx], _ws5[_idx]]

class CachedCell:
    """Lightweight Cell object returned by CachingWorksheet.find() and .cell()."""
    __slots__ = ('row', 'col', 'value')

    def __init__(self, row, col, value=''):
        self.row = row
        self.col = col
        self.value = value

    def __repr__(self):
        return f'CachedCell(row={self.row}, col={self.col}, value={self.value!r})'

    def __eq__(self, other):
        if other is None:
            return False
        return self.row == other.row and self.col == other.col and self.value == other.value

    def __bool__(self):
        return True

def _parse_a1(label):
    """Parse A1 notation (e.g., 'G5', 'AA12') into (row, col) 1-indexed tuple."""
    col_str = ''
    row_str = ''
    for ch in label:
        if ch.isalpha():
            col_str += ch
        else:
            row_str += ch
    col = 0
    for ch in col_str.upper():
        col = col * 26 + (ord(ch) - ord('A') + 1)
    return int(row_str), col

# Global registry: maps a registry key -> list of CachingWorksheet instances.
# For main spreadsheet worksheets: key = sheet_index (0-10).
# For secondary worksheets: key = unique string like "bot3ws12".
_CACHE_REGISTRY = {}

def _invalidate_siblings(registry_key):
    """Mark all CachingWorksheet instances for this sheet as stale."""
    for cws in _CACHE_REGISTRY.get(registry_key, []):
        object.__setattr__(cws, '_stale', True)
        object.__setattr__(cws, '_stale_unformatted', True)

class CachingWorksheet:
    """Wraps a gspread Worksheet with in-memory caching and rate-limit retry.

    Read methods serve from a cached get_all_values() snapshot.
    Write methods pass through to the API (with retry on 429), then mark
    all sibling caches for the same sheet as stale.
    """

    def __init__(self, ws, siblings=None, registry_key=None, default_ttl=300):
        object.__setattr__(self, '_ws', ws)
        object.__setattr__(self, '_siblings', siblings or [])
        object.__setattr__(self, '_registry_key', registry_key)
        object.__setattr__(self, '_data', None)              # List[List[str]] FORMATTED
        object.__setattr__(self, '_data_unformatted', None)  # List[List] UNFORMATTED (lazy)
        object.__setattr__(self, '_stale', True)
        object.__setattr__(self, '_stale_unformatted', True)
        object.__setattr__(self, '_loaded_at', 0.0)
        object.__setattr__(self, '_loaded_at_unformatted', 0.0)
        object.__setattr__(self, '_default_ttl', default_ttl)
        if registry_key is not None:
            _CACHE_REGISTRY.setdefault(registry_key, []).append(self)

    # ── API call with rate-limit retry ───────────────────────────────────

    def _api_call(self, method_name, *args, **kwargs):
        """Call a method on the underlying worksheet with 429 retry via siblings."""
        try:
            return getattr(self._ws, method_name)(*args, **kwargs)
        except APIError as e:
            if e.response.status_code != 429:
                raise
            logger.warning(f"Rate limited on account, trying fallback for {method_name}...")
            for sib in self._siblings:
                if sib is self._ws:
                    continue
                try:
                    return getattr(sib, method_name)(*args, **kwargs)
                except APIError as e2:
                    if e2.response.status_code == 429:
                        continue
                    raise
            logger.warning("All accounts rate limited, waiting 10s...")
            time.sleep(10)
            return getattr(self._ws, method_name)(*args, **kwargs)

    # ── Cache management ─────────────────────────────────────────────────

    def _ensure_fresh(self):
        """Refresh the formatted cache if stale, unloaded, or TTL expired."""
        now = time.time()
        if (self._stale or self._data is None
                or (now - self._loaded_at) > self._default_ttl):
            logger.debug(f"Refreshing formatted cache for registry_key={self._registry_key}")
            object.__setattr__(self, '_data', self._api_call('get_all_values'))
            object.__setattr__(self, '_loaded_at', now)
            object.__setattr__(self, '_stale', False)

    def _ensure_fresh_unformatted(self):
        """Refresh the unformatted cache if stale, unloaded, or TTL expired."""
        now = time.time()
        if (self._stale_unformatted or self._data_unformatted is None
                or (now - self._loaded_at_unformatted) > self._default_ttl):
            logger.debug(f"Refreshing unformatted cache for registry_key={self._registry_key}")
            try:
                raw = self._api_call('get_all_values', value_render_option='UNFORMATTED_VALUE')
            except TypeError:
                # Older gspread versions: get_all_values() may not accept the kwarg
                raw = self._api_call('get', value_render_option='UNFORMATTED_VALUE')
            object.__setattr__(self, '_data_unformatted', raw if raw else [])
            object.__setattr__(self, '_loaded_at_unformatted', now)
            object.__setattr__(self, '_stale_unformatted', False)

    def _mark_all_stale(self):
        """Invalidate caches for ALL worksheet instances sharing this sheet."""
        if self._registry_key is not None:
            _invalidate_siblings(self._registry_key)
        else:
            object.__setattr__(self, '_stale', True)
            object.__setattr__(self, '_stale_unformatted', True)

    def refresh(self):
        """Force-refresh this worksheet's cache on next read."""
        object.__setattr__(self, '_stale', True)
        object.__setattr__(self, '_stale_unformatted', True)

    # ── Read methods (served from cache) ─────────────────────────────────

    def get_all_values(self, **kwargs):
        self._ensure_fresh()
        return [list(row) for row in self._data]

    def col_values(self, col):
        self._ensure_fresh()
        result = []
        for row in self._data:
            if col <= len(row):
                result.append(row[col - 1])
            else:
                result.append('')
        return result

    def row_values(self, row, value_render_option=None):
        if value_render_option == 'UNFORMATTED_VALUE':
            self._ensure_fresh_unformatted()
            data = self._data_unformatted
        else:
            self._ensure_fresh()
            data = self._data
        if data and 1 <= row <= len(data):
            return list(data[row - 1])
        return []

    def cell(self, row, col):
        self._ensure_fresh()
        if self._data and 1 <= row <= len(self._data):
            r = self._data[row - 1]
            if 1 <= col <= len(r):
                return CachedCell(row, col, r[col - 1])
        return CachedCell(row, col, '')

    def acell(self, label):
        row, col = _parse_a1(label)
        return self.cell(row, col)

    def find(self, value, in_column=None):
        self._ensure_fresh()
        search_val = str(value)
        for r_idx, row in enumerate(self._data, start=1):
            if in_column is not None:
                if in_column <= len(row) and row[in_column - 1] == search_val:
                    return CachedCell(r_idx, in_column, row[in_column - 1])
            else:
                for c_idx, cell_val in enumerate(row, start=1):
                    if cell_val == search_val:
                        return CachedCell(r_idx, c_idx, cell_val)
        return None

    # ── Write methods (pass through to API, then invalidate) ─────────────

    def update_cell(self, row, col, value):
        result = self._api_call('update_cell', row, col, value)
        self._mark_all_stale()
        return result

    def update(self, values, *args, **kwargs):
        result = self._api_call('update', values, *args, **kwargs)
        self._mark_all_stale()
        return result

    def append_row(self, values, **kwargs):
        result = self._api_call('append_row', values, **kwargs)
        self._mark_all_stale()
        return result

    def delete_rows(self, start, end=None):
        if end is not None:
            result = self._api_call('delete_rows', start, end)
        else:
            result = self._api_call('delete_rows', start)
        self._mark_all_stale()
        return result

    def update_acell(self, label, value):
        result = self._api_call('update_acell', label, value)
        self._mark_all_stale()
        return result

    # ── Async siblings (dispatch sync work to a worker thread) ───────────
    # Awaitable variants of the I/O-bound methods. Reads still serve from
    # cache (cheap) but the *first* read after staleness/TTL is an HTTP call,
    # so async wrappers around reads keep the event loop unblocked too.

    async def aupdate_cell(self, row, col, value):
        return await asyncio.to_thread(self.update_cell, row, col, value)

    async def aupdate(self, values, *args, **kwargs):
        return await asyncio.to_thread(self.update, values, *args, **kwargs)

    async def aappend_row(self, values, **kwargs):
        return await asyncio.to_thread(self.append_row, values, **kwargs)

    async def adelete_rows(self, start, end=None):
        return await asyncio.to_thread(self.delete_rows, start, end)

    async def aupdate_acell(self, label, value):
        return await asyncio.to_thread(self.update_acell, label, value)

    async def afind(self, value, in_column=None):
        return await asyncio.to_thread(self.find, value, in_column)

    async def aacell(self, label):
        return await asyncio.to_thread(self.acell, label)

    async def acell_(self, row, col):
        return await asyncio.to_thread(self.cell, row, col)

    async def acol_values(self, col):
        return await asyncio.to_thread(self.col_values, col)

    async def arow_values(self, row, value_render_option=None):
        return await asyncio.to_thread(self.row_values, row, value_render_option)

    async def aget_all_values(self, **kwargs):
        return await asyncio.to_thread(self.get_all_values, **kwargs)

    async def arefresh(self):
        return await asyncio.to_thread(self.refresh)

    # ── Proxy unknown attributes to underlying worksheet ─────────────────

    def __getattr__(self, name):
        attr = getattr(self._ws, name)
        if not callable(attr):
            return attr
        # Wrap unknown callable methods with retry logic
        def wrapper(*args, **kwargs):
            return self._api_call(name, *args, **kwargs)
        return wrapper

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError(f"Cannot set attribute '{name}' on CachingWorksheet")

def _wrap_ws(ws, sheet_index):
    """Wrap a worksheet with caching and rate-limit retry using sibling accounts."""
    siblings = _WS_POOL.get(sheet_index, [])
    return CachingWorksheet(ws, siblings=siblings, registry_key=sheet_index)

# Wrap all main spreadsheet worksheets with fallback retry
bot1ws1  = _wrap_ws(bot1ws1, 0);  bot1ws2  = _wrap_ws(bot1ws2, 1);  bot1ws3  = _wrap_ws(bot1ws3, 2)
bot1ws4  = _wrap_ws(bot1ws4, 3);  bot1ws5  = _wrap_ws(bot1ws5, 4);  bot1ws6  = _wrap_ws(bot1ws6, 5)
bot1ws7  = _wrap_ws(bot1ws7, 6);  bot1ws8  = _wrap_ws(bot1ws8, 7);  bot1ws9  = _wrap_ws(bot1ws9, 8)
bot1ws10 = _wrap_ws(bot1ws10, 9); bot1ws11 = _wrap_ws(bot1ws11, 10)
bot2ws1  = _wrap_ws(bot2ws1, 0);  bot2ws2  = _wrap_ws(bot2ws2, 1);  bot2ws3  = _wrap_ws(bot2ws3, 2)
bot2ws4  = _wrap_ws(bot2ws4, 3);  bot2ws5  = _wrap_ws(bot2ws5, 4);  bot2ws6  = _wrap_ws(bot2ws6, 5)
bot2ws7  = _wrap_ws(bot2ws7, 6);  bot2ws8  = _wrap_ws(bot2ws8, 7);  bot2ws9  = _wrap_ws(bot2ws9, 8)
bot2ws10 = _wrap_ws(bot2ws10, 9); bot2ws11 = _wrap_ws(bot2ws11, 10)
bot3ws1  = _wrap_ws(bot3ws1, 0);  bot3ws2  = _wrap_ws(bot3ws2, 1);  bot3ws3  = _wrap_ws(bot3ws3, 2)
bot3ws4  = _wrap_ws(bot3ws4, 3);  bot3ws5  = _wrap_ws(bot3ws5, 4);  bot3ws6  = _wrap_ws(bot3ws6, 5)
bot3ws7  = _wrap_ws(bot3ws7, 6);  bot3ws8  = _wrap_ws(bot3ws8, 7);  bot3ws9  = _wrap_ws(bot3ws9, 8)
bot3ws10 = _wrap_ws(bot3ws10, 9); bot3ws11 = _wrap_ws(bot3ws11, 10)
bot4ws1  = _wrap_ws(bot4ws1, 0);  bot4ws2  = _wrap_ws(bot4ws2, 1);  bot4ws3  = _wrap_ws(bot4ws3, 2)
bot4ws4  = _wrap_ws(bot4ws4, 3);  bot4ws5  = _wrap_ws(bot4ws5, 4);  bot4ws6  = _wrap_ws(bot4ws6, 5)
bot4ws7  = _wrap_ws(bot4ws7, 6);  bot4ws8  = _wrap_ws(bot4ws8, 7);  bot4ws9  = _wrap_ws(bot4ws9, 8)
bot4ws10 = _wrap_ws(bot4ws10, 9); bot4ws11 = _wrap_ws(bot4ws11, 10)
bot5ws1  = _wrap_ws(bot5ws1, 0);  bot5ws2  = _wrap_ws(bot5ws2, 1);  bot5ws3  = _wrap_ws(bot5ws3, 2)
bot5ws4  = _wrap_ws(bot5ws4, 3);  bot5ws5  = _wrap_ws(bot5ws5, 4);  bot5ws6  = _wrap_ws(bot5ws6, 5)
bot5ws7  = _wrap_ws(bot5ws7, 6);  bot5ws8  = _wrap_ws(bot5ws8, 7);  bot5ws9  = _wrap_ws(bot5ws9, 8)
bot5ws10 = _wrap_ws(bot5ws10, 9); bot5ws11 = _wrap_ws(bot5ws11, 10)
print("rate-limit fallback wrapping complete")

# Wrap secondary spreadsheet worksheets (no sibling pool — single account each)
bot3ws12 = CachingWorksheet(bot3ws12, registry_key="bot3ws12")
bot3ws13 = CachingWorksheet(bot3ws13, registry_key="bot3ws13")
# bot4ws12 and bot4ws13 left unwrapped — DG sheets always do fresh reads
bot4ws14 = CachingWorksheet(bot4ws14, registry_key="bot4ws14")
print("secondary worksheets wrapped")

# Pre-populate all caches at startup so the first command has zero latency.
# One get_all_values() per sheet (data is identical across the sibling
# accounts). The 5 accounts warm concurrently, but each sheet's read is pinned
# to a single account and an account's reads run sequentially on one thread —
# gspread's per-account requests.Session isn't safe for concurrent use.
# Round-robining the reader across accounts also spreads the load so we don't
# funnel every warm read through account 1 and trip a 429. Best-effort: a sheet
# that fails to warm just loads lazily on first access instead of crashing boot.
print("warming worksheet caches...")

def _warm_one(instances, fetcher_idx):
    """Load one sheet via the chosen sibling, then share its data to the rest."""
    fetcher = instances[fetcher_idx]
    try:
        fetcher._ensure_fresh()
    except Exception as e:
        logger.warning(f"cache warm failed for {fetcher._registry_key}: {e}")
        return
    for sib in instances:
        if sib is not fetcher:
            object.__setattr__(sib, '_data', fetcher._data)
            object.__setattr__(sib, '_stale', False)

# Bucket each sheet's warm job by the account whose session performs the read,
# so a thread only ever touches one account's session.
_warm_by_account = {}
for _rk, _instances in _CACHE_REGISTRY.items():
    if not _instances:
        continue
    if len(_instances) > 1:
        # main sheet index (int key, one instance per account): round-robin the
        # reader across accounts so warm reads spread evenly.
        _fidx = _rk % len(_instances)
        _acc = _fidx
    else:
        # secondary sheet ("botNwsM" key): only that one account can read it.
        _fidx = 0
        _acc = int(str(_rk)[3]) - 1
    _warm_by_account.setdefault(_acc, []).append((_instances, _fidx))

def _warm_account_queue(jobs):
    for _insts, _fi in jobs:
        _warm_one(_insts, _fi)

with ThreadPoolExecutor(max_workers=max(1, len(_warm_by_account))) as _wpool:
    list(_wpool.map(_warm_account_queue, _warm_by_account.values()))
print("worksheet caches warmed")

vkp_bosses = {}
gkp_bosses = {}
pkp_bosses = {}
akp_bosses = {}
rbppunox_bosses = {}
dpkp_bosses = {}
rbpp_bosses = {}

BOSS_DICTS = {
    "VKP": vkp_bosses,
    "GKP": gkp_bosses,
    "PKP": pkp_bosses,
    "AKP": akp_bosses,
    "RBPPUNOX": rbppunox_bosses,
    "DPKP": dpkp_bosses,
    "RBPP": rbpp_bosses,
}

BOSSES_FILE = "bosses.txt"

def load_bosses():
    """Load boss mappings from bosses.txt into the global dicts. Tolerant of a
    missing or partially-corrupt file so a bad write can't stop the bot booting;
    unparseable lines are skipped with a warning."""
    for d in BOSS_DICTS.values():
        d.clear()
    current_pool = None
    try:
        with open(BOSSES_FILE, "r") as f:
            lines = f.readlines()
    except OSError as e:
        logger.warning(f"Could not read {BOSSES_FILE}: {e} — boss mappings empty until reloaded")
        return
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_pool = line[1:-1]
        elif "=" in line and current_pool in BOSS_DICTS:
            bossname, points = line.split("=", 1)
            try:
                BOSS_DICTS[current_pool][bossname.strip()] = int(points.strip())
            except ValueError:
                logger.warning(f"Skipping malformed boss line in {BOSSES_FILE}: {line!r}")

def save_bosses():
    """Save the current boss dicts back to bosses.txt atomically (temp file +
    os.replace) so a crash mid-write can't leave a corrupt/partial file."""
    tmp = BOSSES_FILE + ".tmp"
    with open(tmp, "w") as f:
        for pool in ["VKP", "GKP", "PKP", "AKP", "RBPPUNOX", "DPKP", "RBPP"]:
            f.write("[" + pool + "]\n")
            for bossname, points in BOSS_DICTS[pool].items():
                f.write(bossname + "=" + str(points) + "\n")
            f.write("\n")
    os.replace(tmp, BOSSES_FILE)

load_bosses()
print("loaded boss mappings from " + BOSSES_FILE)

KP_TYPES = ["VKP", "GKP", "PKP", "AKP", "RBPPUNOX", "DPKP", "RBPP"]
KP_WORKSHEETS = {
    "VKP":      {"read": bot4ws2, "write": bot1ws2, "admin": bot5ws2, "deduct": bot3ws2},
    "GKP":      {"read": bot4ws3, "write": bot1ws3, "admin": bot5ws3, "deduct": bot3ws3},
    "PKP":      {"read": bot4ws4, "write": bot1ws4, "admin": bot5ws4, "deduct": bot3ws4},
    "AKP":      {"read": bot4ws5, "write": bot1ws5, "admin": bot5ws5, "deduct": bot3ws5},
    "RBPPUNOX": {"read": bot4ws6, "write": bot2ws6, "admin": bot5ws6, "deduct": bot3ws6},
    "DPKP":     {"read": bot4ws7, "write": bot1ws7, "admin": bot5ws7, "deduct": bot3ws7},
    "RBPP":     {"read": bot4ws8, "write": bot2ws8, "admin": bot5ws8, "deduct": bot5ws8},
}

DURATION_REGEX = r"(\d{2}:\d{2}:\d{2})"
ROW_REGEX = r"^\s*\d*\s*([A-Za-z][A-Za-z0-9_]+).*?([\d,]{5,})\s*$"
OCR_API_KEY = os.getenv("OCR_API_KEY", "K89202162788957")
BLACKLIST = {"total", "health", "damage", "dps"}

bidslastupdate = time.time()
# Serializes bid read-modify-write across startbid/sendbid/cancelbid/bidloop so
# concurrent calls can't clobber a row or hand out a duplicate auction id.
_bid_lock = asyncio.Lock()

guilds=[814048353603813376,1116453904922726544,1215443011400376391,920411637297598484]

# ─── Early-loaded multi-server gates ──────────────────────────────────────
# Defined this high in the file because every DKP / roster command below uses
# @dkp_only as a decorator, which evaluates at import time. The richer helpers
# (is_server_setup_authorized, _require_world_for_ctx, etc.) live further down
# with the rest of the boss-leaderboard subsystem — they're only called from
# inside async command bodies, so import-order doesn't matter for them.

GWYDION_GUILD_IDS = set(guilds)


def is_gwydion_guild(guild_id):
    """True if the Discord guild is one of the four legacy Relentless guilds."""
    if guild_id is None:
        return False
    try:
        return int(guild_id) in GWYDION_GUILD_IDS
    except Exception:
        return False


def dkp_only():
    """Check decorator: command may only run in the four legacy Relentless guilds.
    Failure surfaces as commands.CheckFailure('dkp_wrong_server') so the global
    on_command_error can produce a friendly redirect to $lbhelp."""
    async def predicate(ctx):
        if is_gwydion_guild(getattr(getattr(ctx, "guild", None), "id", None)):
            return True
        raise commands.CheckFailure("dkp_wrong_server")
    return commands.check(predicate)


def author_in_gwydion_guild(author):
    """True if `author` is a member of one of the four legacy Relentless guilds,
    determined from the guilds the bot shares with them (User.mutual_guilds).
    Requires the members intent (on via Intents.all()) and the member cache."""
    try:
        return any(is_gwydion_guild(g.id) for g in getattr(author, "mutual_guilds", []))
    except Exception:
        return False


def dkp_read():
    """Check decorator for read-only KP / roster lookups. Allows the command in
    the four legacy Relentless guilds (same as @dkp_only) AND in DMs — but a DM is
    only permitted if the author is a member of one of those guilds. Reads hit the
    single master spreadsheet through the read-only service account, so no
    per-guild context is needed.

    Failures surface through on_command_error:
      'dkp_wrong_server'  -> run in a non-Relentless server
      'dkp_dm_not_member' -> DM from someone not in a Relentless server"""
    async def predicate(ctx):
        guild = getattr(ctx, "guild", None)
        if guild is None:
            if author_in_gwydion_guild(ctx.author):
                return True
            raise commands.CheckFailure("dkp_dm_not_member")
        if is_gwydion_guild(guild.id):
            return True
        raise commands.CheckFailure("dkp_wrong_server")
    return commands.check(predicate)


print("setup done")

def cached_col_values(worksheet, col, cache_key=None, ttl=None):
    """Thin wrapper — caching (including TTL) is handled by CachingWorksheet.
    cache_key and ttl kept for call-site compatibility; freshness is governed
    by the worksheet's default_ttl (300s).

    NOTE: synchronous. On cache miss / TTL expiry this issues a blocking
    Sheets call. Use `acached_col_values` from async commands so the
    event loop isn't stalled."""
    return worksheet.col_values(col)


async def acached_col_values(worksheet, col, cache_key=None, ttl=None):
    """Async sibling of `cached_col_values` — dispatches the (possibly
    blocking) col_values read to a worker thread."""
    return await asyncio.to_thread(worksheet.col_values, col)


async def sheet_call(fn, *args, **kwargs):
    """Run a blocking gspread / requests call in a worker thread so it
    does not stall the Discord event loop."""
    return await asyncio.to_thread(fn, *args, **kwargs)

def safe_float(value, default=0.0):
    """Parse a spreadsheet cell as float, tolerating blanks, '#DIV/0!' (and
    other '#...' errors), trailing '%', and junk — returns `default` instead of
    raising ValueError. Use for any column that gets mapped to numbers."""
    try:
        if value is None:
            return default
        s = str(value).strip().rstrip('%').strip()
        if s == '' or s.startswith('#'):
            return default
        return float(s)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Parse a spreadsheet cell as int, tolerating blanks/junk/'12.0'."""
    try:
        return int(safe_float(value, default))
    except (ValueError, TypeError):
        return default

def pad_row(row, length):
    """Right-pad a row (list) with '' to at least `length` cells so fixed-index
    access past the last non-empty cell doesn't IndexError. gspread trims
    trailing empties, so any row with blank trailing columns comes back short."""
    row = list(row)
    if len(row) < length:
        row += [''] * (length - len(row))
    return row

def sanitize_cell(value):
    """Neutralise spreadsheet formula injection for USER-SUPPLIED text written
    with value_input_option='USER_ENTERED': if the value begins with = + - @,
    prefix a single quote so Sheets stores it as literal text rather than
    evaluating it as a formula. Do NOT use on values that are meant to be
    formulas (e.g. the COUNTIFS strings written by $addmem)."""
    if isinstance(value, str) and value[:1] in ('=', '+', '-', '@'):
        return "'" + value
    return value

def toBool(string):
    string = string.capitalize()
    if string == "True":
        return True
    else:
        return False

def time_to_seconds(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s
    
def preprocess(img):
    try:
        print(f"DEBUG: Preprocessing image, shape={getattr(img, 'shape', None)}")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
        print("DEBUG: Preprocessing complete")
        return gray
    except Exception as e:
        print("ERROR: Error during image preprocessing")
        traceback.print_exc()
        raise

def extract_text(image_path):
    with open(image_path, "rb") as f:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": f},
            data={
                "apikey": OCR_API_KEY,
                "language": "eng",
                "isOverlayRequired": False,
                "OCREngine": 2
            },
            timeout=30
        )

    result = response.json()

    if "ParsedResults" not in result:
        raise Exception("OCR failed")

    return result["ParsedResults"][0]["ParsedText"]

def parse_text(text):
    players = []
    duration_seconds = None

    dur = re.search(DURATION_REGEX, text)
    if dur:
        duration_seconds = time_to_seconds(dur.group(1))
        print(f"DEBUG: Found duration {dur.group(1)}")

    for line in text.splitlines():
        m = re.search(ROW_REGEX, line)
        if m:
            name = m.group(1)
    
            if name.lower() in BLACKLIST:
                continue
            
            dmg = int(re.sub(r"[^\d]", "", m.group(2)))
            players.append((name, dmg))
            print(f"DEBUG: Parsed row: {name} -> {dmg}")

    print(f"DEBUG: parse_text returning duration={duration_seconds}, players={len(players)}")
    return duration_seconds, players

def process_images(paths):
    print(f"DEBUG: process_images called with {len(paths)} files: {paths}")
    all_players = {}
    fight_time = None

    for p in paths:
        print(f"DEBUG: Processing file: {p}")
        try:
            text = extract_text(p)
            duration, players = parse_text(text)
            print(f"DEBUG: File {p}: duration={duration}, players_found={len(players)}")
        except Exception as e:
            print(f"ERROR: Failed to process image {p}")
            traceback.print_exc()
            raise

        if duration:
            fight_time = duration

        for name, dmg in players:
            prev = all_players.get(name, 0)
            all_players[name] = max(prev, dmg)
            if all_players[name] != prev:
                print(f"DEBUG: Updated score for {name}: {prev} -> {all_players[name]}")

    if not fight_time:
        print("ERROR: Could not detect fight duration from any image")
        raise ValueError("Could not detect fight duration.")

    rows = []
    for name, dmg in all_players.items():
        dps = round(dmg / fight_time, 2)
        rows.append((name, dmg, dps))

    df = pd.DataFrame(rows, columns=["Player", "Damage", "DPS"])
    df = df.sort_values("Damage", ascending=False)
    df.insert(0, "Rank", range(1, len(df) + 1))
    print(f"DEBUG: Generated leaderboard DataFrame with {len(df)} rows")

    return df

def find_name(name, namelist):
    namelist = list(set(namelist))
    if not name or not namelist:
        return None, False, False, []

    name_lower = name.lower()
    name_compact = name_lower.replace(" ", "")

    # Pass 1: exact case-insensitive
    for candidate in namelist:
        if name_lower == candidate.lower():
            return candidate, True, False, []

    # Pass 2: exact match ignoring spaces
    for candidate in namelist:
        if name_compact == candidate.lower().replace(" ", ""):
            return candidate, True, True, []

    # Pass 3: prefix match (unique only)
    prefix_matches = [c for c in namelist if c.lower().replace(" ", "").startswith(name_compact)]
    if len(prefix_matches) == 1:
        return prefix_matches[0], False, True, []
    if prefix_matches:
        return None, False, False, prefix_matches

    # Pass 4: substring match (unique only)
    substr_matches = [c for c in namelist if name_compact in c.lower().replace(" ", "")]
    if len(substr_matches) == 1:
        return substr_matches[0], False, True, []
    if substr_matches:
        return None, False, False, substr_matches

    # Pass 5: edit distance (only for inputs >= 3 chars)
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

def not_found_message(name, suggestions):
    if suggestions:
        return "Could not find player '" + name + "'. Did you mean: " + ", ".join(suggestions) + "?"
    return "Could not find player '" + name + "'."
            
    
@tasks.loop(seconds=60)
async def bidloop():
    global bidslastupdate
    bidslastupdate = time.time()
    twelvehoursinseconds = 43200
    resultschannel = 1232811852811993169
    try:
        bidopentimes = await bot3ws12.acol_values(1)
        itemids = await bot3ws12.acol_values(2)
        itemnames = await bot3ws12.acol_values(3)
        itemkp = await bot3ws12.acol_values(4)
        bidstatus = await bot3ws12.acol_values(5)
        combilist = list(zip(bidopentimes, itemids, bidstatus, itemnames, itemkp))
        useritemids = await bot3ws13.acol_values(3)
        useritemstatus = await bot3ws13.acol_values(7)
        combiuserlist = list(zip(useritemids,useritemstatus))
        for i in range(1, len(combilist)):
            if combilist[i][2] == "Open" and float(time.time()) > safe_float(combilist[i][0]) + twelvehoursinseconds:
                async with _bid_lock:
                    # locate the auction by its id in column 2 (not a whole-sheet
                    # scan that could match a price/number elsewhere) and use that
                    # row for both the close-write and the results read.
                    cell = await bot3ws12.afind(combilist[i][1], in_column=2)
                    if cell is None:
                        continue
                    row_num = cell.row
                    await bot3ws12.aupdate_cell(row_num, 5, "Closed")
                    for j in range(1, len(combiuserlist)):
                        if combiuserlist[j][1] == "Open" and combiuserlist[j][0] == combilist[i][1]:
                            await bot3ws13.aupdate_cell(j + 1, 7, "Closed")
                    bidrow = await bot3ws12.arow_values(row_num)
                #cut off everything but the player name and the bids
                bidrow = bidrow[5:]
                # split the rest alternating between the player and their bid
                length = len(bidrow)
                results = []
                for k in range(length//2):
                    player = bidrow.pop(0)
                    bid = bidrow.pop(0)
                    results.append([player, bid])
                if not results:
                    continue
                results.sort(key = lambda x: safe_float(x[1]), reverse = True)
                msgtosend = "The bid for " + combilist[i][3] + " has been closed. The highest bidder was " + results[0][0] + " with a bid of " + str(results[0][1]) + " " + combilist[i][4]
                for k in range(1, len(results)):
                    msgtosend += "\n" + results[k][0] + " bid " + str(results[k][1]) + " " + combilist[i][4]
                await client.get_channel(resultschannel).send(msgtosend)

    except Exception as e:
        logger.exception("Error in bidloop")



@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    # Report which of the four legacy Relentless guilds are reachable. Has to
    # run here (not at module top level) because client.get_guild() returns
    # None until the bot is connected.
    for g in guilds:
        guild = client.get_guild(g)
        if guild:
            print(f"Connected to guild: {guild.name} (ID: {guild.id})")
        else:
            print(f"Warning: Could not find guild with ID {g}")
    bidloop.start()
    # --- Boss Leaderboard auto-poller (UTC-anchored) ---
    try:
        _migrate_state_files_if_needed()
        # Seed any world that's configured (Gwydion + every world referenced in
        # server_config.json) so a brand-new world doesn't replay every fight
        # it's ever seen on first auto-poll.
        worlds_to_seed = {GWYDION_WORLD_ID}
        for _gid, _entry in get_all_configured_guilds():
            try:
                worlds_to_seed.add(int(_entry.get("world_id", 0)))
            except Exception:
                continue
        existing_world_keys = _world_keys_in_posted_file()
        had_state = bool(existing_world_keys)
        for _wid in worlds_to_seed:
            if _wid > 0:
                initialize_posted_fights_if_needed(world_id=_wid)
        if had_state:
            try:
                count = await boss_perform_auto_check()
                if count:
                    logger.info(f"Bot-start boss catch-up: posted {count} new fight(s)")
            except Exception:
                logger.exception("Bot-start boss catch-up failed")
    except Exception:
        logger.exception("Boss state init failed on bot start")
    if not boss_poll_loop.is_running():
        boss_poll_loop.start()
        logger.info(
            "Boss poll anchored to UTC: "
            + ", ".join(t.strftime("%H:%M") for t in BOSS_POLL_ANCHOR_TIMES)
        )


@client.event
async def on_guild_join(guild):
    """Sends a setup-instructions message to new servers (skipping Gwydion legacy guilds)."""
    try:
        logger.info(f"Joined guild {guild.name} ({guild.id})")
        if is_gwydion_guild(guild.id):
            return
        msg = (
            "Thanks for adding Winston!\n\n"
            "Winston is primarily a DKP bot for the Gwydion-Relentless community, but "
            "the **boss leaderboard** features work for any Celtic Heroes server.\n\n"
            "**To get started** (Discord admin required):\n"
            "1. `$setworld <world_id_or_name>` — e.g. `$setworld 15` or `$setworld gwydion`. "
            "Run `$listworlds` for known names.\n"
            "2. `$setchannel #your-channel` — enable auto-posting of boss kills.\n"
            "3. Try `$fights`, `$sheet <boss>`, `$bossaliases`, `$bests <boss>`, "
            "`$fighthistory <player> <boss>`.\n\n"
            "Run `$lbhelp` for the full command list or `$serverinfo` to check your "
            "current configuration."
        )
        # Best-effort delivery: system channel > owner DM > silent.
        target = guild.system_channel
        if target:
            try:
                me = guild.me
                if me and target.permissions_for(me).send_messages:
                    await target.send(msg)
                    return
            except Exception:
                pass
        try:
            if guild.owner:
                await guild.owner.send(msg)
        except Exception:
            pass
    except Exception:
        logger.exception("on_guild_join handler failed")


@client.event
async def on_guild_remove(guild):
    """Auto-prunes a non-Gwydion guild's config on bot kick/leave."""
    try:
        logger.info(f"Removed from guild {guild.name} ({guild.id})")
        if is_gwydion_guild(guild.id):
            return
        if remove_server_entry(guild.id):
            logger.info(f"Cleared server_config entry for departed guild {guild.id}")
    except Exception:
        logger.exception("on_guild_remove handler failed")


@client.event
async def on_message(msg):
    if msg.author == client.user:
        return
    checkformemes = msg.content.lower()
    if checkformemes.startswith("$"):
        print("command used: " + str(msg.content) + " by " + str(msg.author))
    # format here
    # message starts with command
    # any image just google images right click copy image address
    if checkformemes == "chico":
        await msg.channel.send("is a 69 year old vegan teacher")
        await msg.channel.send("https://imgur.com/blrOjjE")
    if checkformemes == "thank you winston":
        await msg.channel.send("https://tenor.com/view/oh-yeah-winston-dance-overwatch-gorrila-gif-22531380")
    if checkformemes == "Axy":
        await msg.channel.send("STOP SPENDING MONEY")
    if checkformemes == "deez":
        await msg.channel.send("NUTS (gottem)")
    if checkformemes == "luv":
        await msg.channel.send("ily2 <3")
    if checkformemes == "jax":
        await msg.channel.send("is one sexy mofo")
    if checkformemes == "fax":
        await msg.channel.send("no printer")
    if checkformemes == "cap":
        await msg.channel.send("no cap 🧢")
    if checkformemes == "behave":
        await msg.channel.send("no promises 👀")
    if checkformemes == "m0ney":
        await msg.channel.send("go to sleep")
    if checkformemes == "sleep":
        await msg.channel.send("is for the weak")
    if checkformemes == "nobu":
        await msg.channel.send("got no bitches")
    if checkformemes == "exemp":
        await msg.channel.send("I would just like to say on behalf of Exemp that we do not condone our members causing issues with other clans and that anything said does not reflect our clan as a whole. I am in the process of talking to the parties involved to sort things out as I believe the vast majority of us want to see a fun and non-toxic environment for everyone. \n That being said, I believe this should have been brought to Exemp leaders directly and would appreciate the opportunity to resolve situations before thy are allowed to escalate in the future. \n If anyone has any concerns regarding Exemp or our members please reach out to me directly and I will do my best to mediate the situation. \n Thank you.")
    if checkformemes == "dark":
        await msg.channel.send("likes jalapeño")
    if checkformemes == "jalapeño":
        await msg.channel.send("DEEZ NUTZ JALAPEÑO MOUTH")
    if checkformemes == "mz":
        await msg.channel.send("is in the chats")
    if checkformemes == "trimmings":
        await msg.channel.send("guys. the debuff uptime in relentless is abyssmal. we need people with grims to time them and the phoenix to always be up! how is this a hard concept to grasp")
    if checkformemes == "magi jr":
        await msg.channel.send("is outdated")
    if checkformemes == "renz":
        await msg.channel.send("is the best pvp rogue on server 🤩🤩🤩🤩")
    if checkformemes == "t1ny":
        await msg.channel.send("dick")
    if checkformemes == "bad chain":
        await msg.channel.send("chain sux")
    if checkformemes == "festo":
        await msg.channel.send("are you tired of bidding? Not being able to sell items? Join me in this clan! All drops are rolled to class! No rules! no recruiting period! No more bidding! We are here for personal gain!")
    if checkformemes == "tinyarrow":
        await msg.channel.send("Hello guys, I'm quitting CH. The rewards this game offers just aren't worth the effort and time we all put in, and a busy real life schedule demands my full attention at this point. It was great to meet you all and raid for the past year.  Stay relentless!")
    if checkformemes == "surya":
        await msg.channel.send("meow yusss")
        await msg.channel.send("https://imgur.com/dgVjK3T")
    if checkformemes == "zeroroot":
        await msg.channel.send("hello every one I am sorry to inform you with sad news but I am quitting the game I have no more time to play this game as I am busy with work and irl things I will be leaving clan and all chats and will be selling all my things please pm if you would like to buy any of my stuff take care every one and have a good rest of your day")
    if checkformemes == "radi":
        await msg.channel.send("Hi all. I'm selling out, with a heavy heart. I love yall. I'll sell to rele first. Goodluck in life ❤️")
    if checkformemes == "slap":
        await msg.channel.send("https://imgur.com/BZLb5g9")
    if checkformemes == "swag":
        await msg.channel.send("sux")
    if checkformemes.startswith("who is"):
        person = checkformemes.split(" ")[2]
        if person == "keni":
            await msg.channel.send("Keni is Laur, Laur is Keni")
        elif person == "m0ney" or person == "money":
            await msg.channel.send("For the blind, He is vision. For the hungry, He is the chef. For the thirsty, He is water. If " + person + " thinks, I agree. If " + person + " speaks, I’m listening. If " + person + " has one fan, it is me. If "+ person + " has no fans, I do not exist.")
        else:
            pass
    if checkformemes == "reda sucks at programming":
        await msg.channel.send("water is wet")
    if checkformemes == "reda":
        await msg.channel.send("sucks at programming")
    if checkformemes == "deca":
        await msg.channel.send("https://media.discordapp.net/attachments/1119563151600529468/1166217517862228010/image.png?ex=6629ceb3&is=66287d33&hm=8b2e694af7728d701520eb4fc84c9ce8102814b4fe740d619f8f70f54c837961&=&format=webp&quality=lossless&width=507&height=514")
    if checkformemes == "cheating":
        await msg.channel.send("https://media.discordapp.net/attachments/1119563151600529468/1155310050643021926/IMG_1836.png?ex=6629ad54&is=66285bd4&hm=96b663e76bd9b31ca1aa154c44d4786845febee91e4e514b95bcc1f2425b947a&=&format=webp&quality=lossless&width=365&height=481")
    if checkformemes == "siuuu":
        await msg.channel.send("shud give magi white oni")
    if checkformemes == "siuu":
        await msg.channel.send("sux")
    if checkformemes == "boo":
        await msg.channel.send("BEEZ")
    if checkformemes == "lizzo":
        await msg.channel.send("""NNN
When the nut was plentiful,
When the nut was tender

Because I was fasting from the nut,
I go outside to clear my mind 

But I see a NUT TREE,
I see nuts of every kind.

And so I begin to wonder,
If fasting from the nut was a blunder

Should I just go crazy?
Or should I release the thunder?

But oh no, I made a bet that could resist in that,
And I’m not about to pay that 5 dollars.

A week left in my journey,
For the nut I am yearney
                               
The nut will not bug me,
I’m not a roller polley.

I am a man,
The nut will not control me.


So December comes blooming 
Bloomy like a daisy,
Best believe now that it’s December,
Your boy going crazy""")
    if checkformemes == "mean":
        await msg.channel.send("listen here u lil shit")
    if checkformemes == "lit":
        await msg.channel.send("stfu reda")
    if checkformemes == "zodiak":
        await msg.channel.send("yeah bro you busted me I waited til level 231 to try and get a bt helmet so i could quit and xfer to epona")
    if checkformemes == "shic":
        await msg.channel.send("Shic isn’t just tanking — he’s absorbing entire boss mechanics like they’re light cardio. The way he plants himself, holds aggro, and refuses to die is actually disrespectful to the damage dealers who need babysitting. He’s basically a walking fortress with Wi-Fi. He doesn’t panic, doesn’t fumble, just stands there like, “Yeah, hit me again.” He turns chaotic fights into target practice for the team. Honestly, if Shics is on the front line, the rest of you are just there for moral support. If tanking were a sport, Shics would already have a highlight reel and a sponsorship.")
    await client.process_commands(msg)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure) and str(error) == "dkp_wrong_server":
        # @dkp_only fired in a non-Gwydion server. Friendly redirect to lbhelp
        # rather than the generic "you don't have permission" message.
        try:
            await ctx.send(
                "That command is only available in the Gwydion (Relentless) servers. "
                "Run `$lbhelp` to see the leaderboard commands available here."
            )
        except Exception:
            pass
        return
    if isinstance(error, commands.CheckFailure) and str(error) == "dkp_dm_not_member":
        # A read command was DMed by someone the bot doesn't share a Relentless
        # server with — keep KP lookups scoped to clan members.
        try:
            await ctx.send(
                "These commands are only available to members of the Relentless (Gwydion) "
                "servers. Make sure you're in a server with Winston, then try again."
            )
        except Exception:
            pass
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("you made an error in the command arguments")
        print(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("there is a required section missing in this command")
        print(error)
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send("Winston is crying himself to sleep (google sheets may have been rate limited, there was an error, or reda sucks at programming)")
        print(error)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("command doesn't exist. yet? try $information for text based help or $help for a full list of commands. If what you want isn't there, DM reda to get it added!")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command can't be used in DMs")
    else:
        await ctx.send("Winston got confused")
        raise error

@client.command()
@dkp_only()
async def makeleaderboard(ctx):
    """Generates a leaderboard from attached screenshots (supports attachments, replied messages, and embed images)"""
    temp_files = []

    # Collect attachments from the message
    attachments = list(ctx.message.attachments)
    print(f"DEBUG: Initial attachments found: {len(attachments)}")

    # If none, check if this message is a reply and grab attachments/embeds from the referenced message
    if not attachments and ctx.message.reference:
        try:
            ref = ctx.message.reference
            if ref.message_id:
                ref_msg = await ctx.channel.fetch_message(ref.message_id)
                attachments.extend(ref_msg.attachments)
                for embed in ref_msg.embeds:
                    if embed.image and embed.image.url:
                        attachments.append(embed.image.url)
        except Exception as e:
            print("ERROR: Error fetching referenced message for attachments")
            traceback.print_exc()

    # Also accept images embedded directly in this message
    for embed in ctx.message.embeds:
        if embed.image and embed.image.url:
            attachments.append(embed.image.url)

    print(f"DEBUG: Total attachments/urls to process: {len(attachments)}")

    if not attachments:
        await ctx.send("❌ Please attach one or more screenshots (or reply to a message with images).")
        return

    try:
        # Download attachments and embedded image URLs
        async with aiohttp.ClientSession() as session:
            for a in attachments:
                fname = f"temp_{uuid.uuid4().hex}.png"
                if isinstance(a, str):
                    # URL (from embed.image.url)
                    try:
                        async with session.get(a) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                with open(fname, "wb") as f:
                                    f.write(data)
                                temp_files.append(fname)
                                print(f"DEBUG: Downloaded URL image to {fname}")
                            else:
                                await ctx.send(f"⚠ Could not download image: {a} (status {resp.status})")
                    except Exception as e:
                        print(f"ERROR: Error downloading image URL: {a}")
                        traceback.print_exc()
                        await ctx.send(f"⚠ Error downloading image: {a} — {e}")
                else:
                    # Attachment object
                    await a.save(fname)
                    temp_files.append(fname)
                    print(f"DEBUG: Saved attachment to {fname}")

        df = await sheet_call(process_images, temp_files)

        table = df.to_string(index=False)
        output = f"```\n{table}\n```"

        # Discord message limit safety
        if len(output) > 1900:
            csv_path = "leaderboard.csv"
            df.to_csv(csv_path, index=False)
            await ctx.send("Table too large — sending CSV instead:")
            await ctx.send(file=discord.File(csv_path))
            os.remove(csv_path)
        else:
            await ctx.send(output)

    except Exception as e:
        print("ERROR: makeleaderboard failed")
        traceback.print_exc()
        await ctx.send(f"⚠ Error: {str(e)}")

    finally:
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"DEBUG: Removed temp file {f}")
                except Exception:
                    print(f"ERROR: Failed to remove temp file {f}")
                    traceback.print_exc()

@client.command()
@dkp_only()
async def startbid(ctx, item, startprice, kp, startbidder):
    """Starts a bid for a new item"""
    kp = kp.upper()
    if kp not in ["VKP", "GKP", "PKP", "AKP", "RBPPUNOX", "DPKP"]:
        await ctx.send("Invalid kp type! Please use VKP, GKP, PKP, AKP, RBPPUNOX, DPKP")
        return
    startprice = int(startprice)
    # validate the bidder is a real roster name (the arg was free-form for testing)
    roster_names = await acached_col_values(bot4ws1, 1, "roster_names")
    real_bidder, caps, spaces, suggestions = find_name(startbidder, roster_names)
    if real_bidder is None:
        await ctx.send(not_found_message(startbidder, suggestions))
        return
    startbidder = real_bidder
    # lock so two concurrent $startbid calls can't grab the same id
    async with _bid_lock:
        #get the bottom row for the id
        id = len(await bot3ws12.acol_values(1))
        bidrow = [time.time(), id, item, kp, "Open", startbidder, startprice]
        await bot3ws12.aappend_row(bidrow)
        userrow = [time.time(), str(ctx.author.id), id, item, startprice, kp, "Open", startbidder]
        await bot3ws13.aappend_row(userrow)
    await ctx.send("Bid for " + item + " has started at " + str(startprice) + " " + kp + " by " + startbidder)
    await ctx.send("The ID for this bid is " + str(id) + ". Please use this number to bid on the item!")

@client.command()
@dkp_only()
async def getitemname(ctx):
    """gets the item name from an image"""
    if not ctx.message.attachments:
        await ctx.send("Please attach an image to read the item name from.")
        return
    image = ctx.message.attachments[0]
    response = await sheet_call(requests.get, image.url, timeout=25)
    img = Image.open(BytesIO(response.content))
    processed = await sheet_call(preprocessforgreen, img)
    text = await sheet_call(pytesseract.image_to_string, processed)
    item_regex = r'(\b[A-Z][a-z]{1,}(?:\s+(?:of\s+the|of|the|and))?\s+[A-Z][a-z]{1,}((\s+(?:of\s+the|of|the|and))?\s+[A-Z][a-z]{1,})*)'
    extracted_items = re.findall(item_regex, text, re.DOTALL)
    if not extracted_items:
        await ctx.send("No items were found in the image.")
        return
    item_name = ' '.join(extracted_items[0][0].split())
    await ctx.send(item_name)


def preprocessforgreen(img):
    img_cv = np.array(img)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    lower_green = np.array([40, 40, 40])
    upper_green = np.array([70, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    green_text = cv2.bitwise_and(img_cv, img_cv, mask=mask)
    gray = cv2.cvtColor(green_text, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    final_img = Image.fromarray(binary)
    return final_img


@client.command()
@dkp_only()
async def sendbid(ctx, id, price, bidder):
    """command for sending a bid to the bid sheet"""
    id = int(id)
    price = int(price)
    # validate the bidder is a real roster name (the arg was free-form for testing)
    roster_names = await acached_col_values(bot4ws1, 1, "roster_names")
    real_bidder, caps, spaces, suggestions = find_name(bidder, roster_names)
    if real_bidder is None:
        await ctx.send(not_found_message(bidder, suggestions))
        return
    bidder = real_bidder
    async with _bid_lock:
        cell = await bot3ws12.afind(str(id), in_column=2)
        if cell is None:
            await ctx.send("No bid found with ID " + str(id))
            return
        bidrownum = cell.row
        bidrow = await bot3ws12.arow_values(bidrownum)
        if bidrow[4] == "Open":
            # reject bids the bidder can't afford in this item's KP pool, mirroring
            # the check $deduct does when a won bid is processed (Current = col 7).
            kp_pool = str(bidrow[3]).upper()
            if kp_pool in KP_WORKSHEETS:
                read_ws = KP_WORKSHEETS[kp_pool]["read"]
                kp_cell = await read_ws.afind(bidder, in_column=1)
                if kp_cell is None:
                    await ctx.send(f"{bidder} has no {kp_pool} record, so can't bid in that pool.")
                    return
                current_pts = safe_float((await read_ws.acell_(kp_cell.row, 7)).value)
                if price > current_pts:
                    await ctx.send(f"{bidder} only has {current_pts:g} {kp_pool} — can't place a bid of {price}.")
                    return
            bidrow.append(bidder)
            bidrow.append(price)
            await bot3ws12.aupdate([[sanitize_cell(c) for c in bidrow]], "A" + str(bidrownum), value_input_option='USER_ENTERED')
            userrow = [time.time(), str(ctx.author.id), id, bidrow[2], price, bidrow[3], "Open", bidder]
            await bot3ws13.aappend_row(userrow, value_input_option="raw")
            await ctx.send("Bid for " + bidrow[2] + " has been placed at " + str(price) + " " + bidrow[3] + " by " + bidder)
        else:
            await ctx.send("This bid is closed!")

@client.command()
@dkp_only()
async def cancelbid(ctx, id, price, bidder):
    """command for cancelling a bid"""
    # normalise the bidder to the canonical roster name so it matches the stored bid
    roster_names = await acached_col_values(bot4ws1, 1, "roster_names")
    real_bidder, caps, spaces, suggestions = find_name(bidder, roster_names)
    if real_bidder is None:
        await ctx.send(not_found_message(bidder, suggestions))
        return
    bidder = real_bidder
    # check on the user bids sheet if the bid exists
    async with _bid_lock:
        userids = await bot3ws13.acol_values(2)
        itemids = await bot3ws13.acol_values(3)
        itemprices = await bot3ws13.acol_values(5)
        toonnames = await bot3ws13.acol_values(8)
        combili = list(zip(userids, itemids, itemprices, toonnames))
        bidfound = False
        for i in range(1, len(combili)):
            if combili[i][0] == str(ctx.author.id) and combili[i][1] == id and combili[i][2] == price and combili[i][3] == bidder:
                rownum = i + 1
                await bot3ws13.adelete_rows(rownum)
                bidfound = True
        if bidfound:
            #get the row for the item from the main sheet (match id in column 2)
            cell = await bot3ws12.afind(str(id), in_column=2)
            if cell is None:
                await ctx.send("Bid row not found for ID " + str(id))
                return
            bidrownum = cell.row
            bidrow = await bot3ws12.arow_values(bidrownum)
            #remove the bidder/price from the bid row; bidder/price pairs start
            #at index 5, so step by 2 and stop one short to keep i+1 in range
            for i in range(5, len(bidrow) - 1, 2):
                if bidrow[i] == bidder and bidrow[i + 1] == price:
                    bidrow.pop(i)
                    bidrow.pop(i)
                    break
            if(len(bidrow) <= 6):
                await bot3ws12.aupdate_cell(bidrownum, 5, "Closed")
                await ctx.send("The bid for " + bidrow[2] + " has been closed. " + bidder + " has cancelled their bid")
            else:
            #update the bid row
                bidrow.append("")
                bidrow.append("")
                await bot3ws12.aupdate([[sanitize_cell(c) for c in bidrow]], "A" + str(bidrownum), value_input_option='USER_ENTERED')
            await ctx.send("Bid for " + str(id) + " with bid " + str(price) + " has been cancelled")
    


@client.command()
@dkp_only()
async def bidtimeinfo(ctx):
    global bidslastupdate
    currenttime = time.time()
    timepassed = currenttime - bidslastupdate
    await ctx.send("The last bid update was " + str(round(timepassed, 2)) + " seconds ago")

@client.command()
@dkp_only()
async def mybids(ctx):
    """Shows the bids you have placed"""
    user = ctx.author.id
    userids = await bot3ws13.acol_values(2)
    userbids = []
    for i in range(len(userids)):
        if userids[i] == str(user):
            userbids.append(await bot3ws13.arow_values(i + 1))
    if not userbids:
        await ctx.send("You have no bids placed")
    else:
        for i in range(len(userbids)):
            await ctx.send("You have bid " + str(userbids[i][4]) + " " + userbids[i][5] + " on " + userbids[i][3] + ", Auction ID: " + str(userbids[i][2]) + ", Bidder: " + userbids[i][7] + ", Status: " + userbids[i][6])


@client.command()
@dkp_only()
async def bidinfo(ctx, id):
    """Shows the info for a bid"""
    try:
        id = int(id)
        # bidrow = bot3ws12.find(str(id))
        # search column 2 for the id
        bidrow = await bot3ws12.afind(str(id), in_column=2)
        if bidrow:
            bidrownum = bidrow.row
            bidrow = await bot3ws12.arow_values(bidrownum)
            timeleft = float(bidrow[0]) + 43200 - time.time()
            hoursleft = timeleft // 3600
            minutesleft = (timeleft % 3600) // 60
            timeleft = str(int(hoursleft)) + " hours and " + str(int(minutesleft)) + " minutes"
            await ctx.send("Bid ID " + str(bidrow[1]) + " for " + bidrow[2] + " is currently " + bidrow[4] + " with a starting bid of " + str(bidrow[6]) + " " + bidrow[3])
            if timeleft.startswith("-"):
                timeleft = timeleft[1:]
                await ctx.send("This bid for " + bidrow[2] + " ended " + timeleft + " ago")
            else:
                await ctx.send("This bid was opened at " + bidrow[0] + " and has " + timeleft + " left")
        else:
            await ctx.send("No bid with that ID exists")
    except Exception as e:
        print(e)
        await ctx.send(e)


@client.command()
@dkp_only()
@commands.has_any_role("General", "REDALiCE")
async def addpoints(ctx, playername, pointtype, earned, spent, adjusted):
    """setup command for initializing points on the sheet. only to be used in setup"""
    pointtype = pointtype.upper()
    if pointtype not in KP_WORKSHEETS:
        await ctx.send("Invalid point type! Please use VKP, GKP, PKP, AKP, RBPPUNOX, DPKP, or RBPP")
        return
    earned = float(earned)
    spent = float(spent)
    adjusted = float(adjusted)
    findnames, caps, spaces, suggestions = find_name(playername, await bot5ws1.acol_values(1))
    if not findnames:
        await ctx.send(not_found_message(playername, suggestions))
        return
    playername = findnames
    ws = KP_WORKSHEETS[pointtype]["admin"]
    playerrow = await ws.afind(playername, in_column=1)
    rownum = playerrow.row
    await ws.aupdate_cell(rownum, 4, earned)
    await ws.aupdate_cell(rownum, 5, spent)
    await ws.aupdate_cell(rownum, 6, adjusted)
    await ctx.send(pointtype + " for " + playername + " has been updated")

@client.command()
@dkp_only()
@commands.has_any_role("General", "REDALiCE")
async def addallearned(ctx, playername, VKP, GKP, PKP, AKP, RBPPUNOX, DPKP, RBPP):
    """Adds all the points earned to the player in the order VKP, GKP, PKP, AKP, RBPPUNOX, DPKP, RBPP"""
    playerrow = await bot5ws2.afind(playername, in_column=1)
    rownum = playerrow.row
    await bot5ws2.aupdate_cell(rownum, 4, float(VKP))
    playerrow = await bot5ws3.afind(playername, in_column=1)
    rownum = playerrow.row
    await bot5ws3.aupdate_cell(rownum, 4, float(GKP))
    playerrow = await bot5ws4.afind(playername, in_column=1)
    rownum = playerrow.row
    await bot5ws4.aupdate_cell(rownum, 4, float(PKP))
    playerrow = await bot5ws5.afind(playername, in_column=1)
    rownum = playerrow.row
    await bot5ws5.aupdate_cell(rownum, 4, float(AKP))
    playerrow = await bot5ws6.afind(playername, in_column=1)
    rownum = playerrow.row
    await bot5ws6.aupdate_cell(rownum, 4, float(RBPPUNOX))
    playerrow = await bot5ws7.afind(playername, in_column=1)
    rownum = playerrow.row
    await bot5ws7.aupdate_cell(rownum, 4, float(DPKP))
    playerrow = await bot5ws8.afind(playername, in_column=1)
    rownum = playerrow.row
    await bot5ws8.aupdate_cell(rownum, 4, float(RBPP))
    await ctx.send("All points for " + playername + " have been updated")


@client.command(aliases=["pointinputterinfo", "ii"])
@dkp_only()
async def inputterinfo(ctx):
     """Displays the help for point inputters"""
     embed = discord.Embed(title = "Info Dump", colour=discord.Color.orange())
     bosses = ""
     # get the boss names from the dicts
     for bossnames in akp_bosses.keys():
         bosses += bossnames + ", "
     for bossnames in gkp_bosses.keys():
            if bossnames not in bosses:
                bosses += bossnames + ", "
     for bossnames in vkp_bosses.keys():
                if bossnames not in bosses:
                    bosses += bossnames + ", "
     for bossnames in rbppunox_bosses.keys():
         if bossnames not in bosses:
             bosses += bossnames + ", "
     for bossnames in dpkp_bosses.keys():
         if bossnames not in bosses:
             bosses += bossnames + ", "
     for bossnames in rbpp_bosses.keys():
         if bossnames not in bosses:
             bosses += bossnames + ", "
     bosses = bosses[:-2]  # remove the last comma and space
     
     embed.add_field(name = "Bosses", value = bosses, inline = False)
     embed.add_field(name = "Command usage for adding points", value = "$boss <bossname> <list of characters> \n remember to put the list of characters in quotes", inline=False)
     embed.add_field(name = "Command usage for adding half points", value = "$bosshalf <bossname> <list of characters> \n remember to put the list of characters in quotes", inline=False)
     await ctx.send(embed=embed)

@client.command(aliases=["addmember", "registermember", "registermem", "am"])
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def addmem(ctx, name, rank, main, level, cclass):
    """Adds a member to the Roster, KP Lists and loot list"""
    if not re.fullmatch(r"[A-Za-z0-9 ]+", name or ""):
        await ctx.send("Invalid character name — use only letters, numbers, and spaces (the name is built directly into sheet formulas).")
        return
    cclass = cclass.capitalize()
    rank = rank.capitalize()
    main = toBool(main)
    level = int(level)
    user_list = await bot5ws1.acol_values(1)
    if cclass not in ["Warrior", "Rogue", "Mage", "Druid", "Ranger"]:
        await ctx.send("Invalid class! Please use Warrior, Rogue, Mage, Druid, or Ranger")
        return
    if rank not in ["General", "Guardian", "Clansman", "Recruit", "Chieftain"]:
        await ctx.send("Invalid rank! Please use General, Guardian, Clansman, Recruit, or Chieftain")
        return
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname == None:
        if main:

            body =[name,rank,main,level,cclass,"",name,"",False,False,False,False,False,False,False, 0]
        else:
            body =[name,rank,main,level,cclass,"","","",False,False,False,False,False,False,False, 0]
        await bot5ws1.aappend_row(body)
        rownum = len(await bot5ws2.acol_values(1)) + 1
        rownum = str(rownum)
        currformula = '=Sum(D' + rownum + '+F'+rownum+'-E'+rownum+')'
        attendformula1 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*VKP*\", 'Bosses last 30'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*VKP*\")"
        kpbody1 = [name,0,attendformula1,0,0,0,currformula]
        attendformula2 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*GKP*\", 'Bosses last 30'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*GKP*\")"
        kpbody2 = [name,0,attendformula2,0,0,0,currformula]
        attendformula3 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*PKP*\", 'Bosses last 30'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*PKP*\")"
        kpbody3 = [name,0,attendformula3,0,0,0,currformula]
        attendformula4 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*AKP*\", 'Bosses last 30'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*AKP*\")"
        kpbody4 = [name,0,attendformula4,0,0,0,currformula]
        attendformula5 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*RBPPUNOX*\", 'Bosses last 30'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*RBPPUNOX*\")"
        kpbody5 = [name,0,attendformula5,0,0,0,currformula]
        attendformula6 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*DPKP*\", 'Bosses last 30'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*DPKP*\")"
        kpbody6 = [name,0,attendformula6,0,0,0,currformula]
        attendformula7 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*RBPP*\", 'Bosses last 30'!D2:D, \"*" + name + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*RBPP*\")"
        kpbody7 = [name,0,attendformula7,0,0,0,currformula]
        await bot5ws2.aappend_row(kpbody1, value_input_option='USER_ENTERED')
        await bot5ws3.aappend_row(kpbody2, value_input_option='USER_ENTERED')
        await bot5ws4.aappend_row(kpbody3, value_input_option='USER_ENTERED')
        await bot5ws5.aappend_row(kpbody4, value_input_option='USER_ENTERED')
        await bot5ws6.aappend_row(kpbody5, value_input_option='USER_ENTERED')
        await bot5ws7.aappend_row(kpbody6, value_input_option='USER_ENTERED')
        await bot5ws8.aappend_row(kpbody7, value_input_option='USER_ENTERED')
        lootbody = [name]
        lootbody2 = ["Costs"]
        await bot5ws9.aappend_row(lootbody)
        await bot5ws9.aappend_row(lootbody2)
        if main:
            maintext = "Main"
        else:
            maintext = "Alt"
        await ctx.send(name + " (" + str(level) + " " + cclass + ", " + maintext + ", " + rank + ") was added to the list")
        logbody = ["addmem", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([name, rank, main, level, cclass])]
        await bot3ws11.aappend_row(logbody)
    else:
        await ctx.send(name + " is already in the list!")

@client.command(aliases=["rosteradministrator", "ra"])
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def rosteradmin(ctx, subcommand, name, params):
    """roster management for admins
    subcommands: rank, main"""
    params = sanitize_cell(params)  # neutralise leading =/+/-/@ formula injection in user text
    user_list = await bot5ws1.acol_values(1)
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname != None:
        cell = await bot5ws1.afind(realname, in_column=1)
        row_num = cell.row
        subcommand = subcommand.lower()
        if subcommand == "rank":
            params = params.capitalize()
            await bot5ws1.aupdate_cell(row_num, 2, params)
            await ctx.send(realname + "'s rank has been updated to " + str(params))
            # find all their alts and update those too
            alts = await bot5ws1.acol_values(7)
            for i in range(1, len(alts)):
                if alts[i] == realname:
                    await bot5ws1.aupdate_cell(i + 1, 2, params)
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "main":
            params = toBool(params)
            await bot5ws1.aupdate_cell(row_num, 3, params)
            await ctx.send(realname + "'s main status has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send("invalid subcommand")

@client.command(aliases=["r"])
@dkp_only()
async def roster(ctx, subcommand, name, params):
    """Roster Management Command
    subcommands: dg, subclass, cgoffhand, dl, dlmain, dloffhand, edl, edlmain, edloffhand, setall, level, setmain, bulksetmain, faction"""
    params = sanitize_cell(params)  # neutralise leading =/+/-/@ formula injection in user text
    user_list = await bot5ws1.acol_values(1)
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname != None:
        cell = await bot5ws1.afind(realname, in_column=1)
        row_num = cell.row
        subcommand = subcommand.lower()
        if subcommand == "dg":
            await bot5ws1.aupdate_cell(row_num, 6, params)
            await ctx.send(realname + "'s DG has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "removealt":
            if realname != None:
                await bot5ws1.aupdate_cell(row_num, 7, "")
                await ctx.send(realname + "'s Main character has been removed")
                logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
                await bot3ws11.aappend_row(logbody)
            else:
                await ctx.send(params + " not in list!")
        elif subcommand == "setmain":
            names_list = params.split(",")
            # set the realname main to itself as well
            await bot5ws1.aupdate_cell(row_num, 7, realname)
            await bot5ws1.aupdate_cell(row_num, 3, True)
            await ctx.send(realname + "'s Main character has been updated to " + str(realname))
            if realname != None:
                for names in names_list:
                    findnames, caps, spaces, suggestions = find_name(names, user_list)
                    if findnames != None:
                        cell = await bot5ws1.afind(findnames, in_column=1)
                        row_num = cell.row
                        await bot5ws1.aupdate_cell(row_num, 7, realname)
                        await bot5ws1.aupdate_cell(row_num, 3, False)
                        await ctx.send(findnames + "'s Main character has been updated to " + realname)
                        logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([findnames, subcommand, realname])]
                        await bot3ws11.aappend_row(logbody)
                    else:
                        await ctx.send(not_found_message(names, suggestions))
        elif subcommand == "bulksetmain":
            names_list = params.split(",")
            # set the realname main to itself as well
            await bot5ws1.aupdate_cell(row_num, 7, realname)
            await bot5ws1.aupdate_cell(row_num, 3, True)
            await ctx.send(realname + "'s Main character has been updated to " + str(realname))
            if realname != None:
                for names in names_list:
                    findnames, caps, spaces, suggestions = find_name(names, user_list)
                    if findnames != None:
                        cell = await bot5ws1.afind(findnames, in_column=1)
                        row_num = cell.row
                        await bot5ws1.aupdate_cell(row_num, 7, realname)
                        await bot5ws1.aupdate_cell(row_num, 3, False)
                        await ctx.send(findnames + "'s Main character has been updated to " + realname)
                        logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([findnames, subcommand, realname])]
                        await bot3ws11.aappend_row(logbody)
                    else:
                        await ctx.send(not_found_message(names, suggestions))
        elif subcommand == "level":
            await bot5ws1.aupdate_cell(row_num, 4, params)
            await ctx.send(realname + "'s level has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "class":
            params = params.capitalize()
            if params not in ["Warrior", "Rogue", "Mage", "Druid", "Ranger"]:
                await ctx.send("Invalid class! Please use Warrior, Rogue, Mage, Druid, or Ranger")
                return
            await bot5ws1.aupdate_cell(row_num, 5, params)
            await ctx.send(realname + "'s class has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "subclass":
            await bot5ws1.aupdate_cell(row_num, 8, params)
            await ctx.send(realname + "'s Subclass has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "cgoffhand":
            await bot5ws1.aupdate_cell(row_num, 9, params)
            await ctx.send(realname + "'s CG Offhand has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "dl":
            params = toBool(params)
            await bot5ws1.aupdate_cell(row_num, 10, params)
            await ctx.send(realname + "'s DL has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "dlmain":
            params = toBool(params)
            await bot5ws1.aupdate_cell(row_num, 11, params)
            await ctx.send(realname + "'s DL Main has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "dloffhand":
            params = toBool(params)
            await bot5ws1.aupdate_cell(row_num, 12, params)
            await ctx.send(realname + "'s DL Offhand has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "edl":
            params = toBool(params)
            await bot5ws1.aupdate_cell(row_num, 13, params)
            await ctx.send(realname + "'s EDL has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "edlmain":
            params = toBool(params)
            await bot5ws1.aupdate_cell(row_num, 14, params)
            await ctx.send(realname + "'s EDL Main has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "edloffhand":
            params = toBool(params)
            await bot5ws1.aupdate_cell(row_num, 15, params)
            await ctx.send(realname + "'s EDL Offhand has been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "setall":
            params = toBool(params)
            await bot5ws1.aupdate_cell(row_num, 9, params)
            await bot5ws1.aupdate_cell(row_num, 10, params)
            await bot5ws1.aupdate_cell(row_num, 11, params)
            await bot5ws1.aupdate_cell(row_num, 12, params)
            await bot5ws1.aupdate_cell(row_num, 13, params)
            await bot5ws1.aupdate_cell(row_num, 14, params)
            await bot5ws1.aupdate_cell(row_num, 15, params)
            await ctx.send(realname + "'s gear has all been updated to " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        elif subcommand == "faction":
            params = int(params)
            await bot5ws1.aupdate_cell(row_num, 16, params)
            await ctx.send(realname + "'s Valley Faction has been updated to tier " + str(params))
            logbody = ["roster", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, subcommand, params])]
            await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send("invalid subcommand")
    else:
        await ctx.send(not_found_message(name, suggestions))

@client.command(aliases=["p", "toon", "char", "character"])
@dkp_read()
async def player(ctx, *name):
    """Displays a player's information"""
    name = " ".join(name)
    user_list = await acached_col_values(bot4ws1, 1, "roster_names")
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname != None:
        cell = await bot4ws1.afind(realname, in_column=1)
        row_num = cell.row
        embedvals = pad_row(await bot4ws1.arow_values(row_num, value_render_option='UNFORMATTED_VALUE'), 16)
        embed = discord.Embed(title = realname, colour=discord.Color.orange())
        embed.add_field(name = "Rank", value = embedvals[1], inline = True)
        embed.add_field(name = "Main", value = embedvals[2], inline = True)
        embed.add_field(name = "Level", value = embedvals[3], inline = True)
        embed.add_field(name = "Class", value = embedvals[4], inline = True)
        # embed.add_field(name = "DG", value = embedvals[5], inline = True)
        embed.add_field(name = "Main Character", value = embedvals[6], inline = True)
        # embed.add_field(name = "Subclass", value = embedvals[7], inline = True)
        # embed.add_field(name = "CG Offhand", value = embedvals[8], inline = True)
        # embed.add_field(name = "DL", value = embedvals[9], inline = True)
        # embed.add_field(name = "DL Main", value = embedvals[10], inline = True)
        # embed.add_field(name = "DL Offhand", value = embedvals[11], inline = True)
        # embed.add_field(name = "EDL", value = embedvals[12], inline = True)
        # embed.add_field(name = "EDL Main", value = embedvals[13], inline = True)
        # embed.add_field(name = "EDL Offhand", value = embedvals[14], inline = True)
        embed.add_field(name = "Valley Faction", value = embedvals[15], inline = True)
        cell2 = await bot4ws2.afind(realname, in_column=1)
        row_num2 = cell2.row
        dkprowvals = await bot4ws2.arow_values(row_num2, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "VKP", value = "Earned: " + str(dkprowvals[3]) + ", Current: " + str(dkprowvals[6]), inline = False)
        cell3 = await bot4ws3.afind(realname, in_column=1)
        row_num3 = cell3.row
        dkprowvals2 = await bot4ws3.arow_values(row_num3, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "GKP", value = "Earned: " + str(dkprowvals2[3]) + ", Current: " + str(dkprowvals2[6]), inline = False)
        cell5 = await bot4ws5.afind(realname, in_column=1)
        row_num5 = cell5.row
        dkprowvals4 = await bot4ws5.arow_values(row_num5, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "AKP", value = "Earned: " + str(dkprowvals4[3]) + ", Current: " + str(dkprowvals4[6]), inline = False)
        cell6 = await bot4ws6.afind(realname, in_column=1)
        row_num6 = cell6.row
        dkprowvals5 = await bot4ws6.arow_values(row_num6, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "RBPPUNOX", value = "Earned: " + str(dkprowvals5[3]) + ", Current: " + str(dkprowvals5[6]), inline = False)
        cell7 = await bot4ws7.afind(realname, in_column=1)
        row_num7 = cell7.row
        dkprowvals6 = await bot4ws7.arow_values(row_num7, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "DPKP", value = "Earned: " + str(dkprowvals6[3]) + ", Current: " + str(dkprowvals6[6]), inline = False)
        cell8 = await bot4ws8.afind(realname, in_column=1)
        row_num8 = cell8.row
        dkprowvals7 = await bot4ws8.arow_values(row_num8, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "RBPP", value = "Earned: " + str(dkprowvals7[3]) + ", Current: " + str(dkprowvals7[6]), inline = False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(not_found_message(name, suggestions))

@client.command(aliases=["pf", "playerfullinfo", "playerfullinformation"])
@dkp_read()
async def playerfull(ctx, *name):
    """Displays a player's information"""
    name = " ".join(name)
    user_list = await acached_col_values(bot4ws1, 1, "roster_names")
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname != None:
        cell = await bot4ws1.afind(realname, in_column=1)
        row_num = cell.row
        embedvals = pad_row(await bot4ws1.arow_values(row_num, value_render_option='UNFORMATTED_VALUE'), 16)
        embed = discord.Embed(title = realname, colour=discord.Color.orange())
        embed.add_field(name = "Rank", value = embedvals[1], inline = True)
        embed.add_field(name = "Main", value = embedvals[2], inline = True)
        embed.add_field(name = "Level", value = embedvals[3], inline = True)
        embed.add_field(name = "Class", value = embedvals[4], inline = True)
        embed.add_field(name = "DG", value = embedvals[5], inline = True)
        embed.add_field(name = "Main Character", value = embedvals[6], inline = True)
        embed.add_field(name = "Subclass", value = embedvals[7], inline = True)
        embed.add_field(name = "CG Offhand", value = embedvals[8], inline = True)
        embed.add_field(name = "DL", value = embedvals[9], inline = True)
        embed.add_field(name = "DL Main", value = embedvals[10], inline = True)
        embed.add_field(name = "DL Offhand", value = embedvals[11], inline = True)
        embed.add_field(name = "EDL", value = embedvals[12], inline = True)
        embed.add_field(name = "EDL Main", value = embedvals[13], inline = True)
        embed.add_field(name = "EDL Offhand", value = embedvals[14], inline = True)
        cell2 = await bot4ws2.afind(realname, in_column=1)
        row_num2 = cell2.row
        dkprowvals = await bot4ws2.arow_values(row_num2, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "VKP", value = "Earned: " + str(dkprowvals[3]) + ", Current: " + str(dkprowvals[6]), inline = False)
        cell3 = await bot4ws3.afind(realname, in_column=1)
        row_num3 = cell3.row
        dkprowvals2 = await bot4ws3.arow_values(row_num3, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "GKP", value = "Earned: " + str(dkprowvals2[3]) + ", Current: " + str(dkprowvals2[6]), inline = False)
        cell5 = await bot4ws5.afind(realname, in_column=1)
        row_num5 = cell5.row
        dkprowvals4 = await bot4ws5.arow_values(row_num5, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "AKP", value = "Earned: " + str(dkprowvals4[3]) + ", Current: " + str(dkprowvals4[6]), inline = False)
        cell6 = await bot4ws6.afind(realname, in_column=1)
        row_num6 = cell6.row
        dkprowvals5 = await bot4ws6.arow_values(row_num6, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "RBPPUNOX", value = "Earned: " + str(dkprowvals5[3]) + ", Current: " + str(dkprowvals5[6]), inline = False)
        cell7 = await bot4ws7.afind(realname, in_column=1)
        row_num7 = cell7.row
        dkprowvals6 = await bot4ws7.arow_values(row_num7, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "DPKP", value = "Earned: " + str(dkprowvals6[3]) + ", Current: " + str(dkprowvals6[6]), inline = False)
        cell8 = await bot4ws8.afind(realname, in_column=1)
        row_num8 = cell8.row
        dkprowvals7 = await bot4ws8.arow_values(row_num8, value_render_option='UNFORMATTED_VALUE')
        embed.add_field(name = "RBPP", value = "Earned: " + str(dkprowvals7[3]) + ", Current: " + str(dkprowvals7[6]), inline = False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(not_found_message(name, suggestions))

@client.command(aliases=["pkp"])
@dkp_read()
async def playerkp(ctx, *name):
    """Displays a player's KP information"""
    name = " ".join(name)
    user_list = await acached_col_values(bot4ws1, 1, "roster_names")
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname != None:
        cell = await bot4ws2.afind(realname, in_column=1)
        row_num = cell.row
        embedvals = await bot4ws2.arow_values(row_num)
        embed = discord.Embed(title = realname + "'s KP", colour=discord.Color.orange())
        embed.add_field(name = "VKP", value = "Last Raid: " + embedvals[1] + ", Att %: " + embedvals[2] + ", Earned: " + embedvals[3] + ", Spent: " + embedvals[4] + ", Adjusted: " + embedvals[5] + ", Current: " + str(embedvals[6]), inline = False)
        cell2 = await bot4ws3.afind(realname, in_column=1)
        row_num2 = cell2.row
        embedvals2 = await bot4ws3.arow_values(row_num2)
        embed.add_field(name = "GKP", value = "Last Raid: " + embedvals2[1] + ", Att %: " + embedvals2[2] + ", Earned: " + embedvals2[3] + ", Spent: " + embedvals2[4] + ", Adjusted: " + embedvals2[5] + ", Current: " + str(embedvals2[6]), inline = False)
        cell4 = await bot4ws5.afind(realname, in_column=1)
        row_num4 = cell4.row
        embedvals4 = await bot4ws5.arow_values(row_num4)
        embed.add_field(name = "AKP", value = "Last Raid: " + embedvals4[1] + ", Att %: " + embedvals4[2] + ", Earned: " + embedvals4[3] + ", Spent: " + embedvals4[4] + ", Adjusted: " + embedvals4[5] + ", Current: " + str(embedvals4[6]), inline = False)
        cell5 = await bot4ws6.afind(realname, in_column=1)
        row_num5 = cell5.row
        embedvals5 = await bot4ws6.arow_values(row_num5)
        embed.add_field(name = "RBPPUNOX", value = "Last Raid: " + embedvals5[1] + ", Att %: " + embedvals5[2] + ", Earned: " + embedvals5[3] + ", Spent: " + embedvals5[4] + ", Adjusted: " + embedvals5[5] + ", Current: " + str(embedvals5[6]), inline = False)
        cell6 = await bot4ws7.afind(realname, in_column=1)
        row_num6 = cell6.row
        embedvals6 = await bot4ws7.arow_values(row_num6)
        embed.add_field(name = "DPKP", value = "Last Raid: " + embedvals6[1] + ", Att %: " + embedvals6[2] + ", Earned: " + embedvals6[3] + ", Spent: " + embedvals6[4] + ", Adjusted: " + embedvals6[5] + ", Current: " + str(embedvals6[6]), inline = False)
        cell7 = await bot4ws8.afind(realname, in_column=1)
        row_num7 = cell7.row
        embedvals7 = await bot4ws8.arow_values(row_num7)
        embed.add_field(name = "RBPP", value = "Last Raid: " + embedvals7[1] + ", Att %: " + embedvals7[2] + ", Earned: " + embedvals7[3] + ", Spent: " + embedvals7[4] + ", Adjusted: " + embedvals7[5] + ", Current: " + str(embedvals7[6]), inline = False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(not_found_message(name, suggestions))

@client.command(aliases=["toons", "chars", "characterlist"])
@dkp_read()
async def characters(ctx, *name):
    """shows all characters a player has"""
    name = " ".join(name)
    mains_list = await bot4ws1.acol_values(7)
    characters_list = await acached_col_values(bot4ws1, 1, "roster_names")
    levels_list = await bot4ws1.acol_values(4)
    cclass_list = await bot4ws1.acol_values(5)
    mains_to_chars = zip(mains_list, characters_list, levels_list, cclass_list)
    # remove header
    mains_to_chars = list(mains_to_chars)[1:]
    # sort so that mains come first, then by level descending
    mains_to_chars = sorted(mains_to_chars, key=lambda x: (x[0] != x[1], -safe_int(x[2])))
    realname, caps, spaces, suggestions = find_name(name, mains_list)
    if realname != None:
        #find all instances of main name in the character list, paginate every 20 and send
        user_characters = [(character, level, cclass) for main, character, level, cclass in mains_to_chars if main == realname]
        total = len(user_characters)
        pagecounter = 0
        for i in range(total):
            if i % 20 == 0:
                if i != 0:
                    await ctx.send(embed=embed)
                pagecounter += 1
                title = realname + "'s Characters"
                if total > 20:
                    title += " Page " + str(pagecounter)
                embed = discord.Embed(title=title, colour=discord.Color.orange())
            character, level, cclass = user_characters[i]
            embed.add_field(name=character, value="Level " + str(level) + " " + cclass, inline=False)
        if total > 0:
            await ctx.send(embed=embed)
        return
    altrealname, caps, spaces, alt_suggestions = find_name(name, characters_list)
    if altrealname != None:
        #pull the main first, then find all instances of the main in the character list, paginate every 20 and send
        cell = await bot4ws1.afind(altrealname, in_column=1)
        row_num = cell.row
        main_name = (await bot4ws1.acell_(row_num, 7)).value
        user_characters = [(character, level, cclass) for main, character, level, cclass in mains_to_chars if main == main_name]
        total = len(user_characters)
        pagecounter = 0
        for i in range(total):
            if i % 20 == 0:
                if i != 0:
                    await ctx.send(embed=embed)
                pagecounter += 1
                title = main_name + "'s Characters"
                if total > 20:
                    title += " Page " + str(pagecounter)
                embed = discord.Embed(title=title, colour=discord.Color.orange())
            character, level, cclass = user_characters[i]
            embed.add_field(name=character, value="Level " + str(level) + " " + cclass, inline=False)
        if total > 0:
            await ctx.send(embed=embed)
    else:
        await ctx.send(not_found_message(name, suggestions or alt_suggestions))
        

@client.command()
@dkp_only()
@commands.has_any_role("General", "REDALiCE")
async def fullpointwipe(ctx, name, verification):
    """fully wipes someones points, including earned points"""
    if verification == "releleaderfullwipe":
        user_list = await bot5ws1.acol_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell1 = await bot5ws2.afind(realname, in_column=1)
            row_num1 = cell1.row
            currformula1 = '=Sum(D' + str(row_num1) + '+F'+str(row_num1)+'-E'+str(row_num1)+')'
            attendformula1 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*VKP*\", 'Bosses last 30'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*VKP*\")"
            wipedrow1 = [realname,0,attendformula1,0,0,0,currformula1]
            await bot5ws2.aupdate([wipedrow1], "A" + str(row_num1), value_input_option='USER_ENTERED')
            cell2 = await bot5ws3.afind(realname, in_column=1)
            row_num2 = cell2.row
            currformula2 = '=Sum(D' + str(row_num2) + '+F'+str(row_num2)+'-E'+str(row_num2)+')'
            attendformula2 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*GKP*\", 'Bosses last 30'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*GKP*\")"
            wipedrow2 = [realname,0,attendformula2,0,0,0,currformula2]
            await bot5ws3.aupdate([wipedrow2], "A" + str(row_num2), value_input_option='USER_ENTERED')
            cell3 = await bot5ws4.afind(realname, in_column=1)
            row_num3 = cell3.row
            currformula3 = '=Sum(D' + str(row_num3) + '+F'+str(row_num3)+'-E'+str(row_num3)+')'
            attendformula3 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*PKP*\", 'Bosses last 30'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*PKP*\")"
            wipedrow3 = [realname,0,attendformula3,0,0,0,currformula3]
            await bot5ws4.aupdate([wipedrow3], "A" + str(row_num3), value_input_option='USER_ENTERED')
            cell4 = await bot5ws5.afind(realname, in_column=1)
            row_num4 = cell4.row
            currformula4 = '=Sum(D' + str(row_num4) + '+F'+str(row_num4)+'-E'+str(row_num4)+')'
            attendformula4 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*AKP*\", 'Bosses last 30'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*AKP*\")"
            wipedrow4 = [realname,0,attendformula4,0,0,0,currformula4]
            await bot5ws5.aupdate([wipedrow4], "A" + str(row_num4), value_input_option='USER_ENTERED')
            cell5 = await bot5ws6.afind(realname, in_column=1)
            row_num5 = cell5.row
            currformula5 = '=Sum(D' + str(row_num5) + '+F'+str(row_num5)+'-E'+str(row_num5)+')'
            attendformula5 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*RBPPUNOX*\", 'Bosses last 30'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*RBPPUNOX*\")"
            wipedrow5 = [realname,0,attendformula5,0,0,0,currformula5]
            await bot5ws6.aupdate([wipedrow5], "A" + str(row_num5), value_input_option='USER_ENTERED')
            cell6 = await bot5ws7.afind(realname, in_column=1)
            row_num6 = cell6.row
            currformula6 = '=Sum(D' + str(row_num6) + '+F'+str(row_num6)+'-E'+str(row_num6)+')'
            attendformula6 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*DPKP*\", 'Bosses last 30'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*DPKP*\")"
            wipedrow6 = [realname,0,attendformula6,0,0,0,currformula6]
            await bot5ws7.aupdate([wipedrow6], "A" + str(row_num6), value_input_option='USER_ENTERED')
            cell7 = await bot5ws8.afind(realname, in_column=1)
            row_num7 = cell7.row
            currformula7 = '=Sum(D' + str(row_num7) + '+F'+str(row_num7)+'-E'+str(row_num7)+')'
            attendformula7 = "=(COUNTIFS('Bosses last 30'!C2:C, \"*RBPP*\", 'Bosses last 30'!D2:D, \"*" + realname + "*\"))/COUNTIFS('Bosses last 30'!B2:B, \"<>*HALF*\", 'Bosses last 30'!B2:B, \"<>\", 'Bosses last 30'!C2:C, \"*RBPP*\")"
            wipedrow7 = [realname,0,attendformula7,0,0,0,currformula7]
            await bot5ws8.aupdate([wipedrow7], "A" + str(row_num7), value_input_option='USER_ENTERED')
            await ctx.send(realname + "'s points have been fully wiped")
            logbody = ["wipe", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname])]
            await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send(not_found_message(name, suggestions))


def parse_deduct_args(args_str):
    """Parse deduct arguments from a string like: $deduct "name" "item" 123 KP
    Returns (name, item, number, kp) or (None, None, None, None) on parse error"""
    # Remove $deduct prefix if present
    if isinstance(args_str, str):
        args_str = args_str.strip()
        if args_str.startswith("$deduct"):
            args_str = args_str[7:].strip()
    else:
        return (None, None, None, None)
    
    # Try to extract quoted strings first
    import re as regex_module
    # Pattern: "..." "..." number KP
    match = regex_module.match(r'^"([^"]*)"\s+"([^"]*)"\s+(\S+)\s+(\S+)$', args_str)
    if match:
        name = match.group(1)
        item = match.group(2)
        try:
            number = float(match.group(3))
        except ValueError:
            return (None, None, None, None)
        if number <= 0:
            return (None, None, None, None)
        kp = match.group(4).upper()
        return (name, item, number, kp)

    return (None, None, None, None)


def _loot_next_col(lootlist, costlist):
    """Return the 1-based column to write the next (item, cost) pair into.

    Ignores trailing blanks (so the gspread-rectangular padding on cached rows
    doesn't push writes far to the right), and prefers the earliest column
    where BOTH rows are blank — reusing gaps from prior mis-writes.
    """
    def _effective_len(lst):
        n = len(lst)
        while n > 0 and (lst[n - 1] is None or str(lst[n - 1]).strip() == ""):
            n -= 1
        return n

    loot_n = _effective_len(lootlist)
    cost_n = _effective_len(costlist)
    scan_to = max(loot_n, cost_n)

    for idx in range(1, scan_to):  # 0 = player name cell, skip it
        item_cell = lootlist[idx] if idx < len(lootlist) else ""
        cost_cell = costlist[idx] if idx < len(costlist) else ""
        if (item_cell is None or str(item_cell).strip() == "") and \
           (cost_cell is None or str(cost_cell).strip() == ""):
            return idx + 1  # convert 0-based list index to 1-based column

    return max(max(loot_n, cost_n) + 1, 2)


def _write_loot(ws, lootrow, item, cost_str):
    """Write a single (item, cost) pair to the player's loot/cost row pair.

    Refreshes the cache first to avoid staleness, then targets two cells
    directly rather than rewriting whole rows.
    """
    ws.refresh()
    lootlist = ws.row_values(lootrow)
    costlist = ws.row_values(lootrow + 1)
    col = _loot_next_col(lootlist, costlist)
    ws.update_cell(lootrow, col, sanitize_cell(item))
    ws.update_cell(lootrow + 1, col, cost_str)


def internal_deduct(args_str):
    name, item, number, kp = parse_deduct_args(args_str)

    if name is None or item is None or kp is None:
        return("Could not parse line: " + str(args_str))

    if number <= 0:
        return("Amount must be positive (line: " + str(args_str) + ")")

    kp = kp.upper()

    if kp == "VKP":
        user_list = bot3ws2.col_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = bot3ws2.find(realname, in_column=1)
            row_num = cell.row
            current = float(bot3ws2.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws2.cell(row_num, 5).value) + number
            if new < 0:
                return("Cannot deduct more points than the player has")
            else:
                bot3ws2.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname, in_column=1)
                _write_loot(bot3ws9, lootcell.row, item, str(number) + " VKP")
                logbody = ["deduct", "internal", dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
                return(realname + " has been deducted " + str(number) + " VKP for " + item)
                
        else:
            return(not_found_message(name, suggestions))
    elif kp == "GKP":
        user_list = bot3ws3.col_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = bot3ws3.find(realname, in_column=1)
            row_num = cell.row
            current = float(bot3ws3.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws3.cell(row_num, 5).value) + number
            if new < 0:
                return("Cannot deduct more points than the player has")
            else:
                bot3ws3.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname, in_column=1)
                _write_loot(bot3ws9, lootcell.row, item, str(number) + " GKP")
                logbody = ["deduct", "internal", dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
                return(realname + " has been deducted " + str(number) + " GKP for " + item)
        else:
            return(not_found_message(name, suggestions))
    elif kp == "PKP":
        user_list = bot3ws4.col_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = bot3ws4.find(realname, in_column=1)
            row_num = cell.row
            current = float(bot3ws4.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws4.cell(row_num, 5).value) + number
            if new < 0:
                return("Cannot deduct more points than the player has")
            else:
                bot3ws4.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname, in_column=1)
                _write_loot(bot3ws9, lootcell.row, item, str(number) + " PKP")
                logbody = ["deduct", "internal", dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
                return(realname + " has been deducted " + str(number) + " PKP for " + item)
                
        else:
            return(not_found_message(name, suggestions))
    elif kp == "AKP":
        user_list = bot3ws5.col_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = bot3ws5.find(realname, in_column=1)
            row_num = cell.row
            current = float(bot3ws5.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws5.cell(row_num, 5).value) + number
            if new < 0:
                return("Cannot deduct more points than the player has")
            else:
                bot3ws5.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname, in_column=1)
                _write_loot(bot3ws9, lootcell.row, item, str(number) + " AKP")
                logbody = ["deduct", "internal", dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
                return(realname + " has been deducted " + str(number) + " AKP for " + item)
                
        else:
            return(not_found_message(name, suggestions))
    elif kp == "RBPPUNOX":
        user_list = bot3ws6.col_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = bot3ws6.find(realname, in_column=1)
            row_num = cell.row
            current = float(bot3ws6.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws6.cell(row_num, 5).value) + number
            if new < 0:
                return("Cannot deduct more points than the player has")
            else:
                bot3ws6.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname, in_column=1)
                _write_loot(bot3ws9, lootcell.row, item, str(number) + " RBPPUNOX")
                logbody = ["deduct", "internal", dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
                return(realname + " has been deducted " + str(number) + " RBPPUNOX for " + item)
                
        else:
            return(not_found_message(name, suggestions))
    elif kp == "DPKP":
        user_list = bot3ws7.col_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = bot3ws7.find(realname, in_column=1)
            row_num = cell.row
            current = float(bot3ws7.cell(row_num, 7).value)
            new = current - number
            newspent = float(bot3ws7.cell(row_num, 5).value) + number
            if new < 0:
                return("Cannot deduct more points than the player has")
            else:
                bot3ws7.update_cell(row_num, 5, newspent)
                lootcell = bot3ws9.find(realname, in_column=1)
                _write_loot(bot3ws9, lootcell.row, item, str(number) + " DPKP")
                logbody = ["deduct", "internal", dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                bot3ws11.append_row(logbody)
                return(realname + " has been deducted " + str(number) + " DPKP for " + item)
                
        else:
            return(not_found_message(name, suggestions))
    else:
        return("Invalid KP type: " + kp)

@client.command()
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def deduct(ctx, name, item, number, kp):
    """Deducts points from a player and adds the item to their loot list"""
    kp = kp.upper()
    number = float(number)

    if number <= 0:
        await ctx.send("Amount must be positive.")
        return

    if kp == "VKP":
        user_list = await bot3ws2.acol_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = await bot3ws2.afind(realname, in_column=1)
            row_num = cell.row
            current = float((await bot3ws2.acell_(row_num, 7)).value)
            new = current - number
            newspent = float((await bot3ws2.acell_(row_num, 5)).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                await bot3ws2.aupdate_cell(row_num, 5, newspent)
                lootcell = await bot3ws9.afind(realname, in_column=1)
                await sheet_call(_write_loot, bot3ws9, lootcell.row, item, str(number) + " VKP")
                await ctx.send(realname + " has been deducted " + str(number) + " VKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send(not_found_message(name, suggestions))
    elif kp == "GKP":
        user_list = await bot3ws3.acol_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = await bot3ws3.afind(realname, in_column=1)
            row_num = cell.row
            current = float((await bot3ws3.acell_(row_num, 7)).value)
            new = current - number
            newspent = float((await bot3ws3.acell_(row_num, 5)).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                await bot3ws3.aupdate_cell(row_num, 5, newspent)
                lootcell = await bot3ws9.afind(realname, in_column=1)
                await sheet_call(_write_loot, bot3ws9, lootcell.row, item, str(number) + " GKP")
                await ctx.send(realname + " has been deducted " + str(number) + " GKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send(not_found_message(name, suggestions))
    elif kp == "PKP":
        user_list = await bot3ws4.acol_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = await bot3ws4.afind(realname, in_column=1)
            row_num = cell.row
            current = float((await bot3ws4.acell_(row_num, 7)).value)
            new = current - number
            newspent = float((await bot3ws4.acell_(row_num, 5)).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                await bot3ws4.aupdate_cell(row_num, 5, newspent)
                lootcell = await bot3ws9.afind(realname, in_column=1)
                await sheet_call(_write_loot, bot3ws9, lootcell.row, item, str(number) + " PKP")
                await ctx.send(realname + " has been deducted " + str(number) + " PKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send(not_found_message(name, suggestions))
    elif kp == "AKP":
        user_list = await bot3ws5.acol_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = await bot3ws5.afind(realname, in_column=1)
            row_num = cell.row
            current = float((await bot3ws5.acell_(row_num, 7)).value)
            new = current - number
            newspent = float((await bot3ws5.acell_(row_num, 5)).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                await bot3ws5.aupdate_cell(row_num, 5, newspent)
                lootcell = await bot3ws9.afind(realname, in_column=1)
                await sheet_call(_write_loot, bot3ws9, lootcell.row, item, str(number) + " AKP")
                await ctx.send(realname + " has been deducted " + str(number) + " AKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send(not_found_message(name, suggestions))
    elif kp == "RBPPUNOX":
        user_list = await bot3ws6.acol_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = await bot3ws6.afind(realname, in_column=1)
            row_num = cell.row
            current = float((await bot3ws6.acell_(row_num, 7)).value)
            new = current - number
            newspent = float((await bot3ws6.acell_(row_num, 5)).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                await bot3ws6.aupdate_cell(row_num, 5, newspent)
                lootcell = await bot3ws9.afind(realname, in_column=1)
                await sheet_call(_write_loot, bot3ws9, lootcell.row, item, str(number) + " RBPPUNOX")
                await ctx.send(realname + " has been deducted " + str(number) + " RBPPUNOX for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send(not_found_message(name, suggestions))
    elif kp == "DPKP":
        user_list = await bot3ws7.acol_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = await bot3ws7.afind(realname, in_column=1)
            row_num = cell.row
            current = float((await bot3ws7.acell_(row_num, 7)).value)
            new = current - number
            newspent = float((await bot3ws7.acell_(row_num, 5)).value) + number
            if new < 0:
                await ctx.send("Cannot deduct more points than the player has")
            else:
                await bot3ws7.aupdate_cell(row_num, 5, newspent)
                lootcell = await bot3ws9.afind(realname, in_column=1)
                await sheet_call(_write_loot, bot3ws9, lootcell.row, item, str(number) + " DPKP")
                await ctx.send(realname + " has been deducted " + str(number) + " DPKP for " + item)
                logbody = ["deduct", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, item, number, kp])]
                await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send(not_found_message(name, suggestions))
    else:
        await ctx.send("Invalid pointpool! Use VKP, GKP, PKP, AKP, RBPPUNOX, or DPKP.")
        

@client.command(aliases=["bidgenerator", "bg"])
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def bidgen(ctx, *message):
    """Parses a loot message and generates deduct commands
    
    Format:
    Player Name - Item Name
    (amount pointpool)
    
    Usage: Reply to a message with $bidgen, or use $bidgen followed by the message
    """
    # Check if this is a reply to another message
    
    if ctx.message.reference:
        # Fetch the message being replied to
        replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        message = replied_msg.content
    else:
        message = ' '.join(message)

    lines = message.strip().split('\n')
    commands_output = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Check if this is a player-item line (contains " - ")
        if " - " in line:
            parts = line.split(" - ", 1)
            player_name = parts[0].strip()
            if " for " in player_name:
                player_name = player_name.split(" for ")[0].strip()
            item_name = parts[1].strip()
            # Look for the next line with (amount pointpool)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Pattern: (number POINTPOOL)
                import re
                match = re.match(r'\((\d+)\s+(\w+)\)', next_line)
                if match:
                    amount = match.group(1)
                    pointpool = match.group(2)
                    # Generate deduct command
                    deduct_cmd = f'$deduct "{player_name}" "{item_name}" {amount} {pointpool}'
                    commands_output.append(deduct_cmd)
                    # Skip the next line since we processed it
                    i += 2
                    continue
        else:
            i += 1
            # commands_output.append(f"# Could not parse line: {line}")
            continue
        i += 1
    # Output all commands
    if commands_output:
        output = "Generated deduct commands:\n\n" + "\n".join(commands_output) + "\n"
        await ctx.send(output)
    else:
        await ctx.send("No valid loot entries found. Please check the format:\n```\nPlayer Name - Item Name\n(amount pointpool)\n```")

@client.command(aliases=["loot", "wonitems"])
@dkp_read()
async def winnings(ctx, name, kp = None):
    """Displays a player's loot winnings"""
    if kp != None:
        kp = kp.upper()
    if kp == None:
        user_list = await bot4ws9.acol_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = await bot4ws9.afind(realname, in_column=1)
            row_num = cell.row
            lootlist = await bot4ws9.arow_values(row_num)
            costlist = await bot4ws9.arow_values(row_num + 1)
            lootlist.pop(0)
            costlist.pop(0)
            width = max(len(lootlist), len(costlist))
            pairs = []
            for i in range(width):
                item = lootlist[i] if i < len(lootlist) else ""
                cost = costlist[i] if i < len(costlist) else ""
                if str(item).strip() == "" and str(cost).strip() == "":
                    continue
                pairs.append((item if str(item).strip() else "(blank)",
                              cost if str(cost).strip() else "(blank)"))
            pagecounter = 0
            if len(pairs) == 0:
                await ctx.send(realname + " has no loot winnings")
            else:
                for i, (item, cost) in enumerate(pairs):
                    if i % 20 == 0:
                        if i != 0:
                            await ctx.send(embed=embed)
                        pagecounter += 1
                        embed = discord.Embed(title = realname + "'s Winnings Page " + str(pagecounter), colour=discord.Color.orange())
                    embed.add_field(name = str(i + 1) + ". " + item, value = cost, inline = False)
                await ctx.send(embed=embed)
        else:
            await ctx.send(not_found_message(name, suggestions))
    else:
        user_list = await bot4ws9.acol_values(1)
        realname, caps, spaces, suggestions = find_name(name, user_list)
        if realname != None:
            cell = await bot4ws9.afind(realname, in_column=1)
            row_num = cell.row
            lootlist = await bot4ws9.arow_values(row_num)
            costlist = await bot4ws9.arow_values(row_num + 1)
            lootlist.pop(0)
            costlist.pop(0)
            width = max(len(lootlist), len(costlist))
            pairs = []
            for i in range(width):
                item = lootlist[i] if i < len(lootlist) else ""
                cost = costlist[i] if i < len(costlist) else ""
                if str(item).strip() == "" and str(cost).strip() == "":
                    continue
                pairs.append((item if str(item).strip() else "(blank)",
                              cost if str(cost).strip() else "(blank)"))
            pagecounter = 0
            itemsadded = 0
            for i, (item, cost) in enumerate(pairs):
                if kp in cost:
                    if itemsadded % 20 == 0:
                        if itemsadded != 0:
                            await ctx.send(embed=embed)
                        pagecounter += 1
                        embed = discord.Embed(title = realname + "'s " + kp + " Winnings Page " + str(pagecounter), colour=discord.Color.orange())
                    embed.add_field(name = str(i + 1) + ". " + item, value = cost, inline = False)
                    itemsadded += 1
            if itemsadded == 0:
                await ctx.send(realname + " has no loot winnings for " + kp)
            else:
                await ctx.send(embed=embed)
        else:
            await ctx.send(not_found_message(name, suggestions))

@client.command()
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def refunditem(ctx, name, itemnum):
    """Refunds an item and returns the points to the player"""
    itemnum = int(itemnum)
    if itemnum < 1:
        await ctx.send("Item number must be >= 1 (column 0 holds the player name).")
        return
    user_list = await bot3ws9.acol_values(1)
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname != None:
        cell = await bot3ws9.afind(realname, in_column=1)
        row_num = cell.row
        lootlist = await bot3ws9.arow_values(row_num)
        costlist = await bot3ws9.arow_values(row_num + 1)
        if itemnum >= len(lootlist) or itemnum >= len(costlist):
            await ctx.send(f"Item {itemnum} is out of range for {realname} (loot has {len(lootlist) - 1} entries).")
            return
        itemname = lootlist[itemnum]
        cost_raw = costlist[itemnum]
        if not itemname or not cost_raw:
            await ctx.send(f"Item slot {itemnum} for {realname} is empty.")
            return
        if itemname.startswith("[REFUNDED] "):
            await ctx.send(f"Item {itemnum} ({itemname}) is already refunded.")
            return
        cost = cost_raw.split(" ")
        itemprice = float(cost[0])
        itemkp = cost[1]
        newitemname = "[REFUNDED] " + itemname
        await bot3ws9.aupdate_cell(row_num, itemnum + 1, newitemname)
        if itemkp == "VKP":
            kpcell = await bot3ws2.afind(realname, in_column=1)
            kprow = kpcell.row
            spent = float((await bot3ws2.acell_(kprow, 5)).value)
            newspent = spent - itemprice
            await bot3ws2.aupdate_cell(kprow, 5, newspent)
            await ctx.send(realname + " has been refunded " + str(itemprice) + " VKP for " + itemname)
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
            await bot3ws11.aappend_row(logbody)
        elif itemkp == "GKP":
            kpcell = await bot3ws3.afind(realname, in_column=1)
            kprow = kpcell.row
            spent = float((await bot3ws3.acell_(kprow, 5)).value)
            newspent = spent - itemprice
            await bot3ws3.aupdate_cell(kprow, 5, newspent)
            await ctx.send(realname + " has been refunded " + str(itemprice) + " GKP for " + itemname)
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
            await bot3ws11.aappend_row(logbody)
        elif itemkp == "PKP":
            kpcell = await bot3ws4.afind(realname, in_column=1)
            kprow = kpcell.row
            spent = float((await bot3ws4.acell_(kprow, 5)).value)
            newspent = spent - itemprice
            await bot3ws4.aupdate_cell(kprow, 5, newspent)
            await ctx.send(realname + " has been refunded " + str(itemprice) + " PKP for " + itemname)
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
            await bot3ws11.aappend_row(logbody)
        elif itemkp == "AKP":
            kpcell = await bot3ws5.afind(realname, in_column=1)
            kprow = kpcell.row
            spent = float((await bot3ws5.acell_(kprow, 5)).value)
            newspent = spent - itemprice
            await bot3ws5.aupdate_cell(kprow, 5, newspent)
            await ctx.send(realname + " has been refunded " + str(itemprice) + " AKP for " + itemname)
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
            await bot3ws11.aappend_row(logbody)
        elif itemkp == "RBPPUNOX":
            kpcell = await bot3ws6.afind(realname, in_column=1)
            kprow = kpcell.row
            spent = float((await bot3ws6.acell_(kprow, 5)).value)
            newspent = spent - itemprice
            await bot3ws6.aupdate_cell(kprow, 5, newspent)
            await ctx.send(realname + " has been refunded " + str(itemprice) + " RBPPUNOX for " + itemname)
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
            await bot3ws11.aappend_row(logbody)
        elif itemkp == "DPKP":
            kpcell = await bot3ws7.afind(realname, in_column=1)
            kprow = kpcell.row
            spent = float((await bot3ws7.acell_(kprow, 5)).value)
            newspent = spent - itemprice
            await bot3ws7.aupdate_cell(kprow, 5, newspent)
            await ctx.send(realname + " has been refunded " + str(itemprice) + " DPKP for " + itemname)
            logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, itemname, itemprice, itemkp])]
            await bot3ws11.aappend_row(logbody)
        else:
            await ctx.send("Invalid KP type. somehow?")


@client.command(aliases=["refundold"])
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def refundolditem(ctx, name, amount, kp):
    """Processes a refund for an item that was not added to the loot list"""
    amount = float(amount)
    kp = kp.upper()
    if amount <= 0:
        await ctx.send("Amount must be positive.")
        return
    if kp not in KP_WORKSHEETS:
        await ctx.send("Invalid KP pool!")
        return
    ws = KP_WORKSHEETS[kp]["deduct"]
    user_list = await ws.acol_values(1)
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname != None:
        cell = await ws.afind(realname, in_column=1)
        row_num = cell.row
        currentspent = float((await ws.acell_(row_num, 5)).value)
        new = currentspent - amount
        await ws.aupdate_cell(row_num, 5, new)
        await ctx.send(realname + " has been refunded " + str(amount) + " " + kp)
        logbody = ["refund", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, amount, kp])]
        await bot3ws11.aappend_row(logbody)
    else:
        await ctx.send(not_found_message(name, suggestions))


@client.command()
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE")
async def compactloot(ctx, name):
    """Repacks a player's loot row so items sit contiguously from column B."""
    user_list = await bot3ws9.acol_values(1)
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname is None:
        await ctx.send(not_found_message(name, suggestions))
        return

    cell = await bot3ws9.afind(realname, in_column=1)
    row_num = cell.row
    await bot3ws9.arefresh()
    lootlist = await bot3ws9.arow_values(row_num)
    costlist = await bot3ws9.arow_values(row_num + 1)

    width = max(len(lootlist), len(costlist))

    pairs = []
    for i in range(1, width):  # skip col 0 (player name)
        item_cell = lootlist[i] if i < len(lootlist) else ""
        cost_cell = costlist[i] if i < len(costlist) else ""
        item_blank = item_cell is None or str(item_cell).strip() == ""
        cost_blank = cost_cell is None or str(cost_cell).strip() == ""
        if item_blank and cost_blank:
            continue
        pairs.append((item_cell if not item_blank else "", cost_cell if not cost_blank else ""))

    trailing_len = max(width - 1, len(pairs))
    packed_items = [p[0] for p in pairs] + [""] * (trailing_len - len(pairs))
    packed_costs = [p[1] for p in pairs] + [""] * (trailing_len - len(pairs))

    if trailing_len == 0:
        await ctx.send(realname + " has no loot entries to compact.")
        return

    await bot3ws9.aupdate([[sanitize_cell(x) for x in packed_items]], "B" + str(row_num), value_input_option='USER_ENTERED')
    await bot3ws9.aupdate([[sanitize_cell(x) for x in packed_costs]], "B" + str(row_num + 1), value_input_option='USER_ENTERED')

    logbody = ["compactloot", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, len(pairs)])]
    await bot3ws11.aappend_row(logbody)

    await ctx.send(f"Compacted {len(pairs)} item(s) for {realname}.")


@client.command()
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def adjust(ctx, name, number, kp):
    """adjusts a players kp by a certain amount"""
    kp = kp.upper()
    number = float(number)
    if kp not in KP_WORKSHEETS:
        await ctx.send("Invalid KP pool!")
        return
    ws = KP_WORKSHEETS[kp]["admin"]
    user_list = await ws.acol_values(1)
    realname, caps, spaces, suggestions = find_name(name, user_list)
    if realname != None:
        cell = await ws.afind(realname, in_column=1)
        row_num = cell.row
        adjusted = float((await ws.acell_(row_num, 6)).value) + number
        await ws.aupdate_cell(row_num, 6, adjusted)
        await ctx.send(realname + "'s " + kp + " has been adjusted by " + str(number))
        logbody = ["adjust", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([realname, number, kp])]
        await bot3ws11.aappend_row(logbody)
    else:
        await ctx.send(not_found_message(name, suggestions))

@client.command(aliases=["bc"])
@dkp_only()
@commands.has_any_role("General", "REDALiCE")
async def bossconfig(ctx, action, pool = None, bossname = None, points = None):
    """Manage boss-to-KP-pool mappings. Subcommands: list, add, remove, update"""
    action = action.lower()
    if action == "list":
        embed = discord.Embed(title="Boss Configuration", colour=discord.Color.orange())
        for pool_name in ["VKP", "GKP", "PKP", "AKP", "RBPPUNOX", "DPKP", "RBPP"]:
            bosses = BOSS_DICTS[pool_name]
            if bosses:
                boss_lines = ", ".join(b + " (" + str(p) + ")" for b, p in bosses.items())
            else:
                boss_lines = "None"
            embed.add_field(name=pool_name, value=boss_lines, inline=False)
        await ctx.send(embed=embed)
        return
    # all other actions require pool and bossname
    if pool is None or bossname is None:
        await ctx.send("Usage: `$bossconfig " + action + " <pool> <bossname>" + (" <points>`" if action in ["add", "update"] else "`"))
        return
    pool = pool.upper()
    bossname = bossname.capitalize()
    if pool not in BOSS_DICTS:
        await ctx.send("Invalid pool! Valid pools: " + ", ".join(BOSS_DICTS.keys()))
        return
    if action == "add":
        if points is None:
            await ctx.send("Usage: `$bossconfig add <pool> <bossname> <points>`")
            return
        points = int(points)
        if bossname in BOSS_DICTS[pool]:
            await ctx.send(bossname + " already exists in " + pool + " with " + str(BOSS_DICTS[pool][bossname]) + " points. Use `$bossconfig update` to change it.")
            return
        BOSS_DICTS[pool][bossname] = points
        save_bosses()
        await ctx.send("Added " + bossname + " to " + pool + " with " + str(points) + " points.")
        logbody = ["bossconfig add", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([pool, bossname, points])]
        await bot3ws11.aappend_row(logbody)
    elif action == "remove":
        if bossname not in BOSS_DICTS[pool]:
            await ctx.send(bossname + " is not in " + pool + "!")
            return
        old_points = BOSS_DICTS[pool].pop(bossname)
        save_bosses()
        await ctx.send("Removed " + bossname + " from " + pool + " (was " + str(old_points) + " points).")
        logbody = ["bossconfig remove", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([pool, bossname, old_points])]
        await bot3ws11.aappend_row(logbody)
    elif action == "update":
        if points is None:
            await ctx.send("Usage: `$bossconfig update <pool> <bossname> <points>`")
            return
        points = int(points)
        if bossname not in BOSS_DICTS[pool]:
            await ctx.send(bossname + " is not in " + pool + "! Use `$bossconfig add` to add it.")
            return
        old_points = BOSS_DICTS[pool][bossname]
        BOSS_DICTS[pool][bossname] = points
        save_bosses()
        await ctx.send("Updated " + bossname + " in " + pool + " from " + str(old_points) + " to " + str(points) + " points.")
        logbody = ["bossconfig update", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([pool, bossname, old_points, points])]
        await bot3ws11.aappend_row(logbody)
    else:
        await ctx.send("Unknown action! Use: `list`, `add`, `remove`, or `update`")

@client.command()
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def boss(ctx, bossname, toonlist):
    """attendance command"""
    # check the bossname against the lists
    # some bosses have level requirements to check also, so need to pull the row from the roster
    user_list = await acached_col_values(bot4ws1, 1, "roster_names")
    bossname = bossname.capitalize()
    await ctx.send("processing attendance for " + bossname)
    toonlist = toonlist.split(",")
    # remove leading and trailing spaces from the toon list
    toonlist = [x.strip() for x in toonlist]
    rbpp_list = []
    dpkp_list = []
    akp_list = []
    akp_low_list = []
    pkp_list = []
    pkp_low_list = []  
    gkp_list = []
    vkp_list = []
    rbppunox_list = []
    kppool = []
    toonlist = list(set(toonlist))
    currenttime =  dt.now().strftime("%d/%m/%Y %H:%M:%S")
    for t in toonlist:
        findt, caps, spaces, suggestions = find_name(t, user_list)
        if findt is not None:
            cell = await bot4ws1.afind(findt, in_column=1)
            row_num = cell.row
            #get the whole row
            row = pad_row(await bot3ws1.arow_values(row_num), 7)
            level = safe_int(row[3])
            maintoon = row[2]
            maintoon = toBool(maintoon)
            mainchar = row[6]
            #insert level checking here if its needed

            if maintoon and findt not in rbpp_list:
            # rbpp and dino and crom
                if bossname in rbpp_bosses:
                    cell2 = await bot2ws8.afind(findt, in_column=1)
                    row_num2 = cell2.row
                    earned = float((await bot2ws8.acell_(row_num2, 4)).value)
                    new = earned + 1
                    await bot2ws8.aupdate_cell(row_num2, 4, new)
                    await bot5ws8.aupdate_cell(row_num2, 2, currenttime)
                    rbpp_list.append(findt)
                    if "RBPP" not in kppool:
                        kppool.append("RBPP")
                if bossname in dpkp_bosses:
                    cell3 = await bot1ws7.afind(findt, in_column=1)
                    row_num3 = cell3.row
                    earned = float((await bot1ws7.acell_(row_num3, 4)).value)
                    new = earned + dpkp_bosses[bossname]
                    await bot1ws7.aupdate_cell(row_num3, 4, new)
                    await bot5ws7.aupdate_cell(row_num3, 2, currenttime)
                    dpkp_list.append(findt)
                    if "DPKP" not in kppool:
                        kppool.append("DPKP")
                if bossname in rbppunox_bosses:
                    cell8 = await bot2ws6.afind(findt, in_column=1)
                    row_num8 = cell8.row
                    earned = float((await bot2ws6.acell_(row_num8, 4)).value)
                    new = earned + rbppunox_bosses[bossname]
                    await bot2ws6.aupdate_cell(row_num8, 4, new)
                    await bot5ws6.aupdate_cell(row_num8, 2, currenttime)
                    rbppunox_list.append(findt)
                    if "RBPPUNOX" not in kppool:
                        kppool.append("RBPPUNOX")
                if bossname in vkp_bosses:
                    cell7 = await bot1ws2.afind(findt, in_column=1)
                    row_num7 = cell7.row
                    earned = float((await bot1ws2.acell_(row_num7, 4)).value)
                    new = earned + vkp_bosses[bossname]
                    await bot1ws2.aupdate_cell(row_num7, 4, new)
                    await bot5ws2.aupdate_cell(row_num7, 2, currenttime)
                    vkp_list.append(findt)
                    if "VKP" not in kppool:
                        kppool.append("VKP")
            elif mainchar not in rbpp_list:
                if bossname in rbpp_bosses:
                    cell2 = await bot2ws8.afind(mainchar, in_column=1)
                    row_num2 = cell2.row
                    earned = float((await bot2ws8.acell_(row_num2, 4)).value)
                    new = earned + 1
                    await bot2ws8.aupdate_cell(row_num2, 4, new)
                    await bot5ws8.aupdate_cell(row_num2, 2, currenttime)
                    rbpp_list.append(mainchar)
                    if "RBPP" not in kppool:
                        kppool.append("RBPP")
                if bossname in dpkp_bosses:
                    cell3 = await bot1ws7.afind(mainchar, in_column=1)
                    row_num3 = cell3.row
                    earned = float((await bot1ws7.acell_(row_num3, 4)).value)
                    new = earned + dpkp_bosses[bossname]
                    await bot1ws7.aupdate_cell(row_num3, 4, new)
                    await bot5ws7.aupdate_cell(row_num3, 2, currenttime)
                    dpkp_list.append(mainchar)
                    if "DPKP" not in kppool:
                        kppool.append("DPKP")
                if bossname in rbppunox_bosses:
                    cell8 = await bot2ws6.afind(mainchar, in_column=1)
                    row_num8 = cell8.row
                    earned = float((await bot2ws6.acell_(row_num8, 4)).value)
                    new = earned + rbppunox_bosses[bossname]
                    await bot2ws6.aupdate_cell(row_num8, 4, new)
                    await bot5ws6.aupdate_cell(row_num8, 2, currenttime)
                    rbppunox_list.append(mainchar)
                    if "RBPPUNOX" not in kppool:
                        kppool.append("RBPPUNOX")
                if bossname in vkp_bosses:
                    cell7 = await bot1ws2.afind(mainchar, in_column=1)
                    row_num7 = cell7.row
                    earned = float((await bot1ws2.acell_(row_num7, 4)).value)
                    new = earned + vkp_bosses[bossname]
                    await bot1ws2.aupdate_cell(row_num7, 4, new)
                    await bot5ws2.aupdate_cell(row_num7, 2, currenttime)
                    vkp_list.append(mainchar)
                    if "VKP" not in kppool:
                        kppool.append("VKP")
            if bossname in akp_bosses:
                if level >= 220:
                    cell4 = await bot1ws5.afind(findt, in_column=1)
                    row_num4 = cell4.row
                    earned = float((await bot1ws5.acell_(row_num4, 4)).value)
                    new = earned + akp_bosses[bossname]
                    await bot1ws5.aupdate_cell(row_num4, 4, new)
                    await bot5ws5.aupdate_cell(row_num4, 2, currenttime)
                    akp_list.append(findt)
                    if "AKP" not in kppool:
                        kppool.append("AKP")
                else:
                    cell4 = await bot1ws5.afind(findt, in_column=1)
                    row_num4 = cell4.row
                    earned = float((await bot1ws5.acell_(row_num4, 4)).value)
                    new = earned + akp_bosses[bossname] - 5
                    await bot1ws5.aupdate_cell(row_num4, 4, new)
                    await bot5ws5.aupdate_cell(row_num4, 2, currenttime)
                    akp_low_list.append(findt)
                    if "AKP" not in kppool:
                        kppool.append("AKP")
            if bossname in pkp_bosses:
                if level >= 220 or bossname == "Bane":
                    cell5 = await bot1ws4.afind(findt, in_column=1)
                    row_num5 = cell5.row
                    earned = float((await bot1ws4.acell_(row_num5, 4)).value)
                    new = earned + pkp_bosses[bossname]
                    await bot1ws4.aupdate_cell(row_num5, 4, new)
                    await bot5ws4.aupdate_cell(row_num5, 2, currenttime)
                    pkp_list.append(findt)
                    if "PKP" not in kppool:
                        kppool.append("PKP")
                else:
                    cell5 = await bot1ws4.afind(findt, in_column=1)
                    row_num5 = cell5.row
                    earned = float((await bot1ws4.acell_(row_num5, 4)).value)
                    new = earned + pkp_bosses[bossname] - 5
                    await bot1ws4.aupdate_cell(row_num5, 4, new)
                    await bot5ws4.aupdate_cell(row_num5, 2, currenttime)
                    pkp_low_list.append(findt)
                    if "PKP" not in kppool:
                        kppool.append("PKP")
            if bossname in gkp_bosses:
                cell6 = await bot1ws3.afind(findt, in_column=1)
                row_num6 = cell6.row
                earned = float((await bot1ws3.acell_(row_num6, 4)).value)
                new = earned + gkp_bosses[bossname]
                await bot1ws3.aupdate_cell(row_num6, 4, new)
                await bot5ws3.aupdate_cell(row_num6, 2, currenttime)
                gkp_list.append(findt)
                if "GKP" not in kppool:
                    kppool.append("GKP")
        else:
            await ctx.send(not_found_message(t, suggestions))
            toonlist.pop(toonlist.index(t))
    print("creating embed")
    embed = discord.Embed(title = bossname + " Attendance", colour=discord.Color.orange())
    #emptyattend = False
    if len(toonlist) == 0:
        embed.add_field(name = "No toons attended", value = "No KP awarded", inline = False)
        #emptyattend = True
    if rbpp_list != []:
        rbpp_to_send = ', '.join(map(str, rbpp_list))
        embed.add_field(name = "1 RBPP", value = rbpp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "RBPP", str(rbpp_list)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')
    if dpkp_list != []:
        dpkp_to_send = ', '.join(map(str, dpkp_list))
        embed.add_field(name = str(dpkp_bosses[bossname])+ " DPKP", value = dpkp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "DPKP", str(dpkp_list)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')
    if akp_list != []:
        akp_to_send = ', '.join(map(str, akp_list))
        embed.add_field(name = str(akp_bosses[bossname])+ " AKP", value = akp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "AKP", str(akp_list)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')
    if akp_low_list != []:
        akp_low_to_send = ', '.join(map(str, akp_low_list))
        embed.add_field(name = str((akp_bosses[bossname]-5)) + " AKP", value = akp_low_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "AKP", str(akp_low_list)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')
    if pkp_list != []:
        pkp_to_send = ', '.join(map(str, pkp_list))
        embed.add_field(name = str(pkp_bosses[bossname])+ " PKP", value = pkp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "PKP", str(pkp_list)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')
    if pkp_low_list != []:
        pkp_low_to_send = ', '.join(map(str, pkp_low_list))
        embed.add_field(name = str((pkp_bosses[bossname]-5)) + " PKP", value = pkp_low_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "PKP", str(pkp_low_list)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')
    if gkp_list != []:
        gkp_to_send = ', '.join(map(str, gkp_list))
        embed.add_field(name = str(gkp_bosses[bossname])+ " GKP", value = gkp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "GKP", str(gkp_list)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')
    if vkp_list != []:
        vkp_to_send = ', '.join(map(str, vkp_list))
        embed.add_field(name = str(vkp_bosses[bossname])+ " VKP", value = vkp_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "VKP", str(vkp_list)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')
    if rbppunox_list != []:
        rbppunox_to_send = ', '.join(map(str, rbppunox_list))
        embed.add_field(name = str(rbppunox_bosses[bossname])+ " RBPPUNOX", value = rbppunox_to_send, inline = False)
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), "RBPPUNOX", str(rbppunox_list)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')

    print("sending embed")

    # if not emptyattend:
    #     bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname), str(kppool), str(toonlist)]

    await ctx.send(embed=embed)
    logbody = ["boss", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([bossname, toonlist])]
    await bot3ws11.aappend_row(logbody)
    
@client.command()
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def bosshalf(ctx, bossname, toonlist):
    """attendance command that grants half points for the boss"""
    await ctx.send("processing a half point attendance for " + bossname)
    # check the bossname against the lists
    # some bosses have level requirements to check also, so need to pull the row from the roster
    user_list = await acached_col_values(bot3ws1, 1, "roster_names")
    bossname = bossname.capitalize()
    toonlist = toonlist.split(",")
    toonlist = [x.strip() for x in toonlist]
    rbpp_list = []
    dpkp_list = []
    akp_list = []
    akp_low_list = []
    pkp_list = []
    pkp_low_list = []  
    gkp_list = []
    vkp_list = []
    rbppunox_list = []
    kppool = []
    toonlist = list(set(toonlist))
    currenttime =  dt.now().strftime("%d/%m/%Y %H:%M:%S")
    for t in toonlist:
        findt, caps, spaces, suggestions = find_name(t, user_list)
        if findt is not None:
            cell = await bot3ws1.afind(findt, in_column=1)
            row_num = cell.row
            level = safe_int((await bot3ws1.acell_(row_num, 4)).value)
            maintoon = (await bot3ws1.acell_(row_num, 3)).value
            maintoon = toBool(maintoon)
            if bossname in akp_bosses:
                if level >= 220:
                    cell4 = await bot1ws5.afind(findt, in_column=1)
                    row_num4 = cell4.row
                    earned = float((await bot1ws5.acell_(row_num4, 4)).value)
                    new = earned + (akp_bosses[bossname])/2
                    await bot1ws5.aupdate_cell(row_num4, 4, new)
                    await bot5ws5.aupdate_cell(row_num4, 2, currenttime)
                    akp_list.append(findt)
                    if "AKP" not in kppool:
                        kppool.append("AKP")
                else:
                    cell4 = await bot1ws5.afind(findt, in_column=1)
                    row_num4 = cell4.row
                    earned = float((await bot1ws5.acell_(row_num4, 4)).value)
                    new = earned + (akp_bosses[bossname] - 5)/2
                    await bot1ws5.aupdate_cell(row_num4, 4, new)
                    await bot5ws5.aupdate_cell(row_num4, 2, currenttime)
                    akp_low_list.append(findt)
                    if "AKP" not in kppool:
                        kppool.append("AKP")
            if bossname in pkp_bosses:
                if level >= 220 or bossname == "Bane":
                    cell5 = await bot1ws4.afind(findt, in_column=1)
                    row_num5 = cell5.row
                    earned = float((await bot1ws4.acell_(row_num5, 4)).value)
                    new = earned + (pkp_bosses[bossname])/2
                    await bot1ws4.aupdate_cell(row_num5, 4, new)
                    await bot5ws4.aupdate_cell(row_num5, 2, currenttime)
                    pkp_list.append(findt)
                    if "PKP" not in kppool:
                        kppool.append("PKP")
                else:
                    cell5 = await bot1ws4.afind(findt, in_column=1)
                    row_num5 = cell5.row
                    earned = float((await bot1ws4.acell_(row_num5, 4)).value)
                    new = earned + (pkp_bosses[bossname] - 5)/2
                    await bot1ws4.aupdate_cell(row_num5, 4, new)
                    await bot5ws4.aupdate_cell(row_num5, 2, currenttime)
                    pkp_low_list.append(findt)
                    if "PKP" not in kppool:
                        kppool.append("PKP")
            if bossname in gkp_bosses:
                cell6 = await bot1ws3.afind(findt, in_column=1)
                row_num6 = cell6.row
                earned = float((await bot1ws3.acell_(row_num6, 4)).value)
                new = earned + (gkp_bosses[bossname])/2
                await bot1ws3.aupdate_cell(row_num6, 4, new)
                await bot5ws3.aupdate_cell(row_num6, 2, currenttime)
                gkp_list.append(findt)
                if "GKP" not in kppool:
                    kppool.append("GKP")
        else:
            await ctx.send(not_found_message(t, suggestions))
            toonlist.pop(toonlist.index(t))
    embed = discord.Embed(title = bossname + " Attendance", colour=discord.Color.orange())
    emptyattend = False
    if len(toonlist) == 0:
        embed.add_field(name = "No toons attended", value = "No KP awarded", inline = False)
        emptyattend = True
    if rbpp_list != []:
        rbpp_to_send = ', '.join(map(str, rbpp_list))
        embed.add_field(name = "1 RBPP", value = rbpp_to_send, inline = False)
    if dpkp_list != []:
        dpkp_to_send = ', '.join(map(str, dpkp_list))
        embed.add_field(name = str(dpkp_bosses[bossname]/2)+ " DPKP", value = dpkp_to_send, inline = False)
    if akp_list != []:
        akp_to_send = ', '.join(map(str, akp_list))
        embed.add_field(name = str(akp_bosses[bossname]/2)+ " AKP", value = akp_to_send, inline = False)
    if akp_low_list != []:
        akp_low_to_send = ', '.join(map(str, akp_low_list))
        embed.add_field(name = str((akp_bosses[bossname]-5)/2) + " AKP", value = akp_low_to_send, inline = False)
    if pkp_list != []:
        pkp_to_send = ', '.join(map(str, pkp_list))
        embed.add_field(name = str(pkp_bosses[bossname]/2)+ " PKP", value = pkp_to_send, inline = False)
    if pkp_low_list != []:
        pkp_low_to_send = ', '.join(map(str, pkp_low_list))
        embed.add_field(name = str((pkp_bosses[bossname]-5)/2) + " PKP", value = pkp_low_to_send, inline = False)
    if gkp_list != []:
        gkp_to_send = ', '.join(map(str, gkp_list))
        embed.add_field(name = str(gkp_bosses[bossname]/2)+ " GKP", value = gkp_to_send, inline = False)
    if vkp_list != []:
        vkp_to_send = ', '.join(map(str, vkp_list))
        embed.add_field(name = str(vkp_bosses[bossname]/2)+ " VKP", value = vkp_to_send, inline = False)

    if not emptyattend:
        bosslog = [dt.now().strftime("%d/%m/%Y %H:%M:%S"), str(bossname + " HALF"), str(kppool), str(toonlist)]
        await bot3ws10.aappend_row(bosslog, value_input_option='USER_ENTERED')

    await ctx.send(embed=embed)

    logbody = ["bosshalf", str(ctx.author.name), dt.now().strftime("%d/%m/%Y %H:%M:%S"), str([bossname, toonlist])]
    await bot3ws11.aappend_row(logbody)



@client.command(aliases=['plb', 'pointsleaderboard', 'pointslb', 'pointlb'])
@dkp_read()
async def pointleaderboard(ctx, kp, maxkp = 99999, number = 10):
    """displays the leaderboard for current points in a certain KP pool"""
    kp = kp.upper()
    maxkp = float(maxkp)
    number = int(number)
    if kp not in KP_WORKSHEETS or kp == "PKP":
        await ctx.send("Invalid KP pool")
        return
    ws = KP_WORKSHEETS[kp]["read"]
    namelist = (await ws.acol_values(1))[1:]
    pointlist = (await ws.acol_values(7))[1:]
    floatpointlist = [safe_float(x) for x in pointlist]
    combined = list(zip(namelist, floatpointlist))
    sortedcombined = sorted(combined, key=lambda x: x[1], reverse=True)
    # remove the people who have more than maxkp
    sortedcombined = [x for x in sortedcombined if x[1] <= maxkp]
    total = min(number, len(sortedcombined))
    pagecounter = 0
    for i in range(total):
        if i % 20 == 0:
            if i != 0:
                await ctx.send(embed=embed)
            pagecounter += 1
            title = kp + " Leaderboard"
            if total > 20:
                title += " Page " + str(pagecounter)
            embed = discord.Embed(title=title, colour=discord.Color.orange())
        embed.add_field(name=str(i + 1) + ". " + sortedcombined[i][0], value=sortedcombined[i][1], inline=False)
    if total > 0:
        await ctx.send(embed=embed)


@client.command(aliases=['plb30', 'pointsleaderboardlast30', 'pointslb30', 'pointlb30'])
@dkp_read()
async def pointleaderboardlast30(ctx, kp, maxatt = 100, number = 10):
    """darkhealz last 30 command"""
    kp = kp.upper()
    maxatt = int(maxatt)
    number = int(number)
    if kp not in KP_WORKSHEETS or kp == "PKP":
        await ctx.send("Invalid KP pool")
        return
    ws = KP_WORKSHEETS[kp]["read"]
    namelist = (await ws.acol_values(1))[1:]
    pointlist = (await ws.acol_values(7))[1:]
    attlist = (await ws.acol_values(3))[1:]
    floatpointlist = [safe_float(x) for x in pointlist]
    # attlist is in the format "7.49%", so we need to convert it to a float and remove the percentage sign
    # attlist could also be '#DIV/0!' because my sheet math is no good, so we need to handle that
    floatattlist = [safe_float(x) for x in attlist]
    combined = list(zip(namelist, floatpointlist, floatattlist))
    sortedcombined = sorted(combined, key=lambda x: x[2], reverse=True)
    sortedcombined = [x for x in sortedcombined if x[2] <= maxatt]
    sortedcombined = [x for x in sortedcombined if x[1] > 0]
    total = min(number, len(sortedcombined))
    pagecounter = 0
    for i in range(total):
        if i % 20 == 0:
            if i != 0:
                await ctx.send(embed=embed)
            pagecounter += 1
            title = kp + " Leaderboard"
            if total > 20:
                title += " Page " + str(pagecounter)
            embed = discord.Embed(title=title, colour=discord.Color.orange())
        embed.add_field(name=str(i + 1) + ". " + sortedcombined[i][0], value=f"{sortedcombined[i][1]} ({sortedcombined[i][2]}%)", inline=False)
    if total > 0:
        await ctx.send(embed=embed)


@client.command()
@dkp_only()
@commands.has_any_role("General", "REDALiCE")
async def mainswap(ctx, oldname, newname):
    """Swaps the main of a player"""
    # swaps the main of the oldname player.
    # swaps the rbpp, dpkp, and vkp from the oldname to the newname
    # swaps all the characters owned by this person to the newname

    # get oldname current points
    roster_names = await acached_col_values(bot3ws1, 1, "roster_names")
    findoldname, caps_old, spaces_old, suggestions_old = find_name(oldname, roster_names)
    findnewname, caps_new, spaces_new, suggestions_new = find_name(newname, roster_names)

    if findoldname is None:
        await ctx.send(not_found_message(oldname, suggestions_old))
        return
    if findnewname is None:
        await ctx.send(not_found_message(newname, suggestions_new))
        return

    # cache all find() row lookups — avoids ~25 redundant API reads
    old_roster_cell = await bot1ws1.afind(findoldname, in_column = 1)
    old_roster_row = old_roster_cell.row
    new_roster_cell = await bot1ws1.afind(findnewname, in_column = 1)
    new_roster_row = new_roster_cell.row
    old_rbpp_cell = await bot1ws8.afind(findoldname, in_column = 1)
    old_rbpp_row = old_rbpp_cell.row
    new_rbpp_cell = await bot1ws8.afind(findnewname, in_column = 1)
    new_rbpp_row = new_rbpp_cell.row
    old_dpkp_cell = await bot1ws7.afind(findoldname, in_column = 1)
    old_dpkp_row = old_dpkp_cell.row
    new_dpkp_cell = await bot1ws7.afind(findnewname, in_column = 1)
    new_dpkp_row = new_dpkp_cell.row
    old_vkp_cell = await bot1ws2.afind(findoldname, in_column = 1)
    old_vkp_row = old_vkp_cell.row
    new_vkp_cell = await bot1ws2.afind(findnewname, in_column = 1)
    new_vkp_row = new_vkp_cell.row

    # check if oldname and newname have the same main (ie are owned by the same person)
    oldcell = (await bot5ws1.aacell(f'G{old_roster_row}')).value
    newcell = (await bot5ws1.aacell(f'G{new_roster_row}')).value
    if oldcell != newcell:
        await ctx.send("These characters are not owned by the same person.")
        return

    # set oldname main to false, newname main to true
    await bot5ws1.aupdate_acell(f'C{old_roster_row}', 'FALSE')
    await bot5ws1.aupdate_acell(f'C{new_roster_row}', 'TRUE')

    # set all instances of oldname to newname in column G of bot5ws1
    characters_list = await bot5ws1.acol_values(7)
    for i in range(len(characters_list)):
        if characters_list[i] == findoldname:
            await bot5ws1.aupdate_acell(f'G{i + 1}', findnewname)

    oldrbppe = (await bot5ws8.aacell(f'D{old_rbpp_row}')).value
    olddpkpe = (await bot5ws7.aacell(f'D{old_dpkp_row}')).value
    oldvkpe = (await bot5ws2.aacell(f'D{old_vkp_row}')).value

    oldrbpps = (await bot5ws8.aacell(f'E{old_rbpp_row}')).value
    olddpkps = (await bot5ws7.aacell(f'E{old_dpkp_row}')).value
    oldvkps = (await bot5ws2.aacell(f'E{old_vkp_row}')).value

    oldrbppa = (await bot5ws8.aacell(f'F{old_rbpp_row}')).value
    olddpkpa = (await bot5ws7.aacell(f'F{old_dpkp_row}')).value
    oldvkpa = (await bot5ws2.aacell(f'F{old_vkp_row}')).value

    print(f"Old main {findoldname} has {oldrbppe} RBPP, {olddpkpe} DPKP, and {oldvkpe} VKP")

    # set newnames points to the oldmains values.
    await bot5ws8.aupdate_acell(f'D{new_rbpp_row}', oldrbppe)
    await bot5ws7.aupdate_acell(f'D{new_dpkp_row}', olddpkpe)
    await bot5ws2.aupdate_acell(f'D{new_vkp_row}', oldvkpe)

    await bot5ws8.aupdate_acell(f'E{new_rbpp_row}', oldrbpps)
    await bot5ws7.aupdate_acell(f'E{new_dpkp_row}', olddpkps)
    await bot5ws2.aupdate_acell(f'E{new_vkp_row}', oldvkps)

    await bot5ws8.aupdate_acell(f'F{new_rbpp_row}', oldrbppa)
    await bot5ws7.aupdate_acell(f'F{new_dpkp_row}', olddpkpa)
    await bot5ws2.aupdate_acell(f'F{new_vkp_row}', oldvkpa)

    # set the oldnames points to 0
    await bot5ws8.aupdate_acell(f'D{old_rbpp_row}', 0)
    await bot5ws7.aupdate_acell(f'D{old_dpkp_row}', 0)
    await bot5ws2.aupdate_acell(f'D{old_vkp_row}', 0)

    await bot5ws8.aupdate_acell(f'E{old_rbpp_row}', 0)
    await bot5ws7.aupdate_acell(f'E{old_dpkp_row}', 0)
    await bot5ws2.aupdate_acell(f'E{old_vkp_row}', 0)

    await bot5ws8.aupdate_acell(f'F{old_rbpp_row}', 0)
    await bot5ws7.aupdate_acell(f'F{old_dpkp_row}', 0)
    await bot5ws2.aupdate_acell(f'F{old_vkp_row}', 0)

    await ctx.send(f"Swapped main from {findoldname} to {findnewname}. {findnewname} now has {oldrbppe} RBPP, {olddpkpe} DPKP, and {oldvkpe} VKP")

@client.command()
@dkp_only()
@commands.has_any_role("General", "REDALiCE")
async def newowner(ctx, confirmation, *charnames):
    """wipes the points on a character by adjusting them to zero, sets all the wins to [OLD] prefix, and sets the main to Blank"""
    if confirmation != "confirmnewowner":
        await ctx.send("⚠️ This permanently zeroes all KP pools and relabels loot as [OLD] for the named "
                       "characters. If you're sure, re-run as: `$newowner confirmnewowner <char1> <char2> ...`")
        return
    charnames = list(charnames)
    charnames = [x.strip() for x in charnames]
    sendlist = []
    roster_names_for_newowner = await acached_col_values(bot3ws1, 1, "roster_names")
    for c in charnames:
        findc, caps, spaces, suggestions = find_name(c, roster_names_for_newowner)
        if findc is not None:
            # set the main to Blank
            roster_cell = await bot1ws1.afind(findc, in_column = 1)
            await bot5ws1.aupdate_acell(f'G{roster_cell.row}', '')
            # set all the wins to [OLD] prefix
            # for each column above 2 in ws9 in the row
            # get the name, append [OLD] to the front, and update the cell
            loot_cell = await bot1ws9.afind(findc, in_column = 1)
            row = loot_cell.row
            for col in range(2, bot1ws9.col_count + 1):
                # handle column letter greater than 26 -> AA, AB, etc
                colletter = ''
                if col > 26:
                    colletter += chr(64 + (col // 26))
                    colletter += chr(64 + (col % 26))
                else:
                    colletter = chr(64 + col)
                name = (await bot1ws9.aacell(f'{colletter}{row}')).value
                print("changing " + str(name) + " in cell " + f'{colletter}{row}')
                if name != '' and name is not None and not name.startswith('[OLD] '):
                    newname = '[OLD] ' + name
                    await bot1ws9.aupdate_acell(f'{colletter}{row}', newname)
                else:
                    # stop the for loop, we have reached the end
                    break
            # set the points to 0 by adjusting them
            # get the current points in column g
            # add that value to column f
            vkp4_cell = await bot4ws2.afind(findc, in_column = 1)
            vkp1_cell = await bot1ws2.afind(findc, in_column = 1)
            currvkp = float((await bot5ws2.aacell(f'G{vkp4_cell.row}')).value)
            adjustedvkp = float((await bot5ws2.aacell(f'F{vkp4_cell.row}')).value)
            await bot5ws2.aupdate_acell(f'F{vkp1_cell.row}', adjustedvkp - currvkp)

            gkp4_cell = await bot4ws3.afind(findc, in_column = 1)
            gkp1_cell = await bot1ws3.afind(findc, in_column = 1)
            currgkp = float((await bot5ws3.aacell(f'G{gkp4_cell.row}')).value)
            adjustedgkp = float((await bot5ws3.aacell(f'F{gkp4_cell.row}')).value)
            await bot5ws3.aupdate_acell(f'F{gkp1_cell.row}', adjustedgkp - currgkp)

            pkp4_cell = await bot4ws4.afind(findc, in_column = 1)
            pkp1_cell = await bot1ws4.afind(findc, in_column = 1)
            currpkp = float((await bot5ws4.aacell(f'G{pkp4_cell.row}')).value)
            adjustedpkp = float((await bot5ws4.aacell(f'F{pkp4_cell.row}')).value)
            await bot5ws4.aupdate_acell(f'F{pkp1_cell.row}', adjustedpkp - currpkp)

            akp4_cell = await bot4ws5.afind(findc, in_column = 1)
            akp1_cell = await bot1ws5.afind(findc, in_column = 1)
            currakp = float((await bot5ws5.aacell(f'G{akp4_cell.row}')).value)
            adjustedakp = float((await bot5ws5.aacell(f'F{akp4_cell.row}')).value)
            await bot5ws5.aupdate_acell(f'F{akp1_cell.row}', adjustedakp - currakp)

            rbppunox4_cell = await bot4ws6.afind(findc, in_column = 1)
            rbppunox1_cell = await bot1ws6.afind(findc, in_column = 1)
            currrbppunox = float((await bot5ws6.aacell(f'G{rbppunox4_cell.row}')).value)
            adjustedrbppunox = float((await bot5ws6.aacell(f'F{rbppunox4_cell.row}')).value)
            await bot5ws6.aupdate_acell(f'F{rbppunox1_cell.row}', adjustedrbppunox - currrbppunox)

            dpkp4_cell = await bot4ws7.afind(findc, in_column = 1)
            dpkp1_cell = await bot1ws7.afind(findc, in_column = 1)
            currdpkp = float((await bot5ws7.aacell(f'G{dpkp4_cell.row}')).value)
            adjusteddpkp = float((await bot5ws7.aacell(f'F{dpkp4_cell.row}')).value)
            await bot5ws7.aupdate_acell(f'F{dpkp1_cell.row}', adjusteddpkp - currdpkp)

            rbpp4_cell = await bot4ws8.afind(findc, in_column = 1)
            rbpp1_cell = await bot1ws8.afind(findc, in_column = 1)
            currrbpp = float((await bot5ws8.aacell(f'G{rbpp4_cell.row}')).value)
            adjustedrbpp = float((await bot5ws8.aacell(f'F{rbpp4_cell.row}')).value)
            await bot5ws8.aupdate_acell(f'F{rbpp1_cell.row}', adjustedrbpp - currrbpp)

            sendlist.append(findc)
        else:
            await ctx.send(not_found_message(c, suggestions))
    await ctx.send("Processed the following characters: " + ', '.join(sendlist))

@client.command(aliases=['cplb', 'classpointsleaderboard', 'classpointslb', 'classpointlb'])
@dkp_read()
async def classpointleaderboard(ctx, kp, classname, maxkp = 99999, number = 10):
    """displays the leaderboard for current points in a certain KP pool for a certain class"""
    kp = kp.upper()
    classname = classname.capitalize()
    maxkp = float(maxkp)
    sheet1names = await bot4ws1.acol_values(1)
    sheet1classes = await bot4ws1.acol_values(5)
    classnamelist = []
    for i in range(len(sheet1names)):
        if sheet1classes[i].capitalize() == classname:
            classnamelist.append(sheet1names[i])
    if kp not in KP_WORKSHEETS or kp == "PKP":
        await ctx.send("Invalid KP pool")
        return
    ws = KP_WORKSHEETS[kp]["read"]
    namelist = (await ws.acol_values(1))[1:]
    pointlist = (await ws.acol_values(7))[1:]
    floatpointlist = [safe_float(x) for x in pointlist]
    combined = list(zip(namelist, floatpointlist))
    sortedcombined = sorted(combined, key=lambda x: x[1], reverse=True)
    sortedcombined = [x for x in sortedcombined if x[1] <= maxkp]
    sortedcombined = [x for x in sortedcombined if x[0] in classnamelist]
    total = min(number, len(sortedcombined))
    pagecounter = 0
    for i in range(total):
        if i % 20 == 0:
            if i != 0:
                await ctx.send(embed=embed)
            pagecounter += 1
            title = kp + " Leaderboard"
            if total > 20:
                title += " Page " + str(pagecounter)
            embed = discord.Embed(title=title, colour=discord.Color.orange())
        embed.add_field(name=str(i + 1) + ". " + sortedcombined[i][0], value=sortedcombined[i][1], inline=False)
    if total > 0:
        await ctx.send(embed=embed)


@client.command(aliases=['elb', 'earnedpointsleaderboard', 'earnedpointslb', 'earnedpointlb'])
@dkp_read()
async def earnedleaderboard(ctx, kp, number = 10):
    """displays the leaderboard for total points earned in a certain KP pool"""
    kp = kp.upper()
    if kp not in KP_WORKSHEETS or kp == "PKP":
        await ctx.send("Invalid KP pool")
        return
    ws = KP_WORKSHEETS[kp]["read"]
    namelist = (await ws.acol_values(1))[1:]
    pointlist = (await ws.acol_values(4))[1:]
    floatpointlist = [safe_float(x) for x in pointlist]
    combined = list(zip(namelist, floatpointlist))
    sortedcombined = sorted(combined, key=lambda x: x[1], reverse=True)
    total = min(number, len(sortedcombined))
    pagecounter = 0
    for i in range(total):
        if i % 20 == 0:
            if i != 0:
                await ctx.send(embed=embed)
            pagecounter += 1
            title = kp + " Leaderboard"
            if total > 20:
                title += " Page " + str(pagecounter)
            embed = discord.Embed(title=title, colour=discord.Color.orange())
        embed.add_field(name=str(i + 1) + ". " + sortedcombined[i][0], value=sortedcombined[i][1], inline=False)
    if total > 0:
        await ctx.send(embed=embed)

@client.command(aliases=["generate"])
@dkp_only()
async def gen(ctx):
    """Generates boss and bosshalf commands based on the channel content before the gen command"""
    channel = ctx.channel
    messages = [message async for message in channel.history(limit=100)]
    messages.reverse()
    # i expect this to be called in a thread, if so, get the thread title
    thread_title = None
    if isinstance(channel, discord.Thread):
        thread_title = channel.name

    bosses = ""
    # get the boss names from the dicts
    for bossnames in akp_bosses.keys():
        bosses += bossnames + ", "
    for bossnames in gkp_bosses.keys():
           if bossnames not in bosses:
               bosses += bossnames + ", "
    for bossnames in vkp_bosses.keys():
               if bossnames not in bosses:
                   bosses += bossnames + ", "
    for bossnames in pkp_bosses.keys():
           if bossnames not in bosses:
               bosses += bossnames + ", "
    for bossnames in rbppunox_bosses.keys():
        if bossnames not in bosses:
            bosses += bossnames + ", "
    for bossnames in dpkp_bosses.keys():
        if bossnames not in bosses:
            bosses += bossnames + ", "
    for bossnames in rbpp_bosses.keys():
        if bossnames not in bosses:
            bosses += bossnames + ", "
    bosses = bosses[:-2]
    toonnames = await bot5ws1.acol_values(1)
    
    charnames = []
    charhalfnames = []
    missingnames = []
    for message in messages:
        if message.content.startswith("$gen"):
            break
        else:
            # try to pick character names from the message content
            content = message.content
            tokens = content.split()
            for token in tokens:
                clean_token = re.sub(r'[^0-9A-Za-z]', '', token)
                findt, caps, spaces, suggestions = find_name(token, toonnames)
                # first check if the next token is "HALF"xxxxxxx
                if clean_token.upper() == "HALF":
                    if len(charnames) > 0:
                        charhalfnames.append(charnames[-1])
                        # remove the last charname from charnames
                        charnames.pop()
                elif clean_token.upper() == "TO":
                    # remove the last charname from charnames
                    if len(charnames) > 0:
                        removed = charnames.pop()
                        print("Removed " + removed + " due to 'to' token")
                elif findt is not None and findt not in charnames:
                    charnames.append(findt)
                # if findt is None, try and combine it with the previous token
                elif len(tokens) > 1:
                    prev_token = tokens[tokens.index(token) - 1]
                    combined_token = prev_token + clean_token
                    findt, caps, spaces, suggestions = find_name(combined_token, toonnames)
                    if findt is not None and findt not in charnames:
                        charnames.append(findt)
                else:
                    missingnames.append(token)
    bossname = None
                
    if thread_title is not None:
        # try and find the boss name from the thread title, from the bosses in inputterinfo
        bossname = None
        for b in bosses.split(", "):
            if b.upper() in thread_title.upper():
                bossname = b
                break
    if bossname is None:
        bossname = "BOSSNAME"    
    if len(charnames) > 0:
        msg = "$boss " + bossname + " \"" + ', '.join(charnames) + "\"\n"
        await ctx.send(msg)
    if len(charhalfnames) > 0:
        msg = "$bosshalf " + bossname + " \"" + ', '.join(charhalfnames) + "\"\n"
        await ctx.send(msg)
    if len(missingnames) > 0:
        await ctx.send("Could not find the following names: " + ', '.join(missingnames))


@client.command()
@dkp_only()
async def dg(ctx):
    """displays the currently eligible players for dg armour"""
    print("[DG] Starting DG eligibility check")
    dglist = await sheet_call(bot4ws13.col_values, 1)
    mainlist = await sheet_call(bot4ws13.col_values, 2)
    set_number = await sheet_call(bot4ws13.col_values, 4)
    helm = await sheet_call(bot4ws13.col_values, 10)
    bt_helm = await sheet_call(bot4ws13.col_values, 11)
    next_item = await sheet_call(bot4ws13.col_values, 12)
    last_received = await sheet_call(bot4ws13.col_values, 13) # last received and last polls are dates, like Dec 20, 2025
    last_polls = await sheet_call(bot4ws13.col_values, 15)
    print(f"[DG] Loaded {len(dglist)-1} players from sheet")
    # remove the headers
    del dglist[0]
    del mainlist[0]
    del set_number[0]
    del helm[0]
    del bt_helm[0]
    del next_item[0]
    del last_received[0]
    del last_polls[0]
    print(f"[DG] Processing {len(dglist)} players")

    # Set 1: 15% RBPP attendance, poll CD >= 1, per-item RBPP (Gloves 100, Top 200, Boots 250, Legs 350)
    # Set 2: 25% RBPP attendance, poll CD >= 2, total RBPP >= 500
    # Set 3+: 25% RBPP attendance, poll CD >= 3, total RBPP >= 1000
    #         BT Helm -> 3 pures (gloves+boots), No BT Helm -> 5 pures (gloves+legs)
    #         Must finish previous toon's set before eligible for next

    def parse_date(raw_value):
        if raw_value is None:
            return None
        if isinstance(raw_value, dt):
            return raw_value
        text = str(raw_value).strip()
        if text == "":
            return None
        # excel / sheets serial to datetime
        try:
            serial = float(text)
            if serial > 0 and serial.is_integer():
                result = dt.fromordinal(int(serial) + 693594)
                print(f"[DG] Parsed serial {serial} to {result}")
                return result
        except (ValueError, OverflowError):
            pass
        for fmt in ("%b %d, %Y", "%b %d %Y", "%B %d, %Y", "%B %d %Y", "%m/%d/%Y", "%Y-%m-%d"):
            try:
                result = dt.strptime(text, fmt)
                return result
            except ValueError:
                try:
                    result = dt.strptime(text.title(), fmt)
                    return result
                except ValueError:
                    continue
        return None

    def extract_poll_dates(raw_value):
        if raw_value is None:
            print("[DG] extract_poll_dates: raw_value is None")
            return []
        if isinstance(raw_value, list):
            parts = raw_value
        else:
            text = str(raw_value)
            # find all date-looking substrings without breaking month/day commas
            parts = re.findall(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}", text, flags=re.IGNORECASE)
            if not parts:
                # fallback to line / semicolon splits
                parts = re.split(r"[;\n]+", text)
        dates = []
        for part in parts:
            parsed = parse_date(part.strip())
            if parsed is not None:
                dates.append(parsed)
        #print(f"[DG] extract_poll_dates: found {len(dates)} dates")
        return dates

    def polls_since(received_value, polls_list):
        """Calculate polls since last received item.
        Args:
            received_value: raw date value of when item was last received
            polls_list: list of poll date strings to parse
        Returns:
            index of the poll that matches received_date, or len(polls_list) if not found
        """
        received_date = parse_date(received_value)
        # print(f"[DG] polls_since: received_value='{received_value}', polls_list={polls_list}")
        
        # Parse all poll dates from the list
        poll_dates = []
        if isinstance(polls_list, list):
            for poll_entry in polls_list:
                if poll_entry and str(poll_entry).strip():
                    parsed = parse_date(poll_entry)
                    if parsed is not None:
                        poll_dates.append(parsed)
                        # print(f"[DG] polls_since: parsed poll '{poll_entry}' -> {parsed}")
        else:
            # If it's a string, try to extract multiple dates
            poll_dates = extract_poll_dates(polls_list)
        
        # print(f"[DG] polls_since: received_date={received_date}, num_poll_dates={len(poll_dates)}")
        if received_date is None or not poll_dates:
            # print(f"[DG] polls_since: returning 0 (no dates)")
            return 0
        
        # Find the index where received_date matches a poll_date
        for idx, poll_date in enumerate(poll_dates):
            if poll_date.date() == received_date.date():
                # print(f"[DG] polls_since: found match at index {idx}")
                return idx
        
        # if not found, assume all polls are since the last received
        # print(f"[DG] polls_since: no match found, returning {len(poll_dates)}")
        return len(poll_dates)

    rbpp_list = await bot5ws8.acol_values(1)
    rbpp_total_list = await bot5ws8.acol_values(7)
    rbpp_percentage_list = await bot5ws8.acol_values(3)
    del rbpp_list[0]
    del rbpp_percentage_list[0]
    del rbpp_total_list[0]
    print(f"[DG] Loaded RBPP data for {len(rbpp_list)} players")

    # Pre-build lookups per owner
    owner_incomplete_sets = {}  # which set numbers are still incomplete
    for i in range(len(dglist)):
        owner = mainlist[i].lower()
        try:
            sn = int(set_number[i])
        except (ValueError, TypeError):
            continue
        if next_item[i].lower() != "complete":
            owner_incomplete_sets.setdefault(owner, set()).add(sn)

    # Build owner -> list of (parsed_date, raw_string) from UNFILTERED Doch Tracker (bot4ws12)
    # Scan columns F-K (item award dates: Gloves/Chest/Boots/Pants/Helm/BtHelm) AND M (Last received)
    # so we find the most recent award even if Last Received column wasn't updated.
    all_dg_owners = await sheet_call(bot4ws12.col_values, 2)
    item_cols = [await sheet_call(bot4ws12.col_values, c) for c in (6, 7, 8, 9, 10, 11, 13)]
    del all_dg_owners[0]
    for c in item_cols:
        del c[0]
    owner_dates = {}  # owner_lower -> list of (parsed_date, raw_value)
    for i in range(len(all_dg_owners)):
        owner = all_dg_owners[i].strip().lower()
        if not owner:
            continue
        for col_list in item_cols:
            if i < len(col_list):
                v = col_list[i]
                p = parse_date(v)
                if p is not None and p.year >= 1900:
                    owner_dates.setdefault(owner, []).append((p, v))

    eligible_players = []
    for i in range(len(dglist)):
        rbpp_index = None
        for j in range(len(rbpp_list)):
            if mainlist[i].lower() == rbpp_list[j].lower():
                rbpp_index = j
                break
        rbpp_percentage = float(rbpp_percentage_list[rbpp_index].strip('%')) if rbpp_index is not None else 0.0

        setnum_raw = set_number[i]
        try:
            setnum = int(setnum_raw)
        except (ValueError, TypeError):
            print(f"[DG] {dglist[i]}: Skipping - invalid set number '{setnum_raw}'")
            continue

        print(f"[DG] Checking {dglist[i]}: RBPP%={rbpp_percentage}%, Set={setnum}, NextItem={next_item[i]}")

        if next_item[i].lower() == "complete":
            continue

        # Set 1 requires 15% RBPP attendance, Set 2+ requires 25%
        required_attendance = 15.0 if setnum == 1 else 25.0
        if rbpp_percentage < required_attendance:
            print(f"[DG] {dglist[i]}: Not eligible - RBPP%={rbpp_percentage} < {required_attendance}%")
            continue

        # Use the most recent date across ALL of the owner's characters & item columns for polls_since and display
        owner_key = mainlist[i].strip().lower()
        candidates = list(owner_dates.get(owner_key, []))
        # Include this character's own last_received as a fallback safety net
        own_parsed = parse_date(last_received[i])
        if own_parsed is not None and own_parsed.year >= 1900:
            candidates.append((own_parsed, last_received[i]))
        if candidates:
            best_parsed, best_raw = max(candidates, key=lambda x: x[0])
            effective_last_received = best_raw
            display_last_received = best_raw
        else:
            effective_last_received = last_received[i]
            display_last_received = "N/A"
        polls_since_last = polls_since(effective_last_received, last_polls)
        rbpp = float(rbpp_total_list[rbpp_index]) if rbpp_index is not None else 0.0
        has_bt_helm = (bt_helm[i].strip().upper() == "BT" if i < len(bt_helm) else False) or \
                      (helm[i].strip().upper() == "BT" if i < len(helm) else False)

        print(f"[DG] {dglist[i]}: Attendance OK, Set={setnum}, PollsSince={polls_since_last}, RBPP={rbpp}, BT_Helm={has_bt_helm}")

        if setnum == 1:
            if polls_since_last >= 1:
                item_lower = next_item[i].lower()
                if item_lower == "gloves" and rbpp >= 100:
                    print(f"[DG] {dglist[i]}: ELIGIBLE - Set 1 Gloves")
                    eligible_players.append((dglist[i], mainlist[i], next_item[i], display_last_received, rbpp_percentage, setnum, None))
                elif item_lower in ("chest", "top") and rbpp >= 200:
                    print(f"[DG] {dglist[i]}: ELIGIBLE - Set 1 Top")
                    eligible_players.append((dglist[i], mainlist[i], next_item[i], display_last_received, rbpp_percentage, setnum, None))
                elif item_lower == "boots" and rbpp >= 250:
                    print(f"[DG] {dglist[i]}: ELIGIBLE - Set 1 Boots")
                    eligible_players.append((dglist[i], mainlist[i], next_item[i], display_last_received, rbpp_percentage, setnum, None))
                elif item_lower in ("pants", "legs") and rbpp >= 350:
                    print(f"[DG] {dglist[i]}: ELIGIBLE - Set 1 Legs")
                    eligible_players.append((dglist[i], mainlist[i], next_item[i], display_last_received, rbpp_percentage, setnum, None))
                else:
                    print(f"[DG] {dglist[i]}: Not eligible - item/rbpp requirement not met")
            else:
                print(f"[DG] {dglist[i]}: Not eligible - polls_since_last={polls_since_last} < 1")

        elif setnum == 2:
            if polls_since_last >= 2 and rbpp >= 500:
                print(f"[DG] {dglist[i]}: ELIGIBLE - Set 2")
                eligible_players.append((dglist[i], mainlist[i], next_item[i], display_last_received, rbpp_percentage, setnum, None))
            else:
                print(f"[DG] {dglist[i]}: Not eligible - polls={polls_since_last}<2 or rbpp={rbpp}<500")

        elif setnum >= 3:
            # Must finish farming previous toon's set before eligible for next
            owner = mainlist[i].lower()
            incomplete = owner_incomplete_sets.get(owner, set())
            lower_incomplete = {s for s in incomplete if s < setnum}
            if lower_incomplete:
                print(f"[DG] {dglist[i]}: Not eligible - owner has incomplete lower sets: {lower_incomplete}")
                continue

            if polls_since_last >= 3 and rbpp >= 1000:
                if has_bt_helm:
                    alloc_note = "3 pures (gloves+boots) | Farm chest+legs from VoA"
                else:
                    alloc_note = "5 pures (gloves+legs) | Farm helm+chest+boots from VoA"
                print(f"[DG] {dglist[i]}: ELIGIBLE - Set {setnum} ({alloc_note})")
                eligible_players.append((dglist[i], mainlist[i], next_item[i], display_last_received, rbpp_percentage, setnum, alloc_note))
            else:
                print(f"[DG] {dglist[i]}: Not eligible - polls={polls_since_last}<3 or rbpp={rbpp}<1000")

    print(f"[DG] Found {len(eligible_players)} eligible players")

    # Sanity check: warn if the same character name appears more than once in the sheet
    char_counts = {}
    for name in dglist:
        key = name.strip().lower()
        if key:
            char_counts[key] = char_counts.get(key, 0) + 1
    duplicate_chars = [n for n, c in char_counts.items() if c > 1]
    if duplicate_chars:
        print(f"[DG] WARNING: Duplicate character names found in sheet: {duplicate_chars}")

    embed = discord.Embed(title = "DG Armour Eligibility", colour=discord.Color.orange())
    for toon, main, nxt_item, last_recv, pct, sn, alloc in eligible_players:
        value_text = f"Next Item: {nxt_item}, Last Received: {last_recv}, RBPP%: {pct}"
        if alloc:
            value_text += f"\n{alloc}"
        embed.add_field(name=f"{toon} (Main: {main}) [Set {sn}]", value=value_text, inline=False)
    if not eligible_players:
        embed.description = "No players currently eligible."
    await ctx.send(embed=embed)
    print("[DG] DG eligibility check complete")

@client.command()
@dkp_only()
@commands.has_any_role("General", "Guardian", "REDALiCE", "Helper")
async def massdeduct(ctx, *message):
    """mass deduct command to be used in conjunction with bidgen. reply to the bidgen message or copy paste it in"""
    if ctx.message.reference is not None:
        # get the referenced message
        ref_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        message_content = ref_message.content
    else:
        message_content = ' '.join(message)
    lines = message_content.split('\n')
    # ignore the first line (expecting it to be the $bidgen and "generated bid commands")
    for line in lines[1:]:
        if line.startswith("$deduct"):
            result = await sheet_call(internal_deduct, line)
            await ctx.send(result)
            await asyncio.sleep(15)  # Rate limit to 4 calls per minute (60s / 4 = 15s between calls)
    

@client.command()
@dkp_only()
async def apply(ctx):
    """allows new members to apply for the clan"""
    await ctx.send("Please fill out the application form here: https://forms.gle/zDD3mr56xELXUG4n6")
    leaderchannelid = 1180242808070742117
    leaderchannel = client.get_channel(leaderchannelid)
    await leaderchannel.send("New application started by " + str(ctx.author.name))


@client.command()
@dkp_only()
async def new(ctx):
    """Displays the help for new players"""
    await ctx.send("""Welcome to Relentless! Please start by sending your toon names and levels to the character-declaration channel, along with which is your main.
For Example:
Main: REDALiCE, 220 DPS Druid
Alts: LiLALiCE, 180 Fire Mage
BiGALiCE, 178 Sword Warrior               

as this discord bot is a work in progress, please also set up an account on our website. This is found at http://www.relentless.dkpsystem.com

A leader will approve all this shortly so you can start earning KP (Kill points)
                   
All the point acronyms may be confusing at first, but here is the break down:
                   
VKP - Dragon Kill Points (earned for killing Crom)
AKP - Arcane Kill Points (earned for killing Gelebron and Proteus)
GKP - Gardens Kill Points (earned for killing Bloodthorn and Factions)
DPKP - Dino Kill Points (earned for killing Dino)
RBPP - Relentless Boss Participation Points (earned for attending raids that give KP, not legacies)
                   
send \"$new2\" for the next steps!""")
    
@client.command()
@dkp_only()
async def new2(ctx):
    """displays the second set of help for new players"""
    await ctx.send("""You are setup and ready to start earning some points! Your Recruitment period will be 1 month, and you are required to get 50 RBPP (attendance points) through this period to be promoted. 

Please take some time to get familiar with the Relentless Rules document, here you can find all the rules each player in Relentless must abide by. You can find the rules doc here. https://docs.google.com/document/d/1WT0nh2NzUh2XQpnODY3zPMe_35KwQImsznA7dXqGxds/mobilebasic
                   
Once you read this, you may have some questions! Feel free to ask for clarification in the #question-faq channel.
                   
As this is a lot of information to take in, please allow yourself to review this content over the course of a few days. And of course if you have any further questions please reach out to a fellow clannie or a leader. The Winston bot is also a valuable resource created by REDALiCE (and largely plagiarised from Magister22's bot Magi Jr), you can type “$information” and get a wide assortment of answers. Once you finish and fully understand the rules, please type $new3.""")
    
@client.command()
@dkp_only()
async def new3(ctx):
    """displays the third set of help for new players"""
    await ctx.send("""So you are now setup to earn points and know the rules. You are ready to start grinding points. It is important to note, each toon is considered its separate toon. It earns its own points, and spends its own points. You are allowed to transfer points from one toon to another only up to 4 hours after the attend has been posted in KP chat. After that you can no longer transfer those points.
                   
CAMPING! Camping is the easiest way to earn points! If you are camping a raid while it is open (Mord Necro Hrung Gele BT) and another raid spawns while you are/have been camping it, you will receive FULL POINTS to the toon camping that is unable to attend the raid due to camping. Please note you can only collect points for a single toon for camping each spawning raid.
                   
(You can not log when a raid spawns and run to camp something, you must have been camping before/during when the raid spawns). Be sure to say in KP chat after the raid attend is posted “(Toon you wish to receive points on) was camping (raid camping)” to get points. You do not need to camp with the toon you want points on, any toon you camp with will suffice.

Congratulations you have completed the Relentless Orientation. Again, if you have any questions at all please reach out to a fellow clannie or leader and we will be happy to help you out. You can type “$leadership” for a list of the current leaders. We strive to see everyone succeed and thrive here in Relentless, Have Fun!""")
    

@client.command()
@dkp_only()
async def clanrules(ctx):
    """Displays the clan rules"""
    await ctx.send("""Here is the link to the Relentless Clan rules:
https://docs.google.com/document/d/1WT0nh2NzUh2XQpnODY3zPMe_35KwQImsznA7dXqGxds/mobilebasic""")


@client.command()
@dkp_only()
async def kpinfo(ctx):
    """Displays the KP information"""
    await ctx.send("""Here is the breakdown of the KP pools:
                   
VKP (Valley kill points); earned from Crom (maybe future Valley content)
Used to bid on Crom Gear
GKP (Garden kill points); earned from Bloodthorn and Weekly bosses
Used to bid on Bloodthorn items
AKP (Arcane kill points); earned from Gelebron and Proteus
Used to bid on Gelebron items
LEP (Legacy kill points); Old legacy point pool. unused, repurposed for RBPPUNOX
DPKP (Dhiothu kill points); earned from Dhiothu
Used to bid on Dhiothu items
RBPP (attendance points); earned from all bosses listed above except Weekly bosses and Legacy bosses
RBPP only used to keep track of attendance and activity, not used to bid on items""")
    

@client.command()
@dkp_only()
async def dinoreq(ctx):
    """Displays the Dino requirements"""
    await ctx.send("""Dino Requirements:
                   
To start Dino will require every class to have Dino Ready gear + Skills to participate for points. Dino Requirement: MUST BE LEVEL 220 FOR ANY POINTS.
Dino Requirement Update:

All Dino’s starting from December 22nd 2021 will now require every class to have Dino Ready gear + Skills to participate for points and raid. You will also be required to know Dino mechanics. IF you have no idea what this boss does but reach all requirements you will still not be eligible for points.""")
    
@client.command()
@dkp_only()
async def dinoclassreq(ctx, cclass):
    """Displays the Dino class requirements"""
    cclass = cclass.lower()
    if cclass == "warrior":
        await ctx.send("""Warrior Requirements:
Warriors:
        - Tanks: - Ability to time Dino Heal - 42 Skill Points in bash.
              -MT STATS - MINIMUM OF 28k HP and 13k DEFENSE with SOME DIRECT TAUNT GEAR (more is always better)
                (This can be a Mord/Dino Taunt brace, Taunting bloom ring or BT bands)
              -Add tanks stats - MINIMUN OF 17K HP and 7k defense. 
        - DPS Warriors - Gelebron Axe (or Dino wep) - Hexforged Axe of Might (400 DAMAGE OFFHAND) - 42 Skill points in Bash - Ability to time Dino Heal
*Changes* Last Requirement made it so DPS warriors needed to have full dg but they are now able to participate in raids. DPS Warriors will now have to have 42 points in bash and bash dino. 
**IN THE EVENT THAT WE ARE MISSING PLAYERS AND NEED A PLAYER TO FULLFILL THE ROLES BUT THEY DON” T REACH REQUIREMENTS, LEADERS MAY DEEM IT APPROPIATE FOR THEM TO JOIN DINO AND THEY WILL BE ABLE TO EARN POINTS DURNG THAT SPECIFIC DINO**""")
    if cclass == "ranger":
        await ctx.send("""Ranger Requirements:
Rangers: Magic Quiver - Gelebron Bow (Or Dino) - Entangle at 42 Skill Points 
*Changes* Last Requirement made it so Rangers needed DG gloves, this will not be needed but Rangers will always be the first one to ask to leave the raid if People are starting to get teleported unless a DPS rogue is in raid.""")
    if cclass == "rogue":
        await ctx.send("""Rogue Requirements:
Rogues: 
      - Support Rogue: 50 Points in Expose Weakness and Smokebomb. 
      -DPS Rogue: - Gelebron Dagger (or Dino) - Hexforged Axe of Might (400 MAGIC DAMAGE OFFHAND)
*Changes* Last Requirement made it so rogues needed to have full DG to participate, but now they’re able to participate as long as they meet requirements. DPS rogues will be the first to leave the raid if players are being teleported.""")
    if cclass == "druid":
        await ctx.send("""Druid Requirements:
Druids: 
        - DPS DRUIDS: 30+ Points in magic Ward - BT or Dino Amulet - BT DPS Charm. NOT REQUIRED BUT SUGGESTED: Spring of Life 
        - Support Druid: Minimun of 5.5k heal - Howling winds - Magic Ward - 25% Natures touch recast 
        *Changes* Last Requirement made it so DPS druids needed 50 magic ward which has been changed to a minimum of 30 points. Rooting druids Removed. Also Support druids will now be required to have a 5.5k heal and Natures touch recast.""")
    if cclass == "mage":
        await ctx.send("""Mage Requirements:
Mages: Bloodthorn or Dino Amulet - Bloodthorn Charm - 42 Points in freeze - Ability to time bash
       - Freezers for Troll: 42 points in freeze with a recast freeze skull. 
*Mages will now be required to Time dino heal, and added a sub category for troll freezing where they are required to have a freeze skull to freeze.""")
    

@client.command()
@dkp_only()
async def dinoweps(ctx):
    await ctx.send("""Dino Weapons:
*Dino Weapon Rule Change Rev. 3.0*
 
⭐️ -You may own a total of two (2) Dino weapons across ALL toons. The second weapon must be won for base DPKP price. If you had already won a Dino weapon for above base, and are interested in a new weapon, you must state you will be refunding your current weapon if won on the bidding note, and are allowed to bid above base. If you had won, you must refund your current weapon to receive your new one.
⭐️-  The weapons must be for different toons of different class, you are not able to win 2 weapons for the same toon.
⭐️ -The following bidding restrictions still apply to bid on any tier Dino weapons:
  ~15% RBPP in the past 30 days
  ~3 Dino, 2 Prot, 2 Bloodthorn, 2 Gele attends in the past 30 days.
⭐️- You must own a T10 CG on the toon that will be winning the Dino weapon.

🗡Daggers:
- if you win a Dino dagger, you must refund your Gele dagger(s) and can’t win future Gele dags""")
    
@client.command()
@dkp_only()
async def leadership(ctx):
    """Displays the current leadership"""
    await ctx.send("""07/05/2024 - Leadership

Generals:
Ambie/Sylv (Keni):
Discord ID: @keniwin
Darkhealz:
Discord ID: @darkhealz.
Ayhano (Shicu): 
Discord ID: @shicu_
Unreal:
Discord ID: @unrealmatty 

Guardians:

hubott:
Discord ID: @hubott
Abomination:
Discord ID: @valhallaxx
Aspire:
Discord ID: steller._.
M0neyBank
Discord ID: @moneydeez1
Bones:
Discord ID: @zealous_otter_24291
Swag:
Discord ID: @elijah040404
REDALiCE:
Discord ID: @yukarip3
                   
Bot Creator and Admin:
REDALiCE:
Discord ID: @yukarip3""")
                   

@client.command()
@dkp_only()
async def itemlimit(ctx):
    """Displays the current item limits"""
    await ctx.send("""Item Limitations:
Bloodthorn Helmet- A person can only have one Bloodthorn helmet per person amongst all of their accounts obtained from clan bank or outside clan.
Bloodthorn Recast Rings. Only one recast ring of each skill per character.
Bloodthorn Charms and Necklaces. Only one charm or necklace of each type per character. (Each class has two different types of necks and charms, each character may have both types.)
Bloodthorn Bands:It’s now Alt toons of a different class are allowed 3 bloodleaf bands (Royal/Imperial) Imperial BT bands have main priority if bid on above 2500 GKP. If a Main does not bid above 2500 GKP, an alt may bid and win for above 2500 GKP.
You are only able to earn bands on 3 toons. With main toons able to win up to 4 bands and alts toons winning a maximum of 3 bands. 
Main change: if your main currently has 4 bands and you change your main to another account one band is required to be refunded""")

@client.command()
@dkp_only()
async def multibidding(ctx):
    """Displays the rules for bidding on multiple items"""
    await ctx.send("""When bidding on items where there are multiple of the specific item available a note will be created and bidding will occurs for these items though a single note.This applies for AKP/PKP/GKP/DPKP  (Closed) Bidding. In the comments of the note state how many of the item you are interested in then send your bids ingame to "mcbidders" stating Bid #1 and Bid#2 on the same mail with the subject as the item name (since you are not able to win more than 2 items per KP above base per week).
common misconceptions are that you are able to select and bid on Item #1, Item #2, Item #3, etc… which is incorrect, you are placing one or two separate bids against all items available, the top X (amount of items available) bids win the items.""")
    

@client.command()
@dkp_only()
async def altbidding(ctx):
    """Displays the rules for bidding on items for alts"""
    await ctx.send("""Alt Bidding:
The term “Alt Bidding” means using points from your main toon to bid for gear for one of your Alternate toons. This may ONLY be done for OPEN BIDDING items (DKP)
Any bidding that is made using a toons OWN earned points (Alt or Main) takes priority over “Alt bidding”
-For example, anyone may create a note for a DKP item, the bottom would read, Bidder: (main toon) Alt bidding for (alt toon). If won points would be deducted from the main toon, and item would be won by the alt toon.
What if someone else is interested in the same item that I had bid on using “alt bid”? if the other person interested had done an “Alt Bid” you may continue to “Alt bid” back and forth until the bidding is over.
If the other person interested places a bid using a toons OWN points (alt or main) this will cancel ALL previously made “Alt bids” made from all who had bid using this method.""")

@client.command()
@dkp_only()
async def minimumbids(ctx):
    """Displays the minimum bids for each item type"""
    await ctx.send("""Minimum Bids:""")
    await ctx.send("https://imgur.com/WDQUBaW")

@client.command()
@dkp_only()
async def bidtemplate(ctx):
    """Displays the bidding template"""
    await ctx.send("""Bidding Template:
Copy and paste the correct template for the item you are bidding on. Replace text in (brackets).""")
    await ctx.send("""⭐️ DKP bidding ⭐️: (Mordris, Necro, Hrung, Crowns, Legacy)
This item is being purchased for (insert cost of item) (insert KP type) minimum bid. If interested please comment below with your bid amount and name of toon whose points are being bid with in the next 12 hours. Each bid you place must include the name of the toon whose points are being used, and @tag every other player who bidded above to be valid. Bidding will take place over the next 13 hours.Only your last bid submission within the 13 hours will be used.Bidder: (insert your character's name)""")
    await ctx.send("""⭐️ AKP, GKP, DPKP ⭐️:
(Gelebron, Bloodthorn, Dhiothu)

This item is being purchased for (insert cost of item) (insert KP type) minimum bid. If you are also interested in this item, post interested below using the character name that will be bidding.  
Mail in your bid to McBidders with your name and the name of the item you are bidding on within the next 13 hours.  
Bidder: (insert your character name)""")

@client.command()
@dkp_only()
async def refundsinfo(ctx):
    """Displays the refund policy"""
    await ctx.send("""*rule clarification*

Current refund rule states:
*   Refunding: Raid drops that you have received from the clan may be refunded for 100% of the cost you paid. You may only refund an item after having it for more than 2 weeks.
*   DKP items will be capped at 15,000 points when you refund them.
*   You may only refund 4 items per category every 30 days. DKP items are excluded from this limit.
*   You may not bid on the same item you have refunded in the past 2 weeks.

Instead changing the refunding rule, we want to provide some new clarity in the way that we process refunds.
In the past, as some leaders refunded items based on the smallest KP, other leaders had been refunding chronologically. Refunding based on KP amount has worked well in avoiding loopholes, but we also feel that it isn’t fair as players continue to lose KP. Because we, as leaders, have been unknowingly refunding items in different ways, we have taken the last couple of months to look at how to better clarify the refunding process.
It has been agreed upon that in the future, all refunds will be processed chronologically. This means that whatever item you won first, that KP will be returned to you. But won’t this result in another loophole? No; since we can compare items received to item adjustments, we are able to assure that no one is able to duplicate points.
Because Dino refunds are the hardest to track, we will refund the chronological sum that was spent, unless you won that specific tier through bidding. 
Example: If you built your own imperial brace, but also won an imperial brace, we will refund the points spent on the one that you did not build.""")
    

@client.command()
@dkp_only()
async def halfpoints(ctx):
    """Displays the half points policy"""
    await ctx.send("""Are you multi-loging at raids? If you log two accounts for raids you will be able to receive full points for both accounts! If you are capable and decide to log a 3rd account one if those accounts will get half points and the other two will get full points!
Bonus: on resets you can get half points for a 4th account!""")
    
@client.command()
@dkp_only()
async def mainprio(ctx):
    """Displays the main priority information"""
    await ctx.send("""Main Priority gives those with a main toon of the desired drop to have priority over inactive/alternate toons.
Items that have Main Priority are as follows:
   - Godly Gelebron Jewelry
   - Void Gelebron Weapons
   - Godly Bloodthorn Jewely
   - Imperial/Godly Dino Jewelry
   - All Dino Weapons
   - Godly Dex/Vit Prot Braces
Main priority will now be split into two sections. End game and Mid Game. 
End Game Priority Raids: This category now includes PROT, GELE, BT, and DINO. To achieve main priority for these bosses, you must participate in at least 4 of each raid within the last 45 days.
Mid Game Priority Raids: This encompasses UNOX, HRUNG, MORD, and NECRO. This means that Toons who participate in 4 Mord, 4 Hrung, and 4 Necro raids within the last 45 days will receive priority on certain items over those who do not attend these raids
Specific Requirements for BT Helms and Dino Weapons:
The requirements for BT Helms and Dino Weapons have been adjusted to align with the End Game Priority Raids. Additionally, a minimum RBPP of 250 is now necessary to bid on these items.""")

@client.command()
@dkp_only()
async def questupgrades(ctx):
    """Displays the quest upgrade information"""
    await ctx.send("""Warden, Meteoric, Frozen, DL armor are available upon request. Weapons for Warden, Meteoric, and Frozen are also provided, these are available to Recruits upon request from clan Guardians.
DL weapons (crowns) need to be obtained by calling and rolling at snorri, or purchased from bank for 50 DKP each. Snorri is typically announced in Green 🟢 chat. Keep track of this timer in boss dead chat. All crowns are banked except if called for at Snorri. You must have an eligible toon of the class you call to be awarded the crown(s)
EDL Armor is available to Clansman upon reaching 205, request this with a clan General.
Due to the changes in main priority raids and the introduction of mid-game priority raids, the requirement for EDL Offhand has been modified. To qualify, you must now have attended Unox raids with a minimum RBPP of 15%, along with participation in 4 Hrung, 4 Mord, and 4 Necro within the past 45 days.
Doch upgrades, when the clan acquires 15 pures in bank, a poll will be created in the “Doch Voters” chat. This chat consists of all leaders, and all clannies who have full doch sets. It is the persons preference who they vote for while following the limited number of pures we have available, although most base their votes off attends (RBPP and AKP)
First Toon (Set 1): 15% RBPP attendance required, 1 poll cooldown. Hat farmed from VoA or BT helm won.
Gloves ——-> 100 TOTAL RBPP
Top————>200 TOTAL RBPP
Boots———> 250 TOTAL RBPP
Legs———-> 350 TOTAL RBPP
Second Toon (Set 2): 500 RBPP to start, 25% RBPP attendance in last 30 days, 2 poll cooldown. Hat farmed from VoA or BT helm won.
Third+ Toons (Set 3+): 1000 RBPP to start, 25% RBPP attendance in last 30 days, 3 poll cooldown. Must finish previous toon's set first.
BT Helm: 3 pures allocated (gloves+boots). Farm chest and legs from VoA.
No BT Helm: 5 pures allocated (gloves+legs). Farm helm, chest, and boots from VoA.
Exception to Doch voting, when leaders seem fit and all leaders agree, there is a possibility of a expedited use of pures to upgrade a certain toon(s) or to complete a set. Although this is rare, leaders may do this at a desperate time to benefit the clan. This action will count as a poll during a previously awarded persons poll waiting period.
Echos and Seeds, weeklies are scheduled by leaders at a clannies request, reach out to any guardian to schedule a weekly to get 7 echos to upgrade your EDL OH to T8, reminder weeklies award GKP so help out your fellow clannies. Once you reach a T8 OH reach out to a General to receive 2 Bloodthorn seeds, to upgrade your offhand to T10.""")


@client.command()
@dkp_only()
async def esttime(ctx):
    """Displays the EST time"""
    await ctx.send("""Curious on the current EST time? Click this link to find out : https://time.is/ET/
A lot of the clan is US based and EST is the most common timezone used to time raids and events.
If you are using the discord timer bot, the time is automatically converted to your local timezone""")

@client.command()
@dkp_only()
async def spawntimes(ctx):
    """Displays the spawn times for various bosses"""
    await ctx.send("type \"refresh\" in #dead-timers to get the latest spawn times")

@client.command()
@dkp_only()
async def spreadsheet(ctx):
    """Links Winston's master point spreadsheet"""
    await ctx.send("https://docs.google.com/spreadsheets/d/1Izu2wSmi0aEQCWTvfLAXX0ucXR2223ILzFxTiQXcl80/edit#gid=393681553")

@client.command()
@dkp_only()
async def oldwins(ctx):
    """Links Alice's old wins spreadsheet"""
    await ctx.send("https://docs.google.com/spreadsheets/d/1FbfNkF9SkD0A8a61ChoKvcG88yC2vpaHL8ffm37TSb8/edit?gid=1217357805#gid=1217357805")

@client.command(aliases=["oldloot"])
@dkp_only()
async def oldwinnings(ctx, name, kp = None):
    """Displays a player's old loot winnings from Alice's spreadsheet"""
    if kp != None:
        kp = kp.upper()
    all_rows = await bot4ws14.aget_all_values()
    char_names = [row[2] for row in all_rows if len(row) >= 5 and row[2] != ""]
    realname, caps, spaces, suggestions = find_name(name, char_names)
    if realname == None:
        await ctx.send(not_found_message(name, suggestions))
        return
    # check if character exists in the current system
    current_players = await bot4ws9.acol_values(1)
    in_current = any(realname.lower() == p.lower() for p in current_players)
    warning = "" if in_current else " (not in current system)"
    # collect matching rows
    matches = []
    for row in all_rows:
        if len(row) >= 5 and row[2].lower() == realname.lower():
            date, pool, charname, item, price = row[0], row[1], row[2], row[3], row[4]
            if kp == None or kp in pool.upper():
                matches.append((date, pool, item, price))
    if len(matches) == 0:
        if kp == None:
            await ctx.send(realname + warning + " has no old loot winnings")
        else:
            await ctx.send(realname + warning + " has no old loot winnings for " + kp)
        return
    pagecounter = 0
    for i in range(len(matches)):
        if i % 20 == 0:
            if i != 0:
                await ctx.send(embed=embed)
            pagecounter += 1
            title = realname + "'s Old Winnings"
            if kp != None:
                title += " (" + kp + ")"
            title += " Page " + str(pagecounter) + warning
            embed = discord.Embed(title=title, colour=discord.Color.orange())
        date, pool, item, price = matches[i]
        embed.add_field(name=str(i + 1) + ". " + item, value=price + " " + pool + " (" + date + ")", inline=False)
    await ctx.send(embed=embed)

@client.command()
@dkp_only()
async def kpsite(ctx):
    """Links the KP site"""
    await ctx.send("http://www.relentless.dkpsystem.com/news.php")


@client.command()
@dkp_only()
async def information(ctx):
    """Displays the information dump commands"""
    await ctx.send("""to get started, type one of these commands:
                   
$information - displays this message
$new - new player induction messages
$clanrules - links the clan rules
$spreadsheet - links Winston's master point spreadsheet
$kpinfo - displays information about the various KP pools
$dinoreq - displays the requirements for Dino
$dinoclassreq - displays the requirements for Dino by class. make sure to add the class after the command
$dinoweps - displays the requirements to get weapons from Dino
$leadership - displays the current leadership
$itemlimit - displays current limitations on items
$multibidding - displays the rules for bidding on multiple items
$altbidding - displays the rules for bidding on items for alts
$minimumbids - displays the minimum bids for each item type
$bidtemplate - displays the bidding template
$refundsinfo - displays the refund policy
$halfpoints - displays the half points policy
$mainprio - displays information about main priority
$questupgrades - displays information about acquiring various quest items
$esttime - displays info about EST time
$spawntimes - tells you where to find the spawn times
$kpsite - links the KP site
$lbhelp - boss leaderboard commands (also available in other servers)""")
    
@client.command()
@dkp_only()
async def ban(ctx, name):
    """Bans a player"""
    await ctx.send(name + " has been banned")

@client.command()
@dkp_only()
async def kick(ctx, name):
    """Kicks a player"""
    await ctx.send(name + " has been kicked")

@client.command()
@dkp_only()
async def demote(ctx, name):
    """Demotes a player"""
    await ctx.send(name + " has been demoted")

@client.command()
@dkp_only()
async def promote(ctx, name):
    """Promotes a player"""
    await ctx.send(name + " has been promoted")

@client.command()
@dkp_only()
async def sudo(ctx):
    """pretends to break"""
    await ctx.send("Logging in as Super Admin")
    await ctx.send("Executing...")
    # wait a second
    async with ctx.typing():
        await asyncio.sleep(5)
        await ctx.send("Error: you're a silly goose")

@client.command()
@dkp_only()
async def unban(ctx, name):
    """Unbans a player"""
    await ctx.send(name + " has been unbanned")

@client.command()
@dkp_only()
async def delete(ctx, *args):
    """Deletes something"""
    await ctx.send("Deleting " + " ".join(args))

@client.command()
async def source(ctx):
    """posts the link for the source code (available everywhere, no gate)"""
    await ctx.send("https://github.com/Haylia/Gwydion-DKP-bot")

@client.command()
async def donate(ctx):
    """posts the link for donations (available everywhere, no gate)"""
    await ctx.send("https://www.paypal.me/liastarrrr")

@client.command()
@dkp_only()
@commands.has_any_role("General", "REDALiCE")
async def reload(ctx):
    """Force-refresh all worksheet caches (use after manual sheet edits)"""
    count = 0
    for key, instances in _CACHE_REGISTRY.items():
        for cws in instances:
            cws.refresh()
            count += 1
    await ctx.send(f"Marked {count} worksheet caches as stale. They will refresh on next access.")


# ════════════════════════════════════════════════════════════════════════════
# Boss Leaderboard (BossRanking.ashx integration, ported from larry_for_lia.py)
# Auto-fetches Gwydion (World 15) fight data, generates damage-chart PNGs,
# and posts new raids on a UTC-anchored schedule.
# ════════════════════════════════════════════════════════════════════════════

import json
import textwrap
from PIL import ImageDraw, ImageFont  # PIL.Image already imported above

BOSS_CHAR_ID = "123456"
BOSS_RANKING_URL = "https://production.ch.decagames.com/gamestats_global/BossRanking.ashx"

BOSS_NAMES = {
    103028: "Proteus Prime",
    141966: "Bloodthorn the Ravenous",
    102982: "Gelebron",
    103027: "Proteus Base",
    142027: "Dhiothu",
    73708: "Hrungnir",
    73000: "Mordris",
    100002: "Efnisien the Necromancer",
    200490: "Crom's Hellborne Manikin",
}

BOSS_ALIASES = {
    "prime": 103028, "protprime": 103028, "proteusprime": 103028,
    "bt": 141966, "bloodthorn": 141966, "bloodthorntheravenous": 141966,
    "gele": 102982, "gelebron": 102982,
    "base": 103027, "protbase": 103027, "proteusbase": 103027,
    "dino": 142027, "dhiothu": 142027, "dhio": 142027,
    "hrung": 73708, "hrungnir": 73708,
    "mord": 73000, "mordris": 73000,
    "necro": 100002, "efnisien": 100002, "necromancer": 100002,
    "efnisienthenecromancer": 100002,
    "crom": 200490, "hellborne": 200490, "manikin": 200490,
    "cromhellborne": 200490, "cromshellborne": 200490,
    "cromhellbornemanikin": 200490, "cromshellbornemanikin": 200490, "mani": 200490,
}

CONFIRMED_BOSS_IDS = set(BOSS_NAMES.keys())

_BOSS_DIR = os.path.dirname(os.path.abspath(__file__))
POSTED_FIGHTS_FILE = os.path.join(_BOSS_DIR, "posted_fights.json")
RAID_HISTORY_FILE = os.path.join(_BOSS_DIR, "raid_history.json")

# ─── Multi-server config ──────────────────────────────────────────────────
# The bot was originally Gwydion-only. These constants encode the canonical
# Gwydion defaults; every other server provides its own values via
# server_config.json (see load_server_config / set_server_entry below).
# (GWYDION_GUILD_IDS and is_gwydion_guild are defined much earlier in the file
# because they're needed by @dkp_only at import time.)
GWYDION_WORLD_ID = 15
GWYDION_AUTO_POST_CHANNEL_ID = 1232432110699282493
SERVER_CONFIG_FILE = os.path.join(_BOSS_DIR, "server_config.json")
SERVER_CONFIG_VERSION = 1

# Celtic Heroes world name → world_id. Matched case-insensitively, ignoring
# spaces/apostrophes (so "Crom's" and "crom" both work). Used by $setworld so
# admins can type a name instead of an ID.
# Source: https://production.ch.decagames.com/patchserver/worldlist.aspx
CH_WORLDS = {
    "arawn":     7,
    "crom":      8,
    "danu":      9,
    "morrigan":  10,
    "mabon":     11,
    "sulis":     12,
    "epona":     13,
    "rosmerta":  14,
    "gwydion":   15,
    "fingal":    53,
    "nuada":     56,
    "tethra":    101,
    "rigantona": 102,
    "llyr":      103,
    "belenor":   104,
}

# UTC-anchored fire times. Bot is hosted on non-local servers, so this
# MUST be UTC (== GMT) — not local time.
# Schedule: 00:30 / 04:30 / 08:30 / 12:30 / 16:30 / 20:30 UTC
BOSS_POLL_ANCHOR_TIMES = [
    dtime(0,  30, tzinfo=timezone.utc),
    dtime(4,  30, tzinfo=timezone.utc),
    dtime(8,  30, tzinfo=timezone.utc),
    dtime(12, 30, tzinfo=timezone.utc),
    dtime(16, 30, tzinfo=timezone.utc),
    dtime(20, 30, tzinfo=timezone.utc),
]

# Date ranges to exclude from all fight queries, stats, and auto-posts.
# Inclusive on both ends. Edit this list to change which days are dropped.
BOSS_EXCLUDED_DATE_RANGES = [
    ("2025-09-01", "2025-10-31"),
    ("2026-02-09", "2026-02-12"),
]

# Candidate directories for the chscripts boss ranking traverser output.
# The loader picks the first one that actually exists at query time, so the
# same code works on the local dev box (absolute Windows path) and on the
# remote host (where the folder sits next to the bot script). Add more paths
# here if you deploy to other locations.
BOSS_TRAVERSER_DATA_DIRS = (
    os.path.join(_BOSS_DIR, "bossranking_data"),
    r"D:\CH Projects\chscripts\bossranking_data",
)
BOSS_TRAVERSER_CACHE_TTL = 300  # seconds; the traverser is still running so re-scan periodically

_BOSS_EXCLUDED_DATE_RANGES_PARSED = []
for _start, _end in BOSS_EXCLUDED_DATE_RANGES:
    try:
        _BOSS_EXCLUDED_DATE_RANGES_PARSED.append((
            dt.strptime(_start, "%Y-%m-%d").date(),
            dt.strptime(_end, "%Y-%m-%d").date(),
        ))
    except Exception:
        pass


# ─── World-name helpers ───────────────────────────────────────────────────

def normalize_world_name(s):
    """Lowercases and strips non-alphanumeric chars so 'Crom's' and 'crom' both match."""
    if not s:
        return ""
    return "".join(c for c in str(s).lower() if c.isalnum())


def resolve_world(token):
    """Accepts an int-as-string OR a Celtic Heroes world name (e.g. 'gwydion').
    Returns (world_id, canonical_name_or_None) or (None, None) on failure.
    canonical_name is the CH_WORLDS key when matched by name; None for raw ints
    (the caller can render `f"World {world_id}"` instead)."""
    if token is None:
        return None, None
    raw = str(token).strip()
    if not raw:
        return None, None
    if raw.lstrip("-").isdigit():
        try:
            return int(raw), None
        except Exception:
            return None, None
    key = normalize_world_name(raw)
    if key in CH_WORLDS:
        return CH_WORLDS[key], key
    return None, None


def display_world(world_id):
    """Returns the canonical CH_WORLDS name (capitalised) if known, else 'World {id}'.
    Used for chart titles, embed headers, and confirmation messages."""
    try:
        wid = int(world_id)
    except Exception:
        return f"World {world_id}"
    for name, mapped_id in CH_WORLDS.items():
        if mapped_id == wid:
            return name.capitalize()
    return f"World {wid}"


# ─── server_config.json I/O ───────────────────────────────────────────────
# Per-Discord-guild configuration: which CH world the guild tracks, where to
# auto-post boss kills, and an optional setup role. Stored as a JSON dict
# keyed by Discord guild_id (as a string). The "_meta" key holds schema metadata
# and is never treated as a guild entry by the lookup helpers.

def load_server_config():
    """Returns the full server_config.json contents, or a freshly seeded dict if
    the file doesn't exist or is unreadable. Always contains a '_meta' key."""
    default = {"_meta": {"version": SERVER_CONFIG_VERSION}}
    if not os.path.exists(SERVER_CONFIG_FILE):
        return default
    try:
        with open(SERVER_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        data.setdefault("_meta", {"version": SERVER_CONFIG_VERSION})
        return data
    except Exception:
        logger.exception("Could not read server_config.json; using defaults")
        return default


def save_server_config(cfg):
    """Atomic write (tmp file + os.replace). Mirrors save_posted_fights."""
    if not isinstance(cfg, dict):
        raise ValueError("server config must be a dict")
    cfg.setdefault("_meta", {"version": SERVER_CONFIG_VERSION})
    tmp = SERVER_CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, SERVER_CONFIG_FILE)


def get_server_entry(guild_id):
    """Returns the per-guild config entry, or None if not configured. Ignores '_meta'."""
    if guild_id is None:
        return None
    cfg = load_server_config()
    return cfg.get(str(int(guild_id)))


def set_server_entry(guild_id, *, world_id=None, channel_id=None, setup_role=None):
    """Upserts a guild's entry. None args preserve existing values. Stamps
    added_at on first creation. Returns the merged entry."""
    if guild_id is None:
        raise ValueError("guild_id is required")
    cfg = load_server_config()
    key = str(int(guild_id))
    entry = dict(cfg.get(key) or {})
    is_new = not entry
    if world_id is not None:
        entry["world_id"] = int(world_id)
    if channel_id is not None:
        entry["channel_id"] = int(channel_id) if channel_id else None
    if setup_role is not None:
        # Empty string clears the role
        entry["setup_role"] = setup_role if setup_role else None
    if is_new:
        entry["added_at"] = dt.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cfg[key] = entry
    save_server_config(cfg)
    return entry


def remove_server_entry(guild_id):
    """Deletes a guild's entry. Returns True if it existed."""
    if guild_id is None:
        return False
    cfg = load_server_config()
    key = str(int(guild_id))
    if key in cfg:
        del cfg[key]
        save_server_config(cfg)
        return True
    return False


def get_world_id_for_guild(guild_id):
    """Returns the configured world_id for guild_id, or None if unset."""
    entry = get_server_entry(guild_id)
    if not entry:
        return None
    wid = entry.get("world_id")
    return int(wid) if wid is not None else None


def get_channel_id_for_guild(guild_id):
    """Returns the configured auto-post channel_id, or None if unset."""
    entry = get_server_entry(guild_id)
    if not entry:
        return None
    cid = entry.get("channel_id")
    return int(cid) if cid else None


def get_all_configured_guilds():
    """Returns [(guild_id, entry), ...] for every guild with a valid world_id.
    Used by the auto-poller to iterate every server that should be checked."""
    cfg = load_server_config()
    out = []
    for key, entry in cfg.items():
        if key == "_meta" or not isinstance(entry, dict):
            continue
        try:
            gid = int(key)
        except Exception:
            continue
        if entry.get("world_id"):
            out.append((gid, entry))
    return out


def _boss_parse_kill_date(date_text):
    raw = str(date_text).strip()
    if not raw:
        return None
    raw = raw.split("T")[0].split(" ")[0]
    try:
        return dt.strptime(raw, "%Y-%m-%d").date()
    except Exception:
        return None


def _boss_is_excluded_date(date_text):
    d = _boss_parse_kill_date(date_text)
    if not d:
        return False
    return any(start <= d <= end for start, end in _BOSS_EXCLUDED_DATE_RANGES_PARSED)


_BOSS_WINDOW_RE = re.compile(r"^(all|\d+[dwmy])$", re.IGNORECASE)


def _boss_parse_window(token):
    """Parses '7d', '4w', '6m', '1y', 'all'. Returns a timedelta or None (no filter).
    Months are 30 days, years are 365 days (approximations)."""
    if not token:
        return None
    t = token.lower()
    if t == "all":
        return None
    m = _BOSS_WINDOW_RE.match(t)
    if not m:
        return None
    n = int(t[:-1])
    unit = t[-1]
    if unit == "d":
        return timedelta(days=n)
    if unit == "w":
        return timedelta(weeks=n)
    if unit == "m":
        return timedelta(days=n * 30)
    if unit == "y":
        return timedelta(days=n * 365)
    return None


def _boss_extract_window(args):
    """Pulls a window token from the start or end of args. Returns (token, remainder)."""
    parts = args.strip().split()
    if not parts:
        return None, ""
    if _BOSS_WINDOW_RE.match(parts[0]):
        return parts[0].lower(), " ".join(parts[1:])
    if len(parts) > 1 and _BOSS_WINDOW_RE.match(parts[-1]):
        return parts[-1].lower(), " ".join(parts[:-1])
    return None, args.strip()


def boss_normalize_name(name):
    s = str(name).strip().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def boss_display_name(boss_id):
    try:
        boss_id = int(boss_id)
    except Exception:
        boss_id = 0
    return BOSS_NAMES.get(boss_id, f"BossId {boss_id}")


def parse_boss_input(boss_text):
    key = boss_normalize_name(boss_text)
    if key in BOSS_ALIASES:
        return BOSS_ALIASES[key]
    try:
        return int(boss_text)
    except (ValueError, TypeError):
        return None


# ─── Multi-server gating helpers ──────────────────────────────────────────

def _member_has_role_named(member, role_name):
    """Case-insensitive role-name check that survives missing attrs."""
    if member is None or not role_name:
        return False
    target = str(role_name).lower().strip()
    try:
        for r in getattr(member, "roles", []) or []:
            if str(getattr(r, "name", "")).lower() == target:
                return True
    except Exception:
        pass
    return False


def is_server_setup_authorized(member, entry):
    """True if `member` may run setup / admin commands for their guild.
    Authorized if ANY of:
      - member has Discord administrator permission
      - member has a role named 'Winston Admin' (case-insensitive)
      - member has a role named 'REDALiCE' (case-insensitive)
      - entry has setup_role set AND member has that role
    """
    if member is None:
        return False
    try:
        if getattr(member.guild_permissions, "administrator", False):
            return True
    except Exception:
        pass
    if _member_has_role_named(member, "Winston Admin"):
        return True
    if _member_has_role_named(member, "REDALiCE"):
        return True
    if entry and entry.get("setup_role"):
        if _member_has_role_named(member, entry["setup_role"]):
            return True
    return False


async def _require_world_for_ctx(ctx):
    """Resolves the Celtic Heroes world_id for the guild running this command,
    or sends an error message and returns None.

    - DMs are rejected.
    - Gwydion guilds always resolve to GWYDION_WORLD_ID (no config required).
    - Other guilds need a server_config.json entry; if missing, the user is
      prompted to run $setworld."""
    guild = getattr(ctx, "guild", None)
    if guild is None:
        await ctx.send("This command can't be used in DMs.")
        return None
    gid = guild.id
    if is_gwydion_guild(gid):
        return GWYDION_WORLD_ID
    wid = get_world_id_for_guild(gid)
    if wid is None:
        await ctx.send(
            "This server hasn't been configured for the boss leaderboard yet. "
            "An admin needs to run `$setworld <world_id_or_name>` first "
            "(e.g. `$setworld gwydion` or `$setworld 15`). "
            "Try `$lbhelp` for the full list of leaderboard commands, or "
            "`$listworlds` for known world names."
        )
        return None
    return wid


# ─── BossRanking API ──────────────────────────────────────────────────────

def boss_get_fight_data(fight_id, world_id=None):
    if world_id is None:
        world_id = GWYDION_WORLD_ID
    url = (
        f"{BOSS_RANKING_URL}?board=fight"
        f"&fightid={fight_id}"
        f"&worldid={int(world_id)}"
        f"&playerWorldId={int(world_id)}"
        f"&charId={BOSS_CHAR_ID}"
        "&sortCol=1&sortDir=0&page=1&numRecs=1"
    )
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    return resp.json()


def boss_get_detailed_fights(num_recs=500, page=1, exclude_dates=True, world_id=None):
    """Fetches detailed fight list filtered to `world_id` (default: Gwydion).
    By default drops fights whose DateOfKill falls inside any
    BOSS_EXCLUDED_DATE_RANGES entry. Pass exclude_dates=False to bypass the
    filter (used when looking up a specific FightId regardless of date)."""
    if world_id is None:
        world_id = GWYDION_WORLD_ID
    wid = int(world_id)
    url = (
        f"{BOSS_RANKING_URL}?board=detailed"
        f"&playerWorldId={wid}"
        f"&charId={BOSS_CHAR_ID}"
        f"&sortCol=1&sortDir=0&page={page}&numRecs={num_recs}"
    )
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    data = resp.json()
    fights = data.get("Data", []) if isinstance(data, dict) else data
    fights = [f for f in fights if int(f.get("WorldId", 0)) == wid]
    if exclude_dates:
        fights = [f for f in fights if not _boss_is_excluded_date(f.get("DateOfKill", ""))]
    return fights


def boss_get_latest_fight_id(world_id=None):
    fights = boss_get_detailed_fights(num_recs=500, page=1, world_id=world_id)
    if not fights:
        return None
    newest = max(fights, key=lambda f: int(f.get("FightId", 0)))
    return int(newest.get("FightId"))


def boss_get_latest_boss_fight_id(boss_text, world_id=None):
    boss_id = parse_boss_input(boss_text)
    if not boss_id:
        return None, None
    fights = boss_get_detailed_fights(num_recs=500, page=1, world_id=world_id)
    boss_fights = [f for f in fights if int(f.get("BossId", 0)) == boss_id]
    if not boss_fights:
        return boss_id, None
    newest = max(boss_fights, key=lambda f: int(f.get("FightId", 0)))
    return boss_id, int(newest.get("FightId"))


# ─── State persistence ────────────────────────────────────────────────────
# Schema v1: flat list/dict, world 15 implicit.
# Schema v2: world-keyed dict with a "_meta" key.
#   posted_fights.json: {"_meta": {"version": 2}, "15": [fid, ...], "27": [...]}
#   raid_history.json:  {"_meta": {"version": 2}, "15": {fid_str: rec, ...}, ...}
# _migrate_state_files_if_needed() runs on boot and wraps any old-format file
# under key "15" (GWYDION_WORLD_ID). Idempotent.

STATE_FILE_VERSION = 2


def _migrate_state_files_if_needed():
    """One-time migration from flat (v1) to world-keyed (v2) state files.
    Detects the old schema by absence of '_meta'. Creates a
    `.pre_migration_backup` next to each migrated file. Safe to call on every boot."""

    # ---- posted_fights.json ----
    if os.path.exists(POSTED_FIGHTS_FILE):
        try:
            with open(POSTED_FIGHTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = None
        if isinstance(data, list):
            # Old format: flat list of ints. Wrap under "15".
            try:
                with open(POSTED_FIGHTS_FILE + ".pre_migration_backup", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                logger.exception("Could not write posted_fights.json backup")
            new_data = {
                "_meta": {"version": STATE_FILE_VERSION},
                str(GWYDION_WORLD_ID): sorted(int(x) for x in data),
            }
            tmp = POSTED_FIGHTS_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2)
            os.replace(tmp, POSTED_FIGHTS_FILE)
            logger.info(
                f"Migrated posted_fights.json ({len(data)} fights → world {GWYDION_WORLD_ID})"
            )

    # ---- raid_history.json ----
    if os.path.exists(RAID_HISTORY_FILE):
        try:
            with open(RAID_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = None
        if isinstance(data, dict) and "_meta" not in data:
            # Old format: flat dict of {fight_id_str: record}. Records have FightId.
            looks_old = any(
                isinstance(v, dict) and "FightId" in v for v in data.values()
            ) if data else False
            if looks_old:
                try:
                    with open(RAID_HISTORY_FILE + ".pre_migration_backup", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                except Exception:
                    logger.exception("Could not write raid_history.json backup")
                new_data = {
                    "_meta": {"version": STATE_FILE_VERSION},
                    str(GWYDION_WORLD_ID): data,
                }
                tmp = RAID_HISTORY_FILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2)
                os.replace(tmp, RAID_HISTORY_FILE)
                logger.info(
                    f"Migrated raid_history.json ({len(data)} records → world {GWYDION_WORLD_ID})"
                )


def _world_keys_in_posted_file():
    """Returns the set of world-ID ints present as keys in posted_fights.json
    (excluding '_meta'). Used at boot to know whether seeding is needed."""
    if not os.path.exists(POSTED_FIGHTS_FILE):
        return set()
    try:
        with open(POSTED_FIGHTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return set()
    if not isinstance(data, dict):
        return set()
    keys = set()
    for k in data.keys():
        if k == "_meta":
            continue
        try:
            keys.add(int(k))
        except Exception:
            continue
    return keys


def load_posted_fights(world_id=None):
    """Returns the set of posted fight IDs for `world_id`. Defaults to Gwydion.
    Returns an empty set if the file is missing or the world has no key yet."""
    if world_id is None:
        world_id = GWYDION_WORLD_ID
    if not os.path.exists(POSTED_FIGHTS_FILE):
        return set()
    try:
        with open(POSTED_FIGHTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return set()
    # v2 dict-keyed format
    if isinstance(data, dict):
        return set(int(x) for x in data.get(str(int(world_id)), []))
    # v1 fallback (in case migration didn't run for some reason): only the
    # Gwydion world reads from a flat list.
    if isinstance(data, list) and int(world_id) == GWYDION_WORLD_ID:
        return set(int(x) for x in data)
    return set()


def save_posted_fights(posted, world_id=None):
    """Writes the set of posted fight IDs for `world_id`, preserving other worlds'
    entries. Atomic write."""
    if world_id is None:
        world_id = GWYDION_WORLD_ID
    if os.path.exists(POSTED_FIGHTS_FILE):
        try:
            with open(POSTED_FIGHTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {"_meta": {"version": STATE_FILE_VERSION}}
        except Exception:
            data = {"_meta": {"version": STATE_FILE_VERSION}}
    else:
        data = {"_meta": {"version": STATE_FILE_VERSION}}
    data.setdefault("_meta", {"version": STATE_FILE_VERSION})
    data[str(int(world_id))] = sorted(int(x) for x in posted)
    tmp = POSTED_FIGHTS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, POSTED_FIGHTS_FILE)


def load_raid_history(world_id=None):
    """Returns the dict of {fight_id_str: record} for `world_id`. Defaults to Gwydion."""
    if world_id is None:
        world_id = GWYDION_WORLD_ID
    if not os.path.exists(RAID_HISTORY_FILE):
        return {}
    try:
        with open(RAID_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    if "_meta" in data:
        # v2 world-keyed
        bucket = data.get(str(int(world_id)), {})
        return bucket if isinstance(bucket, dict) else {}
    # v1 fallback: flat dict was Gwydion only.
    if int(world_id) == GWYDION_WORLD_ID:
        return data
    return {}


def save_raid_history(history, world_id=None):
    """Writes the dict for `world_id`, preserving other worlds' entries.
    Atomic write — see save_posted_fights for rationale."""
    if world_id is None:
        world_id = GWYDION_WORLD_ID
    if os.path.exists(RAID_HISTORY_FILE):
        try:
            with open(RAID_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "_meta" not in data:
                # Either v1 flat (which migration should have already converted)
                # or unexpected shape — start a fresh v2 wrapper to be safe.
                data = {"_meta": {"version": STATE_FILE_VERSION}}
        except Exception:
            data = {"_meta": {"version": STATE_FILE_VERSION}}
    else:
        data = {"_meta": {"version": STATE_FILE_VERSION}}
    data.setdefault("_meta", {"version": STATE_FILE_VERSION})
    data[str(int(world_id))] = history
    tmp = RAID_HISTORY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, RAID_HISTORY_FILE)


# ─── Traverser data source (chscripts/bossranking_data) ───────────────────

# Cache keyed by world_id so different worlds don't trash each other's loaded
# history. Each value: {"loaded_at", "file_count", "history", "mismatched"}.
_boss_traverser_cache = {}
# Guards reads/writes of the per-world cache buckets, since
# boss_load_traverser_history runs in worker threads (via sheet_call).
_boss_traverser_lock = threading.Lock()


def _boss_traverser_cache_for(world_id):
    """Returns the (mutable) cache dict for `world_id`, creating it if absent."""
    bucket = _boss_traverser_cache.get(world_id)
    if bucket is None:
        bucket = {"loaded_at": 0.0, "file_count": -1, "history": {}, "mismatched": 0}
        _boss_traverser_cache[world_id] = bucket
    return bucket


def _boss_traverser_paths():
    """Returns (fights_dir, index_path) for the first BOSS_TRAVERSER_DATA_DIRS entry
    that exists on disk, or (None, None) if none do. Re-checks on every call so a
    folder appearing after bot start is picked up automatically."""
    for root in BOSS_TRAVERSER_DATA_DIRS:
        if root and os.path.isdir(root):
            return os.path.join(root, "fights"), os.path.join(root, "fights_index.json")
    return None, None


def _read_json_file(path):
    """Blocking JSON read — call via sheet_call from async code."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _boss_write_json_atomic(fp, data):
    """Blocking atomic JSON write (temp + os.replace) — call via sheet_call."""
    tmp = fp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, fp)


def boss_load_traverser_history(world_id=None, force=False):
    """Reads the chscripts traverser output (fights_index.json + per-fight JSONs)
    and returns {fight_id_str: history_record} for `world_id` (default: Gwydion).
    In-memory cached per-world for BOSS_TRAVERSER_CACHE_TTL seconds; invalidates
    immediately if the on-disk file count changes. Returns {} if the traverser
    directory is missing."""
    if world_id is None:
        world_id = GWYDION_WORLD_ID
    world_id = int(world_id)
    cache = _boss_traverser_cache_for(world_id)
    fights_dir, index_path = _boss_traverser_paths()
    if not fights_dir or not os.path.isdir(fights_dir) or not os.path.exists(index_path):
        return {}
    try:
        current_count = sum(
            1 for f in os.listdir(fights_dir)
            if f.startswith(f"fight_{world_id}_") and f.endswith(".json")
        )
    except Exception:
        current_count = -1
    now = time.time()
    with _boss_traverser_lock:
        stale = (now - cache["loaded_at"]) >= BOSS_TRAVERSER_CACHE_TTL
        changed = current_count != cache["file_count"]
        if not force and not stale and not changed and cache["history"]:
            return cache["history"]
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    except Exception:
        logger.exception("Could not read traverser fights_index.json")
        return cache["history"]
    index_by_id = {}
    for r in index:
        try:
            if int(r.get("WorldId", 0)) == world_id:
                index_by_id[int(r["FightId"])] = r
        except Exception:
            continue
    history = {}
    mismatched = 0
    file_prefix = f"fight_{world_id}_"
    for filename in os.listdir(fights_dir):
        if not filename.startswith(file_prefix) or not filename.endswith(".json"):
            continue
        try:
            fight_id = int(filename[len(file_prefix):-len(".json")])
        except ValueError:
            continue
        idx_row = index_by_id.get(fight_id)
        if not idx_row:
            continue
        try:
            bid = int(idx_row.get("BossId", 0))
        except Exception:
            continue
        if bid not in CONFIRMED_BOSS_IDS:
            continue
        date = idx_row.get("DateOfKill", "")
        if _boss_is_excluded_date(date):
            continue
        try:
            with open(os.path.join(fights_dir, filename), "r", encoding="utf-8") as f:
                detail = json.load(f)
        except Exception:
            continue
        # Per-world validation: BossRanking sometimes ignores worldid for board=fight
        # and returns the wrong world's fight. Index TotalDamage is the authoritative
        # value for THIS (FightId, WorldId) pair — if the cached per-fight file's
        # TotalDamageDone doesn't match, the file is for a different world. Skip it
        # to avoid attributing other servers' damage to Gwydion players.
        try:
            idx_dmg = int(idx_row.get("TotalDamage", 0) or 0)
            pf_dmg = int(detail.get("TotalDamageDone", 0) or 0)
            if idx_dmg > 0 and pf_dmg != idx_dmg:
                mismatched += 1
                continue
        except Exception:
            pass
        players = []
        for p in detail.get("DetailsPerPlayer", []):
            try:
                level = int(p.get("Level", 0))
            except Exception:
                level = 0
            try:
                dmg = int(p.get("DamageDealt", 0))
            except Exception:
                dmg = 0
            try:
                rank = int(p.get("Rank", 0))
            except Exception:
                rank = 0
            players.append({
                "Name": str(p.get("Name", "")).strip(),
                "ClassName": str(p.get("ClassName", "")).strip(),
                "Clan": str(p.get("Clan", "")).strip(),
                "DamageDealt": dmg,
                "Level": level,
                "Rank": rank,
            })
        try:
            duration_sec = int(detail.get("FightDurationSeconds", 0))
        except Exception:
            duration_sec = 0
        try:
            total_dmg = int(detail.get("TotalDamageDone", idx_row.get("TotalDamage", 0)))
        except Exception:
            total_dmg = 0
        history[str(fight_id)] = {
            "FightId": fight_id,
            "BossId": bid,
            "BossName": boss_display_name(bid),
            "DateOfKill": date,
            "FightDuration": idx_row.get("FightDuration", ""),
            "FightDurationSeconds": duration_sec,
            "TotalDamageDone": total_dmg,
            "BossHealth": int(detail.get("BossHealth", 0) or 0),
            "BossRestoredHealth": int(detail.get("BossRestoredHealth", 0) or 0),
            "Players": players,
        }
    with _boss_traverser_lock:
        cache["loaded_at"] = now
        cache["file_count"] = current_count
        cache["history"] = history
        cache["mismatched"] = mismatched
    logger.info(
        f"Loaded traverser history for world {world_id}: {len(history)} fights "
        f"({current_count} files on disk, {mismatched} skipped as wrong-world data)"
    )
    return history


def get_saved_boss_id_for_fight(fight_id, world_id=None):
    history = load_raid_history(world_id=world_id)
    key = str(int(fight_id))
    if key in history:
        try:
            bid = int(history[key].get("BossId", 0))
            if bid in BOSS_NAMES:
                return bid
        except Exception:
            pass
    return 0


def find_detailed_fight_record(fight_id, max_pages=20, world_id=None):
    fight_id = int(fight_id)
    for page in range(1, max_pages + 1):
        try:
            fights = boss_get_detailed_fights(
                num_recs=500, page=page, exclude_dates=False, world_id=world_id
            )
        except Exception:
            break
        if not fights:
            break
        for f in fights:
            try:
                if int(f.get("FightId", 0)) == fight_id:
                    return f
            except Exception:
                continue
    return None


def get_best_boss_id_for_fight(fight_id, fight_data=None, world_id=None):
    """Returns the BossId for `fight_id`, preferring a previously-saved value,
    then the per-fight API response, then a live listing lookup. Returns any
    non-zero BossId we can find — even if not in BOSS_NAMES — so non-Gwydion
    worlds don't lose data for bosses we don't have friendly names for."""
    saved = get_saved_boss_id_for_fight(fight_id, world_id=world_id)
    if saved:
        return saved
    if fight_data:
        try:
            bid = int(fight_data.get("BossId", 0))
            if bid > 0:
                return bid
        except Exception:
            pass
    detailed = find_detailed_fight_record(fight_id, max_pages=20, world_id=world_id)
    if detailed:
        try:
            bid = int(detailed.get("BossId", 0))
            if bid > 0:
                return bid
        except Exception:
            pass
    return 0


def _boss_fight_to_history_record(fight_id, detailed_fight, fight_data, world_id=None):
    # Prefer the listing-API BossId (more reliable), then the per-fight API,
    # then our own history cache. Preserve any non-zero value — don't drop
    # unknown bosses to 0.
    boss_id = 0
    try:
        boss_id = int(detailed_fight.get("BossId", 0))
    except Exception:
        pass
    if not boss_id:
        try:
            boss_id = int(fight_data.get("BossId", 0))
        except Exception:
            pass
    if not boss_id:
        boss_id = get_saved_boss_id_for_fight(fight_id, world_id=world_id)
    duration = int(fight_data.get("FightDurationSeconds", 0))
    total_damage = int(fight_data.get("TotalDamageDone", detailed_fight.get("TotalDamage", 0)))
    boss_hp = int(fight_data.get("BossHealth", 0))
    boss_heal = int(fight_data.get("BossRestoredHealth", 0))
    players = []
    for p in fight_data.get("DetailsPerPlayer", []):
        players.append({
            "Name": str(p.get("Name", "")).strip(),
            "ClassName": str(p.get("ClassName", "")).strip(),
            "Clan": str(p.get("Clan", "")).strip(),
            "DamageDealt": int(p.get("DamageDealt", 0)),
            "Level": int(p.get("Level", 0)),
            "Rank": int(p.get("Rank", 0)),
        })
    return {
        "FightId": int(fight_id),
        "BossId": boss_id,
        "BossName": boss_display_name(boss_id),
        "DateOfKill": str(detailed_fight.get("DateOfKill", "")),
        "FightDuration": str(detailed_fight.get("FightDuration", "")),
        "FightDurationSeconds": duration,
        "TotalDamageDone": total_damage,
        "BossHealth": boss_hp,
        "BossRestoredHealth": boss_heal,
        "Players": players,
    }


def add_fight_to_history(fight_id, detailed_fight=None, fight_data=None, world_id=None):
    history = load_raid_history(world_id=world_id)
    key = str(int(fight_id))
    if key in history:
        return False
    if fight_data is None:
        fight_data = boss_get_fight_data(fight_id, world_id=world_id)
    if detailed_fight is None:
        detailed_fight = find_detailed_fight_record(fight_id, max_pages=20, world_id=world_id) or {}
    history[key] = _boss_fight_to_history_record(fight_id, detailed_fight, fight_data, world_id=world_id)
    save_raid_history(history, world_id=world_id)
    return True


def initialize_posted_fights_if_needed(world_id=None):
    """Seeds posted_fights.json for `world_id` from the current API page if that
    world has no entry yet. Prevents replay of every historical fight when a new
    world is configured."""
    if world_id is None:
        world_id = GWYDION_WORLD_ID
    world_id = int(world_id)
    # If this world already has a key in posted_fights, skip seeding.
    if world_id in _world_keys_in_posted_file():
        return
    try:
        fights = boss_get_detailed_fights(num_recs=100, page=1, world_id=world_id)
    except Exception:
        logger.exception(
            f"Could not seed posted fights from API for world {world_id}; "
            f"writing empty set"
        )
        save_posted_fights(set(), world_id=world_id)
        return
    current = {
        int(f.get("FightId", 0))
        for f in fights
        if int(f.get("BossId", 0)) in CONFIRMED_BOSS_IDS
    }
    save_posted_fights(current, world_id=world_id)
    logger.info(
        f"Seeded posted_fights.json for world {world_id} with {len(current)} existing fight(s)"
    )


# ─── Roster bridge: Winston schema -> Larry's Pilot/Toon shape ────────────

def boss_get_pilot_toon_map():
    """Returns [{Pilot, Toon Name, Class}, ...] from Winston's clan-reader sheet.
    Mains (col C truthy): Pilot == Toon Name.
    Alts: Pilot == col G (Main Character) if present, else fallback to Toon Name.
    """
    try:
        names      = cached_col_values(bot4ws1, 1, "boss_roster_names",     ttl=120)
        mains      = cached_col_values(bot4ws1, 3, "boss_roster_mains",     ttl=120)
        classes    = cached_col_values(bot4ws1, 5, "boss_roster_classes",   ttl=120)
        main_chars = cached_col_values(bot4ws1, 7, "boss_roster_mainchars", ttl=120)
    except Exception:
        logger.exception("Could not read roster columns for boss leaderboard")
        return []
    names      = names[1:]      if names      else []
    mains      = mains[1:]      if mains      else []
    classes    = classes[1:]    if classes    else []
    main_chars = main_chars[1:] if main_chars else []
    rows = []
    for i, toon_name in enumerate(names):
        if not toon_name or not str(toon_name).strip():
            continue
        toon_name = str(toon_name).strip()
        is_main = str(mains[i] if i < len(mains) else "").strip().lower() in ("true", "1", "yes")
        cls = str(classes[i] if i < len(classes) else "").strip()
        if is_main:
            pilot = toon_name
        else:
            cand = str(main_chars[i] if i < len(main_chars) else "").strip()
            pilot = cand if cand else toon_name
        rows.append({"Pilot": pilot, "Toon Name": toon_name, "Class": cls})
    return rows


def boss_get_roster_map():
    return {boss_normalize_name(r["Toon Name"]): r for r in boss_get_pilot_toon_map()}


def boss_get_roster_lookup_for_toon(roster_map, toon_name):
    return roster_map.get(boss_normalize_name(toon_name))


# ─── PIL chart renderer (cross-platform font fallbacks) ───────────────────

def _boss_load_font(size, bold=False):
    if bold:
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "arialbd.ttf",
            "DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _boss_trim_text(text, max_chars):
    text = str(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."


def _boss_build_pilot_totals(players):
    try:
        roster_map = boss_get_roster_map()
    except Exception:
        roster_map = {}
    pilot_totals = {}
    missing_toons = []
    for p in players:
        toon_name = str(p.get("Name", "Unknown")).strip()
        damage = int(p.get("DamageDealt", 0))
        lookup = boss_get_roster_lookup_for_toon(roster_map, toon_name)
        if lookup:
            pilot = lookup["Pilot"]
        else:
            pilot = toon_name
            missing_toons.append(toon_name)
        if pilot not in pilot_totals:
            pilot_totals[pilot] = {"Damage": 0, "Toons": []}
        pilot_totals[pilot]["Damage"] += damage
        if toon_name not in pilot_totals[pilot]["Toons"]:
            pilot_totals[pilot]["Toons"].append(toon_name)
    sorted_pilots = sorted(pilot_totals.items(), key=lambda item: item[1]["Damage"], reverse=True)
    return sorted_pilots, sorted(set(missing_toons))


def _boss_calc_pilot_row_heights(sorted_pilots):
    heights = []
    for _pilot_name, info in sorted_pilots:
        toons = ", ".join(info["Toons"])
        wrapped = textwrap.wrap(toons, width=42) or [""]
        heights.append(44 + (len(wrapped) * 19))
    return heights


def create_boss_chart_image(fight_id, data, title, show_pilots=True):
    """Renders the damage chart PNG for a fight.

    When `show_pilots` is False, the right-hand Pilot/Toons table is omitted
    (used for non-Gwydion servers that don't have the Relentless roster sheet).
    """
    duration = int(data.get("FightDurationSeconds", 0))
    total_damage = int(data.get("TotalDamageDone", 0))
    boss_hp = int(data.get("BossHealth", 0))
    boss_heal = int(data.get("BossRestoredHealth", 0))
    players = data.get("DetailsPerPlayer", [])
    players = sorted(players, key=lambda x: int(x.get("Rank", 999)))
    if show_pilots:
        sorted_pilots, missing_toons = _boss_build_pilot_totals(players)
    else:
        sorted_pilots, missing_toons = [], []

    left_x, left_w = 25, 1160
    right_x, right_w = 1225, 650
    if show_pilots:
        width = 1900
    else:
        width = left_x + left_w + 25  # 1210 — just enough for the left table + margin
    top = 30
    row_h = 34
    header_h = 145
    pilot_row_heights = _boss_calc_pilot_row_heights(sorted_pilots) if show_pilots else []
    left_table_h = row_h * (len(players) + 1)
    right_table_h = row_h + sum(pilot_row_heights) if show_pilots else 0
    table_h = max(left_table_h, right_table_h, 8 * row_h)
    height = header_h + table_h + 115

    img = Image.new("RGB", (width, height), (10, 10, 10))
    draw = ImageDraw.Draw(img)
    font_title = _boss_load_font(36, bold=True)
    font_sub = _boss_load_font(20)
    font_header = _boss_load_font(18, bold=True)
    font_row = _boss_load_font(17)
    font_small = _boss_load_font(15)
    font_tiny = _boss_load_font(14)

    white = (245, 245, 245)
    gray = (170, 170, 170)
    dark_gray = (32, 32, 32)
    header_bg = (45, 45, 45)
    blue = (0, 105, 255)
    line_color = (80, 80, 80)
    orange_warning = (255, 190, 120)
    toon_gray = (190, 190, 190)

    draw.text((width // 2, top), title, fill=white, font=font_title, anchor="ma")
    sub_y = top + 52
    minutes = duration // 60
    seconds = duration % 60
    duration_text = f"{minutes}:{seconds:02d}"
    draw.text((width // 2, sub_y),
              f"Fight {fight_id}   |   Time: {duration_text}   |   Total Damage: {total_damage:,}",
              fill=gray, font=font_sub, anchor="ma")
    draw.text((width // 2, sub_y + 30),
              f"Boss HP: {boss_hp:,}   |   Boss Heal/Restore: {boss_heal:,}",
              fill=gray, font=font_small, anchor="ma")

    table_y = header_h
    draw.rectangle((left_x, table_y, left_x + left_w, table_y + row_h), fill=header_bg)
    draw.text((left_x + 10, table_y + 8), "Rank", fill=white, font=font_header)
    draw.text((left_x + 80, table_y + 8), "Player", fill=white, font=font_header)
    draw.text((left_x + 300, table_y + 8), "Class", fill=white, font=font_header)
    draw.text((left_x + 430, table_y + 8), "Damage", fill=white, font=font_header)
    draw.text((left_x + 590, table_y + 8), "%", fill=white, font=font_header)
    draw.text((left_x + 700, table_y + 8), "DPS", fill=white, font=font_header)
    draw.text((left_x + 810, table_y + 8), "DPS Bar", fill=white, font=font_header)

    if show_pilots:
        draw.rectangle((right_x, table_y, right_x + right_w, table_y + row_h), fill=header_bg)
        draw.text((right_x + 10, table_y + 8), "Pilot", fill=white, font=font_header)
        draw.text((right_x + 315, table_y + 8), "Total Damage",
                  fill=white, font=font_header, anchor="ra")
        draw.text((right_x + 430, table_y + 8), "%", fill=white, font=font_header, anchor="ra")
        draw.text((right_x + 555, table_y + 8), "Total DPS",
                  fill=white, font=font_header, anchor="ra")

    max_dps = 1
    for p in players:
        dmg = int(p.get("DamageDealt", 0))
        dps = dmg / duration if duration else 0
        max_dps = max(max_dps, dps)

    for i, p in enumerate(players):
        y = table_y + row_h * (i + 1)
        if i % 2 == 0:
            draw.rectangle((left_x, y, left_x + left_w, y + row_h), fill=(18, 18, 18))
        rank = str(p.get("Rank", "?"))
        name = _boss_trim_text(p.get("Name", "Unknown"), 20)
        class_name = p.get("ClassName", "?")
        dmg = int(p.get("DamageDealt", 0))
        dps = dmg / duration if duration else 0
        percent = dmg / total_damage * 100 if total_damage else 0
        draw.text((left_x + 10, y + 8), rank, fill=white, font=font_row)
        draw.text((left_x + 80, y + 8), name, fill=white, font=font_row)
        draw.text((left_x + 300, y + 8), class_name, fill=white, font=font_row)
        draw.text((left_x + 540, y + 8), f"{dmg:,}", fill=white, font=font_row, anchor="ra")
        draw.text((left_x + 650, y + 8), f"{percent:.2f}%",
                  fill=white, font=font_row, anchor="ra")
        draw.text((left_x + 760, y + 8), f"{dps:.1f}",
                  fill=white, font=font_row, anchor="ra")
        bar_x = left_x + 810
        bar_y = y + 8
        bar_w_max = 315
        bar_h = 18
        bar_w = int((dps / max_dps) * bar_w_max) if max_dps else 0
        draw.rectangle((bar_x, bar_y, bar_x + bar_w_max, bar_y + bar_h), fill=dark_gray)
        draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), fill=blue)
        draw.text((bar_x + 8, bar_y + 1), f"{dps:.1f}", fill=white, font=font_small)

    if show_pilots:
        current_y = table_y + row_h
        for i, (pilot_name, info) in enumerate(sorted_pilots):
            row_height = pilot_row_heights[i]
            if i % 2 == 0:
                draw.rectangle((right_x, current_y, right_x + right_w, current_y + row_height),
                               fill=(18, 18, 18))
            dmg = info["Damage"]
            percent = dmg / total_damage * 100 if total_damage else 0
            pilot_dps = dmg / duration if duration else 0
            toons = ", ".join(info["Toons"])
            wrapped_toons = textwrap.wrap(toons, width=42) or [""]
            draw.text((right_x + 10, current_y + 8),
                      _boss_trim_text(pilot_name, 24), fill=white, font=font_row)
            draw.text((right_x + 315, current_y + 8),
                      f"{dmg:,}", fill=white, font=font_row, anchor="ra")
            draw.text((right_x + 430, current_y + 8),
                      f"{percent:.2f}%", fill=white, font=font_row, anchor="ra")
            draw.text((right_x + 555, current_y + 8),
                      f"{pilot_dps:,.1f}", fill=white, font=font_row, anchor="ra")
            toon_y = current_y + 31
            draw.text((right_x + 10, toon_y), "Toons:", fill=toon_gray, font=font_tiny)
            for li, toon_line in enumerate(wrapped_toons):
                draw.text((right_x + 70, toon_y + (li * 19)),
                          toon_line, fill=toon_gray, font=font_tiny)
            current_y += row_height

    draw.rectangle((left_x, table_y, left_x + left_w, table_y + left_table_h),
                   outline=line_color, width=2)
    if show_pilots:
        draw.rectangle((right_x, table_y, right_x + right_w, table_y + right_table_h),
                       outline=line_color, width=2)

    footer_y = height - 75
    draw.text((25, footer_y), "Boss Leaderboard chart (via Winston)",
              fill=gray, font=font_small)
    if show_pilots and missing_toons:
        missing_text = "Roster missing: " + ", ".join(missing_toons)
        draw.text((25, footer_y + 28), _boss_trim_text(missing_text, 180),
                  fill=orange_warning, font=font_small)

    output_path = os.path.join(_BOSS_DIR, f"boss_damage_chart_{int(fight_id)}.png")
    img.save(output_path)
    return output_path


# ─── Auto-poller ──────────────────────────────────────────────────────────

# Prevents overlap between the scheduled tick and a manual $bosspollnow.
_boss_poll_lock = asyncio.Lock()


def _collect_auto_post_targets():
    """Returns {world_id: [(guild_id, channel_id, show_pilots), ...]}.

    Sources:
    - Every entry in server_config.json that has a valid world_id and channel_id.
    - The primary Gwydion guild (using GWYDION_AUTO_POST_CHANNEL_ID) is seeded
      implicitly so the legacy auto-post target keeps firing without the four
      Relentless guilds having to run $setworld/$setchannel manually.
    """
    targets = {}
    seen_gwydion_primary = False
    for gid, entry in get_all_configured_guilds():
        try:
            wid = int(entry.get("world_id", 0))
        except Exception:
            continue
        cid = entry.get("channel_id")
        if not cid:
            continue
        targets.setdefault(wid, []).append((gid, int(cid), is_gwydion_guild(gid)))
        if wid == GWYDION_WORLD_ID and int(cid) == GWYDION_AUTO_POST_CHANNEL_ID:
            seen_gwydion_primary = True
    # Legacy Gwydion fallback: always include the hardcoded channel even if no
    # entry exists for it yet. Posting goes to that channel directly; we don't
    # know which of the four Relentless guilds owns it without inspecting it.
    if not seen_gwydion_primary:
        # show_pilots=True because this is the canonical Gwydion auto-post.
        targets.setdefault(GWYDION_WORLD_ID, []).append(
            (None, GWYDION_AUTO_POST_CHANNEL_ID, True)
        )
    return targets


async def boss_perform_auto_check():
    """Iterates every configured guild's world, posts any new fights to that
    guild's channel, and persists per-world state. Returns total fights posted
    across all guilds this cycle."""
    if _boss_poll_lock.locked():
        logger.info("Boss auto-check skipped — another cycle is already running")
        return 0
    async with _boss_poll_lock:
        targets = _collect_auto_post_targets()
        if not targets:
            logger.info("No configured guilds with auto-post channels; nothing to do")
            return 0
        total_posted = 0
        for world_id, guild_channels in targets.items():
            try:
                posted = await sheet_call(load_posted_fights, world_id=world_id)
                try:
                    fights = await sheet_call(boss_get_detailed_fights, num_recs=100, page=1, world_id=world_id)
                except Exception:
                    logger.exception(f"Boss auto-check API failed for world {world_id}")
                    continue
                known = [f for f in fights if int(f.get("BossId", 0)) in CONFIRMED_BOSS_IDS]
                new_fights = [f for f in known if int(f.get("FightId", 0)) not in posted]
                if not new_fights:
                    continue
                new_fights = sorted(new_fights, key=lambda f: int(f.get("FightId", 0)))

                for fight in new_fights:
                    fight_id = int(fight.get("FightId", 0))
                    # Fetch fight detail ONCE per fight, share across all guilds on this world.
                    try:
                        data = await sheet_call(boss_get_fight_data, fight_id, world_id=world_id)
                        boss_id = await sheet_call(get_best_boss_id_for_fight, fight_id, data, world_id=world_id)
                        await sheet_call(add_fight_to_history, fight_id, fight_data=data, world_id=world_id)
                    except Exception:
                        logger.exception(
                            f"Failed to fetch fight {fight_id} (world {world_id}); skipping"
                        )
                        continue

                    for gid, channel_id, show_pilots in guild_channels:
                        channel = client.get_channel(int(channel_id))
                        if channel is None:
                            logger.warning(
                                f"Auto-post channel {channel_id} not found (guild {gid}, "
                                f"world {world_id}); skipping"
                            )
                            continue
                        try:
                            title = f"{boss_display_name(boss_id)} - Damage Chart"
                            image_path = await sheet_call(
                                create_boss_chart_image, fight_id, data, title, show_pilots=show_pilots
                            )
                            await channel.send(
                                f"New **{boss_display_name(boss_id)}** raid detected. "
                                f"Fight ID: **{fight_id}**"
                            )
                            chart_msg = await channel.send(file=discord.File(image_path))
                            try:
                                os.remove(image_path)
                            except Exception:
                                pass
                            # Always open a discussion thread on the chart. The
                            # "LB damage" role ping is a Relentless convention,
                            # so only attempt that lookup in Gwydion guilds.
                            try:
                                thread = await chart_msg.create_thread(
                                    name=f"{boss_display_name(boss_id)} - Fight {fight_id}",
                                    auto_archive_duration=1440,  # 24h
                                )
                                is_gw = is_gwydion_guild(gid) or (
                                    gid is None
                                    and int(channel_id) == GWYDION_AUTO_POST_CHANNEL_ID
                                )
                                if is_gw:
                                    lb_role = None
                                    if channel.guild:
                                        for r in channel.guild.roles:
                                            if r.name.lower() == "lb damage":
                                                lb_role = r
                                                break
                                    mention = lb_role.mention if lb_role else "@LB damage"
                                    allowed = (
                                        discord.AllowedMentions(roles=[lb_role])
                                        if lb_role else discord.AllowedMentions.none()
                                    )
                                    await thread.send(
                                        f"{mention} new **{boss_display_name(boss_id)}** run — "
                                        f"Fight `{fight_id}`.",
                                        allowed_mentions=allowed,
                                    )
                                else:
                                    await thread.send(
                                        f"New **{boss_display_name(boss_id)}** run — "
                                        f"Fight `{fight_id}`. Discuss here.",
                                        allowed_mentions=discord.AllowedMentions.none(),
                                    )
                            except discord.Forbidden:
                                logger.warning(
                                    "Bot lacks permission to create threads or mention "
                                    f"roles in channel {channel_id}"
                                )
                            except Exception:
                                logger.exception(
                                    f"Failed to create thread for fight {fight_id}"
                                )
                            total_posted += 1
                            await asyncio.sleep(0.5)
                        except Exception:
                            logger.exception(
                                f"Failed to post fight {fight_id} to guild {gid} "
                                f"channel {channel_id}"
                            )

                    # Mark the fight as posted ONCE per world (regardless of how many
                    # guilds saw it). Any guild's post failure doesn't replay the
                    # whole world — prevents storms.
                    posted.add(fight_id)
                    await sheet_call(save_posted_fights, posted, world_id=world_id)
            except Exception:
                logger.exception(f"Boss auto-check iteration failed for world {world_id}")
        return total_posted


@tasks.loop(time=BOSS_POLL_ANCHOR_TIMES)
async def boss_poll_loop():
    try:
        count = await boss_perform_auto_check()
        if count:
            logger.info(f"Boss poll posted {count} new fight(s) at anchor tick")
    except Exception:
        logger.exception("Boss poll iteration failed")


# ─── Commands ─────────────────────────────────────────────────────────────

def _boss_collect_fights_for_listing(world_id=None):
    """Merges traverser + local raid history + a single live API page (for fights
    newer than what either source has). Returns a list of fight rows sorted by
    FightId DESC. Each row has at least FightId, BossId, DateOfKill. Excluded
    dates are filtered out."""
    by_id = {}
    for rec in boss_load_traverser_history(world_id=world_id).values():
        try:
            fid = int(rec.get("FightId", 0))
        except Exception:
            continue
        if fid <= 0:
            continue
        by_id[fid] = {
            "FightId": fid,
            "BossId": int(rec.get("BossId", 0)),
            "DateOfKill": rec.get("DateOfKill", ""),
        }
    for rec in load_raid_history(world_id=world_id).values():
        try:
            fid = int(rec.get("FightId", 0))
        except Exception:
            continue
        if fid <= 0 or fid in by_id:
            continue
        if _boss_is_excluded_date(rec.get("DateOfKill", "")):
            continue
        by_id[fid] = {
            "FightId": fid,
            "BossId": int(rec.get("BossId", 0)),
            "DateOfKill": rec.get("DateOfKill", ""),
        }
    # Best-effort: one live API page for ultra-recent fights not yet scraped.
    try:
        for f in boss_get_detailed_fights(num_recs=500, page=1, world_id=world_id):
            try:
                fid = int(f.get("FightId", 0))
            except Exception:
                continue
            if fid <= 0 or fid in by_id:
                continue
            by_id[fid] = {
                "FightId": fid,
                "BossId": int(f.get("BossId", 0)),
                "DateOfKill": f.get("DateOfKill", ""),
            }
    except Exception:
        logger.exception("Live API fetch in $fights failed; serving cached sources only")
    return sorted(by_id.values(), key=lambda r: r["FightId"], reverse=True)


class FightsPaginator(discord.ui.View):
    """Button-paginated embed view for the $fights command."""

    def __init__(self, fights_list, per_page=20, timeout=300, world_label=None):
        super().__init__(timeout=timeout)
        self.fights = fights_list
        self.per_page = per_page
        self.page = 0
        self.max_page = max(0, (len(fights_list) - 1) // per_page)
        self.message = None
        self.world_label = world_label or "Gwydion"
        # Build buttons programmatically so callback signatures match across
        # discord.py / py-cord variants.
        self.btn_first = discord.ui.Button(label="⏮ First", style=discord.ButtonStyle.secondary)
        self.btn_prev = discord.ui.Button(label="◀ Prev", style=discord.ButtonStyle.primary)
        self.btn_indicator = discord.ui.Button(
            label=self._indicator_label(), style=discord.ButtonStyle.secondary, disabled=True
        )
        self.btn_next = discord.ui.Button(label="Next ▶", style=discord.ButtonStyle.primary)
        self.btn_last = discord.ui.Button(label="Last ⏭", style=discord.ButtonStyle.secondary)
        self.btn_first.callback = self._go_first
        self.btn_prev.callback = self._go_prev
        self.btn_next.callback = self._go_next
        self.btn_last.callback = self._go_last
        for b in (self.btn_first, self.btn_prev, self.btn_indicator, self.btn_next, self.btn_last):
            self.add_item(b)
        self._refresh_button_states()

    def _indicator_label(self):
        return f"Page {self.page + 1} / {self.max_page + 1}"

    def _refresh_button_states(self):
        at_start = self.page <= 0
        at_end = self.page >= self.max_page
        self.btn_first.disabled = at_start
        self.btn_prev.disabled = at_start
        self.btn_next.disabled = at_end
        self.btn_last.disabled = at_end
        self.btn_indicator.label = self._indicator_label()

    def render_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        page_rows = self.fights[start:end]
        embed = discord.Embed(
            title=f"Recent {self.world_label} Fights — Page {self.page + 1}/{self.max_page + 1}",
            colour=discord.Color.orange(),
        )
        if not page_rows:
            embed.description = "No fights to display."
            return embed
        for idx, fight in enumerate(page_rows, start=start + 1):
            fid = fight.get("FightId", "?")
            bid = int(fight.get("BossId", 0))
            bname = BOSS_NAMES.get(bid, f"Unknown ({bid})")
            date = fight.get("DateOfKill", "?")
            embed.add_field(
                name=f"{idx}. Fight {fid}",
                value=f"{bname} — {date}",
                inline=False,
            )
        embed.set_footer(
            text=f"Total: {len(self.fights)} fights  •  use the buttons to navigate"
        )
        return embed

    async def _update(self, interaction):
        self._refresh_button_states()
        await interaction.response.edit_message(embed=self.render_embed(), view=self)

    async def _go_first(self, interaction):
        self.page = 0
        await self._update(interaction)

    async def _go_prev(self, interaction):
        if self.page > 0:
            self.page -= 1
        await self._update(interaction)

    async def _go_next(self, interaction):
        if self.page < self.max_page:
            self.page += 1
        await self._update(interaction)

    async def _go_last(self, interaction):
        self.page = self.max_page
        await self._update(interaction)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


@client.command(aliases=['fightlist', 'recentfights'])
async def fights(ctx, per_page: int = 20):
    """Lists recent in-game fights for this server's configured Celtic Heroes world,
    with button pagination. Optional arg: per-page size (default 20, max 25 —
    Discord embed field cap)."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    per_page = max(1, min(per_page, 25))
    fights_list = await sheet_call(_boss_collect_fights_for_listing, world_id=world_id)
    world_label = display_world(world_id)
    if not fights_list:
        await ctx.send(
            f"No {world_label} fights found in traverser, local history, or live API."
        )
        return
    view = FightsPaginator(
        fights_list, per_page=per_page, timeout=300, world_label=world_label
    )
    msg = await ctx.send(embed=view.render_embed(), view=view)
    view.message = msg


@client.command(aliases=['damagechart'])
async def sheet(ctx, *, target: str):
    """Damage chart for a fight ID, or the latest fight of a named boss alias.
    Uses this server's configured Celtic Heroes world (set via `$setworld`)."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    show_pilots = is_gwydion_guild(ctx.guild.id)
    world_label = display_world(world_id)
    try:
        target_clean = target.strip()
        if target_clean.isdigit():
            fight_id = int(target_clean)
            data = await sheet_call(boss_get_fight_data, fight_id, world_id=world_id)
            boss_id = await sheet_call(get_best_boss_id_for_fight, fight_id, data, world_id=world_id)
        else:
            boss_id, fight_id = await sheet_call(boss_get_latest_boss_fight_id, target_clean, world_id=world_id)
            if not boss_id:
                await ctx.send(f"Unknown boss `{target}`. Try `$bossaliases`.")
                return
            if not fight_id:
                await ctx.send(
                    f"No recent {world_label} fight found for {boss_display_name(boss_id)}."
                )
                return
            data = await sheet_call(boss_get_fight_data, fight_id, world_id=world_id)
        title = f"{boss_display_name(boss_id)} - Damage Chart"
        image_path = await sheet_call(create_boss_chart_image, fight_id, data, title, show_pilots=show_pilots)
        await sheet_call(add_fight_to_history, fight_id, fight_data=data, world_id=world_id)
        try:
            await ctx.send(
                f"Damage chart for fight **{fight_id}** ({world_label})",
                file=discord.File(image_path),
            )
        finally:
            try:
                os.remove(image_path)
            except Exception:
                pass
    except Exception as e:
        logger.exception("sheet command failed")
        await ctx.send(f"Could not generate chart: {e}")


@client.command()
async def bossaliases(ctx):
    """Lists the boss alias shortcuts usable with $sheet."""
    lines = ["**Boss Aliases (for `$sheet <alias>`)**", "```"]
    lines.append("prime  = Proteus Prime")
    lines.append("bt     = Bloodthorn the Ravenous")
    lines.append("gele   = Gelebron")
    lines.append("base   = Proteus Base")
    lines.append("dino   = Dhiothu")
    lines.append("hrung  = Hrungnir")
    lines.append("mord   = Mordris")
    lines.append("necro  = Efnisien the Necromancer")
    lines.append("crom   = Crom's Hellborne Manikin")
    lines.append("```")
    await ctx.send("\n".join(lines))


@client.command(aliases=['leaderboardhelp', 'lbh', 'lbinfo'])
async def lbhelp(ctx):
    """Help for the in-game boss leaderboard commands available to all servers
    (set up by an admin via `$setworld` / `$setchannel`)."""
    lines = [
        "**Winston Boss Leaderboard — Commands**",
        "",
        "*Winston tracks Celtic Heroes boss-kill data per server. Each Discord*",
        "*server can be configured for one CH world; data and auto-posting are*",
        "*kept separate per world.*",
        "",
        "**Setup (admin / Winston Admin / REDALiCE / configured role):**",
        "`$setworld <world_id_or_name>` — pick this server's CH world (e.g. `gwydion` or `15`)",
        "`$setchannel [#channel]` — choose where boss kills are auto-posted",
        "`$setchanneloff` — disable auto-posting (commands still work)",
        "`$setsetuprole <role>` — optionally let another role configure the bot",
        "`$serverinfo` — show this server's current configuration",
        "`$listworlds` — known Celtic Heroes world names",
        "`$resetserver` — clear this server's configuration",
        "",
        "**Leaderboard queries (everyone):**",
        "`$fights [per_page]` — paginated list of recent in-game raids",
        "`$sheet <fight_id_or_boss>` — damage chart for a fight or latest of a boss",
        "`$bossaliases` — boss-name shortcuts usable with `$sheet`",
        "`$bosspollstatus` — auto-poller status and posted-fight counts",
        "`$historyinfo` — saved fight counts per boss",
        "`$fighthistory [N] <player> <boss>` — last N fights at a boss",
        "`$bests <boss> [Nd|Nw|Nm|Ny] [unique]` — top damage/DPS at a boss",
        "`$statcard <player> [window] [boss]` — best damage/DPS per boss (PR card)",
        "",
        "**Admin (configured setup role):**",
        "`$bossreloadtraverser` — force-refresh the traverser cache",
        "`$bossrescrape [year|all]` — repair truncated cached fight JSONs",
        "`$bosspollnow` — force an immediate auto-check cycle",
        "`$repairhistory [max_pages]` — re-fetch missing BossIds from the live API",
        "",
        "*DKP, roster, and bidding commands are Gwydion-Relentless-only and won't run elsewhere.*",
    ]
    await ctx.send("\n".join(lines))


@client.command()
async def bosspollstatus(ctx):
    """Shows auto-poller status and next scheduled fire (UTC) for this server."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    world_label = display_world(world_id)
    posted = await sheet_call(load_posted_fights, world_id=world_id)
    history = await sheet_call(load_raid_history, world_id=world_id)
    entry = get_server_entry(ctx.guild.id)
    if not entry and is_gwydion_guild(ctx.guild.id):
        # Synthesize a virtual entry for Gwydion legacy guilds
        channel_id = GWYDION_AUTO_POST_CHANNEL_ID
    else:
        channel_id = (entry or {}).get("channel_id") or 0
    now = dt.now(timezone.utc)
    upcoming = []
    for t in BOSS_POLL_ANCHOR_TIMES:
        candidate = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        upcoming.append(candidate)
    next_fire = min(upcoming) if upcoming else None
    excluded = ", ".join(f"{s}→{e}" for s, e in BOSS_EXCLUDED_DATE_RANGES) or "none"
    # Diagnose traverser availability with a specific reason if unreachable.
    fights_dir, index_path = _boss_traverser_paths()
    if not fights_dir:
        tried = "\n  ".join(BOSS_TRAVERSER_DATA_DIRS) or "(none configured)"
        traverser_status = f"NO DIR FOUND — tried:\n  {tried}"
    elif not os.path.isdir(fights_dir):
        traverser_status = f"UNREACHABLE — `{fights_dir}` is not a readable directory"
    elif not os.path.exists(index_path):
        traverser_status = (
            f"INDEX MISSING — `{index_path}` not found "
            f"(traverser may not have finished its first sweep)"
        )
    else:
        traverser_history = await sheet_call(boss_load_traverser_history, world_id=world_id)
        cache = _boss_traverser_cache.get(int(world_id), {})
        traverser_count = cache.get("file_count", -1)
        mismatched = cache.get("mismatched", 0)
        traverser_status = (
            f"`{len(traverser_history)}` loaded for {world_label} "
            f"(files on disk: `{traverser_count}`, "
            f"skipped as wrong-world: `{mismatched}`, "
            f"path: `{fights_dir}`)"
        )
    channel_str = f"<#{channel_id}>" if channel_id else "(none — auto-posting disabled)"
    lines = [
        f"**Boss Poll Status — {world_label}**",
        f"Auto-post channel: {channel_str}",
        f"Schedule (UTC): {', '.join(t.strftime('%H:%M') for t in BOSS_POLL_ANCHOR_TIMES)}",
        f"Next fire (UTC): `{next_fire.strftime('%Y-%m-%d %H:%M') if next_fire else 'n/a'}`",
        f"Loop running: `{boss_poll_loop.is_running()}`",
        f"Posted fights tracked: `{len(posted)}`",
        f"Raid history records (local): `{len(history)}`",
        f"Traverser fights: {traverser_status}",
        f"Excluded date ranges: {excluded}",
    ]
    await ctx.send("\n".join(lines))


@client.command()
async def bossreloadtraverser(ctx):
    """Admin: force-refresh the traverser history cache for this server's world."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    entry = get_server_entry(ctx.guild.id)
    if not is_server_setup_authorized(ctx.author, entry):
        await ctx.send("You don't have permission to run this admin command.")
        return
    try:
        history = await sheet_call(boss_load_traverser_history, world_id=world_id, force=True)
        cache = _boss_traverser_cache.get(int(world_id), {})
        await ctx.send(
            f"Reloaded traverser history: **{len(history)}** {display_world(world_id)} "
            f"fights ({cache.get('file_count', -1)} files on disk)."
        )
    except Exception as e:
        logger.exception("Manual traverser reload failed")
        await ctx.send(f"Traverser reload failed: {e}")


@client.command()
async def bossrescrape(ctx, scope: str = "2026"):
    """Admin: re-fetch any per-fight JSON for this server's world whose
    DetailsPerPlayer is suspiciously short vs the index's GroupScale (sign of
    an API truncation at scrape time). Scope: a year string like '2026', '2025',
    or 'all'. Default: 2026. Refetches with numRecs=2000 and overwrites the
    cached file only if the new response has more players. Invalidates Winston's
    traverser cache when done."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    entry = get_server_entry(ctx.guild.id)
    if not is_server_setup_authorized(ctx.author, entry):
        await ctx.send("You don't have permission to run this admin command.")
        return
    fights_dir, index_path = _boss_traverser_paths()
    if not fights_dir or not os.path.exists(index_path):
        await ctx.send("Traverser data not reachable from this host. See `$bosspollstatus`.")
        return
    try:
        idx = await sheet_call(_read_json_file, index_path)
    except Exception as e:
        await ctx.send(f"Could not read traverser index: {e}")
        return
    year_prefix = "" if scope.lower() == "all" else scope.strip()
    suspects = []
    for r in idx:
        try:
            if int(r.get("WorldId", 0)) != int(world_id):
                continue
            if year_prefix and not str(r.get("DateOfKill", "")).startswith(year_prefix):
                continue
            fid = int(r["FightId"])
        except Exception:
            continue
        fp = os.path.join(fights_dir, f"fight_{int(world_id)}_{fid}.json")
        if not os.path.exists(fp):
            continue
        try:
            d = await sheet_call(_read_json_file, fp)
        except Exception:
            continue
        n = len(d.get("DetailsPerPlayer", []))
        try:
            gs = int(r.get("GroupScale", 0))
        except Exception:
            gs = 0
        # Truncation signal: too few player rows vs the group size
        truncated = (n < gs * 0.6 and n < 6)
        # Wrong-world signal: per-fight TotalDamageDone disagrees with index TotalDamage
        wrong_world = False
        try:
            idx_dmg = int(r.get("TotalDamage", 0) or 0)
            pf_dmg = int(d.get("TotalDamageDone", 0) or 0)
            if idx_dmg > 0 and pf_dmg != idx_dmg:
                wrong_world = True
        except Exception:
            pass
        if truncated or wrong_world:
            suspects.append((fid, fp, n, gs, int(r.get("TotalDamage", 0) or 0)))
    if not suspects:
        await ctx.send(
            f"No truncated or wrong-world fights to repair in scope `{scope}` "
            f"for {display_world(world_id)}."
        )
        return
    await ctx.send(
        f"Found **{len(suspects)}** suspect {display_world(world_id)} fight(s) in scope "
        f"`{scope}` (truncated or wrong-world data). Refetching with `numRecs=2000`, "
        f"validating against the index... (~{len(suspects) * 0.3:.0f}s)"
    )
    fixed = 0
    still_wrong = 0
    errors = 0
    for fid, fp, old_n, gs, expected_dmg in suspects:
        url = (
            f"{BOSS_RANKING_URL}?board=fight&fightid={fid}"
            f"&worldid={int(world_id)}&playerWorldId=0&charId=0"
            f"&sortCol=1&sortDir=0&page=1&numRecs=2000"
        )
        try:
            resp = await sheet_call(requests.get, url, timeout=30)
            resp.raise_for_status()
            d = resp.json()
        except Exception:
            errors += 1
            continue
        # Validate: API may still return wrong-world data for some fights. Only
        # save if TotalDamageDone matches the index's TotalDamage (= same fight).
        api_dmg = int(d.get("TotalDamageDone", 0) or 0)
        if expected_dmg > 0 and api_dmg != expected_dmg:
            still_wrong += 1
            await asyncio.sleep(0.15)
            continue
        await sheet_call(_boss_write_json_atomic, fp, d)
        fixed += 1
        await asyncio.sleep(0.15)
    # Invalidate this world's cache so the next query reloads.
    with _boss_traverser_lock:
        cache = _boss_traverser_cache.get(int(world_id))
        if cache is not None:
            cache["loaded_at"] = 0.0
            cache["file_count"] = -1
    await ctx.send(
        f"Re-scrape complete (scope `{scope}`, {display_world(world_id)}).\n"
        f"Repaired: **{fixed}**, still wrong-world after retry: **{still_wrong}**, "
        f"errors: **{errors}**.\n"
        f"Cache invalidated — next `$fights`/`$sheet` will see the corrected data."
    )


@client.command()
async def bosspollnow(ctx):
    """Admin: force an immediate boss auto-check cycle across all configured guilds."""
    entry = get_server_entry(ctx.guild.id) if ctx.guild else None
    if not is_server_setup_authorized(ctx.author, entry):
        await ctx.send("You don't have permission to run this admin command.")
        return
    await ctx.send("Running boss auto-check now (across all configured guilds)...")
    try:
        count = await boss_perform_auto_check()
        await ctx.send(f"Auto-check complete. Posted **{count}** new fight(s) total.")
    except Exception as e:
        logger.exception("Manual boss auto-check failed")
        await ctx.send(f"Auto-check failed: {e}")


@client.command(aliases=['repairraidhistory', 'fixbossids'])
async def repairhistory(ctx, max_pages: int = 20):
    """Admin: re-fetch BossIds from the live listing API for any raid_history
    entries in this server's world that currently have BossId 0. Scans up to
    `max_pages` pages (default 20, ~10,000 fights) of the live listing. Older
    entries saved before the bot recognised a particular boss get repaired."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    entry = get_server_entry(ctx.guild.id)
    if not is_server_setup_authorized(ctx.author, entry):
        await ctx.send("You don't have permission to run this admin command.")
        return
    world_label = display_world(world_id)
    history = await sheet_call(load_raid_history, world_id=world_id)
    bad_keys = [k for k, rec in history.items() if int(rec.get("BossId", 0) or 0) == 0]
    if not bad_keys:
        await ctx.send(
            f"No BossId=0 entries to repair in {world_label} raid_history "
            f"(scanned {len(history)} records)."
        )
        return
    await ctx.send(
        f"Found **{len(bad_keys)}** {world_label} entries with BossId=0. "
        f"Scanning up to **{max_pages}** API page(s) (~{max_pages * 500} fights) "
        f"to find their correct BossIds..."
    )

    # Build a FightId -> BossId map from the live listing API
    fight_to_boss = {}
    for page in range(1, max(1, int(max_pages)) + 1):
        try:
            fights = await sheet_call(
                boss_get_detailed_fights,
                num_recs=500, page=page, exclude_dates=False, world_id=world_id
            )
        except Exception:
            logger.exception(f"repairhistory: API fetch failed on page {page}")
            break
        if not fights:
            break
        for f in fights:
            try:
                fid = int(f.get("FightId", 0))
                bid = int(f.get("BossId", 0))
            except Exception:
                continue
            if fid > 0 and bid > 0:
                fight_to_boss[fid] = bid
        await asyncio.sleep(0.15)

    fixed = 0
    not_found = 0
    for key in bad_keys:
        try:
            fid = int(key)
        except Exception:
            not_found += 1
            continue
        bid = fight_to_boss.get(fid, 0)
        if bid > 0:
            history[key]["BossId"] = bid
            history[key]["BossName"] = boss_display_name(bid)
            fixed += 1
        else:
            not_found += 1

    if fixed:
        await sheet_call(save_raid_history, history, world_id=world_id)

    await ctx.send(
        f"Repair complete for **{world_label}**.\n"
        f"Repaired: **{fixed}** of **{len(bad_keys)}** entries. "
        f"Could not resolve: **{not_found}** (live API didn't return those fights "
        f"in the scanned window — try `$repairhistory 40` for a larger scan)."
    )


# ─── Player stat card ─────────────────────────────────────────────────────

def _boss_resolve_pilot_identity(query):
    """Returns (display_name, toon_keys_set, mode_text) for the player query.
    Toon-first: if the query matches a toon name, returns just that one character.
    Only falls back to pilot mode if no toon matches at all (covers nicknames that
    aren't on any toon). Returns (None, None, error_message) if neither matches."""
    roster_rows = boss_get_pilot_toon_map()
    if not roster_rows:
        return None, None, "Roster unreadable."
    all_toons = [r["Toon Name"] for r in roster_rows]
    toon_realname, _c, _s, toon_suggestions = find_name(query, all_toons)
    if toon_realname:
        return toon_realname, {boss_normalize_name(toon_realname)}, "Toon only"
    pilots = sorted({r["Pilot"] for r in roster_rows})
    pilot_realname, _caps, _spaces, pilot_suggestions = find_name(query, pilots)
    if pilot_realname:
        toon_keys = {
            boss_normalize_name(r["Toon Name"])
            for r in roster_rows
            if r["Pilot"] == pilot_realname
        }
        return pilot_realname, toon_keys, "Pilot total"
    suggestions = toon_suggestions or pilot_suggestions or []
    return None, None, not_found_message(query, suggestions)


def _boss_extract_statcard_args(args, roster_keys=None):
    """Parses '$statcard' arguments — window, boss alias, and player name can
    appear in any order. Returns (window_token, boss_id, player_name).
    A token that's a boss alias is only treated as a boss if it doesn't also
    match a roster name (so a player named Crom still routes correctly).

    `roster_keys` is the set of normalized roster names preferred over a
    boss-alias interpretation. If None (the default), the Gwydion roster is
    fetched from Google Sheets. Non-Gwydion callers should pass an empty set to
    skip the roster fetch entirely."""
    parts = args.strip().split()
    if not parts:
        return None, None, ""
    if roster_keys is None:
        try:
            roster_rows = boss_get_pilot_toon_map()
            roster_keys = {boss_normalize_name(r["Toon Name"]) for r in roster_rows}
            roster_keys |= {boss_normalize_name(r["Pilot"]) for r in roster_rows}
        except Exception:
            roster_keys = set()
    window_token = None
    boss_id = None
    remaining = []
    for token in parts:
        lower = token.lower()
        if window_token is None and _BOSS_WINDOW_RE.match(lower):
            window_token = lower
            continue
        if boss_id is None:
            key = boss_normalize_name(token)
            if key in BOSS_ALIASES and key not in roster_keys:
                boss_id = BOSS_ALIASES[key]
                continue
        remaining.append(token)
    return window_token, boss_id, " ".join(remaining)


def _boss_collect_player_prs(toon_keys, cutoff_date=None, boss_id_filter=None, world_id=None):
    """Scans the traverser output (canonical) + raid_history.json (auto-poll cache)
    and returns {boss_id: {best_damage, best_dps, fights_counted}} for the given set
    of normalized toon name keys. Excluded dates are skipped. Traverser records win
    on collision. cutoff_date (date) restricts to fights on/after that date.
    boss_id_filter (int) restricts to a single boss. world_id selects the CH world
    (default: Gwydion)."""
    merged = dict(load_raid_history(world_id=world_id))
    merged.update(boss_load_traverser_history(world_id=world_id))
    per_boss = {}
    for rec in merged.values():
        if _boss_is_excluded_date(rec.get("DateOfKill", "")):
            continue
        if cutoff_date is not None:
            kd = _boss_parse_kill_date(rec.get("DateOfKill", ""))
            if not kd or kd < cutoff_date:
                continue
        bid = int(rec.get("BossId", 0))
        if bid not in CONFIRMED_BOSS_IDS:
            continue
        if boss_id_filter is not None and bid != boss_id_filter:
            continue
        duration = int(rec.get("FightDurationSeconds", 0))
        damage = 0
        used_toons = []
        for p in rec.get("Players", []):
            tk = boss_normalize_name(p.get("Name", ""))
            if tk in toon_keys:
                damage += int(p.get("DamageDealt", 0))
                used_toons.append(str(p.get("Name", "")).strip())
        if damage <= 0:
            continue
        dps = damage / duration if duration else 0
        fid = int(rec.get("FightId", 0))
        entry = {
            "FightId": fid,
            "Damage": damage,
            "DPS": dps,
            "Toons": used_toons,
            "Date": rec.get("DateOfKill", ""),
        }
        if bid not in per_boss:
            per_boss[bid] = {"best_damage": entry, "best_dps": entry, "fights_counted": 1}
        else:
            per_boss[bid]["fights_counted"] += 1
            if damage > per_boss[bid]["best_damage"]["Damage"]:
                per_boss[bid]["best_damage"] = entry
            if dps > per_boss[bid]["best_dps"]["DPS"]:
                per_boss[bid]["best_dps"] = entry
    return per_boss


def create_boss_stat_card_image(display_name, mode_text, per_boss, history_count, window_label="all time", boss_label=None):
    """Renders a stat card PNG showing best damage / best DPS per boss for one pilot."""
    width = 1200
    pad = 30
    boss_list = sorted(per_boss.keys(), key=lambda b: boss_display_name(b))
    header_h = 130
    table_header_h = 40
    row_h = 95
    footer_h = 60
    height = header_h + table_header_h + (len(boss_list) * row_h) + footer_h + pad

    img = Image.new("RGB", (width, height), (10, 10, 10))
    draw = ImageDraw.Draw(img)

    font_title = _boss_load_font(36, bold=True)
    font_sub = _boss_load_font(20)
    font_bossname = _boss_load_font(22, bold=True)
    font_label = _boss_load_font(14, bold=True)
    font_value = _boss_load_font(22, bold=True)
    font_small = _boss_load_font(14)
    font_meta = _boss_load_font(13)

    white = (245, 245, 245)
    gray = (170, 170, 170)
    dim = (130, 130, 130)
    accent = (255, 165, 0)
    blue = (100, 180, 255)
    header_bg = (35, 35, 35)
    row_bg_alt = (20, 20, 20)
    line_color = (60, 60, 60)

    # Title + subtitle
    draw.text((width // 2, pad), display_name, fill=white, font=font_title, anchor="ma")
    subtitle = f"Boss PR Card  •  Mode: {mode_text}  •  Window: {window_label}"
    if boss_label:
        subtitle += f"  •  Boss: {boss_label}"
    draw.text(
        (width // 2, pad + 50),
        subtitle,
        fill=gray, font=font_sub, anchor="ma",
    )

    # Column geometry
    col_boss_x = pad
    col_dmg_x = 380
    col_dps_x = 790
    table_y = header_h

    # Header strip
    draw.rectangle((pad, table_y, width - pad, table_y + table_header_h), fill=header_bg)
    draw.text((col_boss_x + 8, table_y + 12), "BOSS", fill=white, font=font_label)
    draw.text((col_dmg_x + 8, table_y + 12), "BEST DAMAGE", fill=accent, font=font_label)
    draw.text((col_dps_x + 8, table_y + 12), "BEST DPS", fill=blue, font=font_label)

    # Rows
    y = table_y + table_header_h
    for i, bid in enumerate(boss_list):
        info = per_boss[bid]
        bd = info["best_damage"]
        bp = info["best_dps"]
        same_fight = bd["FightId"] == bp["FightId"]

        if i % 2 == 0:
            draw.rectangle((pad, y, width - pad, y + row_h), fill=row_bg_alt)

        draw.text((col_boss_x + 8, y + 12), boss_display_name(bid),
                  fill=white, font=font_bossname)
        fights_counted = info.get("fights_counted", 0)
        toon_summary = ", ".join(sorted(set(bd["Toons"] + bp["Toons"])))[:60]
        draw.text((col_boss_x + 8, y + 44),
                  f"{fights_counted} fight(s) in window",
                  fill=dim, font=font_meta)
        draw.text((col_boss_x + 8, y + 62), "Toons: " + (toon_summary or "—"),
                  fill=dim, font=font_meta)

        # Best Damage cell
        draw.text((col_dmg_x + 8, y + 8), f"{bd['Damage']:,}",
                  fill=accent, font=font_value)
        draw.text((col_dmg_x + 8, y + 40), f"@ {bd['DPS']:,.1f} DPS",
                  fill=white, font=font_small)
        draw.text((col_dmg_x + 8, y + 60), f"Fight {bd['FightId']}  •  {bd['Date']}",
                  fill=dim, font=font_meta)

        # Best DPS cell
        draw.text((col_dps_x + 8, y + 8), f"{bp['DPS']:,.1f}",
                  fill=blue, font=font_value)
        draw.text((col_dps_x + 8, y + 40), f"on {bp['Damage']:,} dmg",
                  fill=white, font=font_small)
        if same_fight:
            draw.text((col_dps_x + 8, y + 60), "(same fight as best dmg)",
                      fill=dim, font=font_meta)
        else:
            draw.text((col_dps_x + 8, y + 60), f"Fight {bp['FightId']}  •  {bp['Date']}",
                      fill=dim, font=font_meta)

        y += row_h

    # Table border
    draw.rectangle(
        (pad, table_y, width - pad, table_y + table_header_h + len(boss_list) * row_h),
        outline=line_color, width=2,
    )

    footer_y = height - footer_h + 10
    draw.text(
        (pad, footer_y),
        f"Source: traverser + local raid history "
        f"({history_count} fight(s) total, excluded dates skipped).",
        fill=gray, font=font_small,
    )

    safe_name = boss_normalize_name(display_name) or "player"
    output_path = os.path.join(_BOSS_DIR, f"boss_statcard_{safe_name}.png")
    img.save(output_path)
    return output_path


@client.command(aliases=['playerstats', 'statcards', 'pr'])
async def statcard(ctx, *, args: str):
    """Player stat card: best damage and best DPS per boss from historical data.

    Usage:
      $statcard <player>                     — all time, all bosses
      $statcard <player> 30d                 — last 30 days
      $statcard <player> dhiothu             — Dhiothu only, all time
      $statcard <player> dhiothu 30d         — Dhiothu, last 30 days
      $statcard 30d redalice dhiothu         — any order works

    Window tokens: Nd, Nw, Nm, Ny, or 'all'. Months=30d, years=365d (approx).
    Boss tokens: any alias from `$bossaliases` (bt, gele, dino, etc.).
    Runs on this server's configured CH world (set via `$setworld`). On Gwydion
    servers the player is matched as a single character first, falling back to
    pilot (all alts) only if the name isn't a known toon. On other servers the
    name is treated as a literal toon name (face value, no roster lookup)."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    is_gwydion = is_gwydion_guild(ctx.guild.id)
    try:
        # On non-Gwydion guilds, skip the roster fetch entirely.
        window_token, boss_id, player_name = _boss_extract_statcard_args(
            args, roster_keys=None if is_gwydion else set()
        )
        if not player_name:
            await ctx.send(
                "Usage: `$statcard <player> [window] [boss]` — window: `7d`/`30d`/`6m`/`all`. "
                "Boss: any alias from `$bossaliases`. All three can appear in any order."
            )
            return
        window_delta = _boss_parse_window(window_token) if window_token else None
        cutoff_date = None
        window_label = "all time"
        if window_delta is not None:
            cutoff_date = dt.now(timezone.utc).date() - window_delta
            window_label = f"last {window_token} (since {cutoff_date.isoformat()})"
        boss_label = boss_display_name(boss_id) if boss_id else None
        if is_gwydion:
            display_name, toon_keys, mode_text_or_msg = _boss_resolve_pilot_identity(player_name)
            if not display_name:
                await ctx.send(mode_text_or_msg)
                return
        else:
            # Face-value: the typed name IS the toon. No roster lookup.
            display_name = player_name.strip()
            toon_keys = {boss_normalize_name(display_name)}
            mode_text_or_msg = "Toon only (face value)"
        per_boss = await sheet_call(_boss_collect_player_prs,
            toon_keys, cutoff_date=cutoff_date, boss_id_filter=boss_id, world_id=world_id
        )
        if not per_boss:
            traverser_n = len(await sheet_call(boss_load_traverser_history, world_id=world_id))
            local_n = len(await sheet_call(load_raid_history, world_id=world_id))
            scope = f"window `{window_label}`"
            if boss_label:
                scope += f", boss `{boss_label}`"
            await ctx.send(
                f"No raid records found for `{display_name}` ({scope}).\n"
                f"Sources scanned: traverser=`{traverser_n}` fights, "
                f"local=`{local_n}` fights. Try widening the window or check spelling."
            )
            return
        merged = dict(await sheet_call(load_raid_history, world_id=world_id))
        merged.update(await sheet_call(boss_load_traverser_history, world_id=world_id))
        history_count = len(merged)
        image_path = await sheet_call(
            create_boss_stat_card_image, display_name, mode_text_or_msg, per_boss, history_count,
            window_label=window_label, boss_label=boss_label,
        )
        reply_bits = [
            f"Stat card for **{display_name}**",
            f"{len(per_boss)} boss(es)" if not boss_label else boss_label,
            f"window: {window_label}",
        ]
        try:
            await ctx.send(
                " • ".join(reply_bits),
                file=discord.File(image_path),
            )
        finally:
            try:
                os.remove(image_path)
            except Exception:
                pass
    except Exception as e:
        logger.exception("statcard command failed")
        await ctx.send(f"Could not generate stat card: {e}")


def _boss_extract_last_args(args, roster_keys=None):
    """Parses '$fighthistory' args. Returns (count, boss_id, player_name, leftover).
    Position-independent. First integer in [1, 100] wins as count (default 10).
    Boss alias is required. Player name = whatever remains. Collisions between
    boss aliases and roster names are resolved in favor of the roster.

    `roster_keys` is the set of normalized roster names that should be preferred
    over a boss-alias interpretation (so a player named "Crom" doesn't get parsed
    as the boss alias). If None (the default), the Gwydion roster is fetched from
    Google Sheets. Non-Gwydion callers should pass an empty set to skip the
    roster fetch entirely."""
    parts = args.strip().split()
    count = 10
    count_seen = False
    boss_id = None
    if roster_keys is None:
        try:
            roster_rows = boss_get_pilot_toon_map()
            roster_keys = {boss_normalize_name(r["Toon Name"]) for r in roster_rows}
            roster_keys |= {boss_normalize_name(r["Pilot"]) for r in roster_rows}
        except Exception:
            roster_keys = set()
    leftover = []
    for token in parts:
        if not count_seen:
            try:
                v = int(token)
                if 1 <= v <= 100:
                    count = v
                    count_seen = True
                    continue
            except ValueError:
                pass
        if boss_id is None:
            key = boss_normalize_name(token)
            if key in BOSS_ALIASES and key not in roster_keys:
                boss_id = BOSS_ALIASES[key]
                continue
        leftover.append(token)
    return count, boss_id, " ".join(leftover)


def _boss_collect_player_boss_history(toon_keys, boss_id, limit, world_id=None):
    """Returns a list of run dicts for the player's most recent `limit` fights
    against this boss. Each dict: {FightId, Date, Damage, DPS, Toons, Duration}.
    Sorted newest first by FightId DESC. Excluded dates skipped."""
    merged = dict(load_raid_history(world_id=world_id))
    merged.update(boss_load_traverser_history(world_id=world_id))
    runs = []
    for rec in merged.values():
        if _boss_is_excluded_date(rec.get("DateOfKill", "")):
            continue
        try:
            if int(rec.get("BossId", 0)) != boss_id:
                continue
        except Exception:
            continue
        try:
            duration = int(rec.get("FightDurationSeconds", 0))
        except Exception:
            duration = 0
        damage = 0
        used_toons = []
        for p in rec.get("Players", []):
            tk = boss_normalize_name(p.get("Name", ""))
            if tk in toon_keys:
                try:
                    damage += int(p.get("DamageDealt", 0))
                except Exception:
                    pass
                used_toons.append(str(p.get("Name", "")).strip())
        if damage <= 0:
            continue
        dps = damage / duration if duration else 0
        runs.append({
            "FightId": int(rec.get("FightId", 0)),
            "Date": rec.get("DateOfKill", ""),
            "Damage": damage,
            "DPS": dps,
            "Toons": used_toons,
            "Duration": duration,
        })
    return sorted(runs, key=lambda r: r["FightId"], reverse=True)[:limit]


@client.command(aliases=['lastfights', 'recentfightsfor', 'lh'])
async def fighthistory(ctx, *, args: str):
    """Last N fights at a specific boss for a player, with damage/DPS summary stats.

    Usage:
      $fighthistory <player> <boss>            — last 10 (default)
      $fighthistory 5 <player> <boss>          — last 5
      $fighthistory 20 redalice BT             — last 20 Bloodthorn for REDALiCE
      $fighthistory redalice 10 dhiothu        — any order works

    Boss aliases via `$bossaliases`. On Gwydion servers the player can be a pilot
    or toon name (roster-aware). On other servers the name is treated as a literal
    toon name (face value, no roster lookup)."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    is_gwydion = is_gwydion_guild(ctx.guild.id)
    try:
        # On non-Gwydion guilds, skip the roster fetch entirely
        count, boss_id, player_name = _boss_extract_last_args(
            args, roster_keys=None if is_gwydion else set()
        )
        if not boss_id:
            await ctx.send(
                "Usage: `$fighthistory [N] <player> <boss>` — boss alias required. "
                "Run `$bossaliases`."
            )
            return
        if not player_name:
            await ctx.send(
                "Usage: `$fighthistory [N] <player> <boss>` — player name required."
            )
            return
        if is_gwydion:
            display_name, toon_keys, mode_text = _boss_resolve_pilot_identity(player_name)
            if not display_name:
                await ctx.send(mode_text)
                return
        else:
            # Face-value: the typed name IS the toon. No roster lookup.
            display_name = player_name.strip()
            toon_keys = {boss_normalize_name(display_name)}
            mode_text = "Toon only (face value)"
        runs = await sheet_call(_boss_collect_player_boss_history, toon_keys, boss_id, count, world_id=world_id)
        if not runs:
            await ctx.send(
                f"No saved fights for `{display_name}` at "
                f"**{boss_display_name(boss_id)}**."
            )
            return
        damages = [r["Damage"] for r in runs]
        dpses = [r["DPS"] for r in runs]
        avg_dmg = sum(damages) / len(damages)
        avg_dps = sum(dpses) / len(dpses)
        embed = discord.Embed(
            title=f"{display_name} — Last {len(runs)} {boss_display_name(boss_id)} run(s)",
            description=f"Mode: {mode_text}",
            colour=discord.Color.orange(),
        )
        summary_lines = [
            "**Damage**",
            f"  avg `{avg_dmg:,.0f}`  •  best `{max(damages):,}`  •  low `{min(damages):,}`",
            "**DPS**",
            f"  avg `{avg_dps:,.1f}`  •  best `{max(dpses):,.1f}`  •  low `{min(dpses):,.1f}`",
        ]
        embed.add_field(name="Summary", value="\n".join(summary_lines), inline=False)
        run_lines = []
        for i, r in enumerate(runs, 1):
            toons_str = ", ".join(r["Toons"]) or "—"
            run_lines.append(
                f"**{i}.** Fight `{r['FightId']}` • {r['Date']} — "
                f"`{r['Damage']:,}` dmg • `{r['DPS']:,.1f}` DPS\n"
                f" └ {toons_str}"
            )
        # Split into multiple fields if the joined text exceeds Discord's 1024-char
        # per-field limit (10 runs at ~100 chars per line is right at the edge).
        chunks = []
        current = []
        current_len = 0
        for line in run_lines:
            if current_len + len(line) + 1 > 950:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            current.append(line)
            current_len += len(line) + 1
        if current:
            chunks.append("\n".join(current))
        if len(chunks) == 1:
            embed.add_field(name="Recent runs (newest first)", value=chunks[0], inline=False)
        else:
            for i, chunk in enumerate(chunks, 1):
                embed.add_field(
                    name=f"Recent runs (newest first) — pt {i}/{len(chunks)}",
                    value=chunk, inline=False,
                )
        await ctx.send(embed=embed)
    except Exception as e:
        logger.exception("fighthistory command failed")
        await ctx.send(f"Could not fetch fight history: {e}")


def _boss_extract_bests_args(args):
    """Parses '$bests' args. Returns (boss_id, window_token, unique_flag, leftover).
    Boss alias is required (first match wins). Window and 'unique' flag are
    optional and order-independent."""
    parts = args.strip().split()
    window_token = None
    boss_id = None
    unique = False
    leftover = []
    for token in parts:
        lower = token.lower()
        if lower in ("unique", "u", "uniqueplayers"):
            unique = True
            continue
        if window_token is None and _BOSS_WINDOW_RE.match(lower):
            window_token = lower
            continue
        if boss_id is None:
            key = boss_normalize_name(token)
            if key in BOSS_ALIASES:
                boss_id = BOSS_ALIASES[key]
                continue
        leftover.append(token)
    return boss_id, window_token, unique, leftover


def _boss_collect_top_performances(boss_id, cutoff_date=None, unique_only=False, limit=5, world_id=None):
    """Scans traverser + local raid history for the given boss. Returns
    (top_by_damage, top_by_dps) — each a list of up to `limit` performance dicts:
    {Name, Class, Damage, DPS, FightId, Date}. Excluded dates are skipped.
    If unique_only=True, keeps each toon's single best run per metric."""
    merged = dict(load_raid_history(world_id=world_id))
    merged.update(boss_load_traverser_history(world_id=world_id))
    entries = []
    for rec in merged.values():
        if _boss_is_excluded_date(rec.get("DateOfKill", "")):
            continue
        if cutoff_date is not None:
            kd = _boss_parse_kill_date(rec.get("DateOfKill", ""))
            if not kd or kd < cutoff_date:
                continue
        try:
            if int(rec.get("BossId", 0)) != boss_id:
                continue
        except Exception:
            continue
        try:
            duration = int(rec.get("FightDurationSeconds", 0))
        except Exception:
            duration = 0
        for p in rec.get("Players", []):
            name = str(p.get("Name", "")).strip()
            if not name:
                continue
            try:
                damage = int(p.get("DamageDealt", 0))
            except Exception:
                damage = 0
            if damage <= 0:
                continue
            dps = damage / duration if duration else 0
            entries.append({
                "Name": name,
                "Class": str(p.get("ClassName", "")).strip(),
                "Damage": damage,
                "DPS": dps,
                "FightId": int(rec.get("FightId", 0)),
                "Date": rec.get("DateOfKill", ""),
            })
    if unique_only:
        best_dmg = {}
        best_dps = {}
        for e in entries:
            n = e["Name"]
            if n not in best_dmg or e["Damage"] > best_dmg[n]["Damage"]:
                best_dmg[n] = e
            if n not in best_dps or e["DPS"] > best_dps[n]["DPS"]:
                best_dps[n] = e
        top_dmg = sorted(best_dmg.values(), key=lambda x: -x["Damage"])[:limit]
        top_dps = sorted(best_dps.values(), key=lambda x: -x["DPS"])[:limit]
    else:
        top_dmg = sorted(entries, key=lambda x: -x["Damage"])[:limit]
        top_dps = sorted(entries, key=lambda x: -x["DPS"])[:limit]
    return top_dmg, top_dps


@client.command(aliases=['top', 'topperformances', 'leaderboard'])
async def bests(ctx, *, args: str):
    """Top performances at a specific boss (top 5 by damage + top 5 by DPS) on
    this server's configured Celtic Heroes world.

    Usage:
      $bests <boss>                   — top 5, all time, all entries
      $bests <boss> 30d               — last 30 days only
      $bests <boss> unique            — one entry per toon (their best)
      $bests <boss> 30d unique        — both filters; any order

    Window tokens: Nd, Nw, Nm, Ny, all. Boss is required — try `$bossaliases`."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    try:
        boss_id, window_token, unique_only, leftover = _boss_extract_bests_args(args)
        if not boss_id:
            await ctx.send(
                "Usage: `$bests <boss> [window] [unique]` — boss alias is required. "
                "Run `$bossaliases` for the list."
            )
            return
        window_delta = _boss_parse_window(window_token) if window_token else None
        cutoff_date = None
        window_label = "all time"
        if window_delta is not None:
            cutoff_date = dt.now(timezone.utc).date() - window_delta
            window_label = f"last {window_token}"
        top_dmg, top_dps = await sheet_call(_boss_collect_top_performances,
            boss_id, cutoff_date=cutoff_date, unique_only=unique_only, limit=5,
            world_id=world_id,
        )
        if not top_dmg:
            await ctx.send(
                f"No fights found for **{boss_display_name(boss_id)}** in window `{window_label}`."
            )
            return
        scope = (
            f"Window: {window_label}  •  "
            f"{'Unique toons only' if unique_only else 'All entries (a toon may appear multiple times)'}"
        )
        embed = discord.Embed(
            title=f"{boss_display_name(boss_id)} — Top Performances",
            description=scope,
            colour=discord.Color.orange(),
        )

        def _fmt_class(cls):
            return f" *({cls})*" if cls else ""

        dmg_lines = [
            f"**{i}.** {e['Name']}{_fmt_class(e['Class'])} — "
            f"**{e['Damage']:,}** dmg ({e['DPS']:,.1f} DPS)\n"
            f" └ Fight {e['FightId']} • {e['Date']}"
            for i, e in enumerate(top_dmg, 1)
        ]
        dps_lines = [
            f"**{i}.** {e['Name']}{_fmt_class(e['Class'])} — "
            f"**{e['DPS']:,.1f}** DPS ({e['Damage']:,} dmg)\n"
            f" └ Fight {e['FightId']} • {e['Date']}"
            for i, e in enumerate(top_dps, 1)
        ]
        embed.add_field(name="Top 5 by Damage", value="\n".join(dmg_lines), inline=False)
        embed.add_field(name="Top 5 by DPS", value="\n".join(dps_lines), inline=False)
        if leftover:
            embed.set_footer(text=f"Ignored extra args: {' '.join(leftover)}")
        await ctx.send(embed=embed)
    except Exception as e:
        logger.exception("bests command failed")
        await ctx.send(f"Could not compute top performances: {e}")


@client.command(aliases=['fighthistoryinfo', 'savedfights'])
async def historyinfo(ctx):
    """Shows saved fight counts per boss — total (all worlds) vs this world."""
    world_id = await _require_world_for_ctx(ctx)
    if world_id is None:
        return
    world_label = display_world(world_id)
    fights_dir, index_path = _boss_traverser_paths()
    counts_total = {}
    counts_this_world = {}
    grand_total = 0
    grand_this_world = 0

    if index_path and os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            for row in index:
                try:
                    bid = int(row.get("BossId", 0))
                    wid = int(row.get("WorldId", 0))
                except Exception:
                    continue
                counts_total[bid] = counts_total.get(bid, 0) + 1
                grand_total += 1
                if wid == world_id:
                    counts_this_world[bid] = counts_this_world.get(bid, 0) + 1
                    grand_this_world += 1
        except Exception as e:
            await ctx.send(f"Could not read traverser index: {e}")
            return

    local_count = len(await sheet_call(load_raid_history, world_id=world_id))

    this_world_detail_count = 0
    if fights_dir and os.path.isdir(fights_dir):
        try:
            prefix = f"fight_{world_id}_"
            this_world_detail_count = sum(
                1 for fn in os.listdir(fights_dir)
                if fn.startswith(prefix) and fn.endswith(".json")
            )
        except Exception:
            this_world_detail_count = -1

    if not counts_total and local_count == 0:
        await ctx.send(
            "No saved fight history available. Traverser index missing AND no local "
            "`raid_history.json`. Check `$bosspollstatus` for diagnostics."
        )
        return

    col_label = world_label[:8]
    lines = [f"**Saved Fight History per Boss** ({world_label})", "```"]
    lines.append(f"{'Boss':<30} {'Total':>8} {col_label:>8}")
    lines.append(f"{'-' * 30} {'-' * 8} {'-' * 8}")
    for bid in sorted(BOSS_NAMES.keys(), key=lambda b: BOSS_NAMES[b]):
        lines.append(
            f"{BOSS_NAMES[bid]:<30} "
            f"{counts_total.get(bid, 0):>8} {counts_this_world.get(bid, 0):>8}"
        )
    unknown_total = sum(c for bid, c in counts_total.items() if bid not in BOSS_NAMES)
    unknown_this_world = sum(c for bid, c in counts_this_world.items() if bid not in BOSS_NAMES)
    if unknown_total or unknown_this_world:
        lines.append(f"{'(unknown bosses)':<30} {unknown_total:>8} {unknown_this_world:>8}")
    lines.append(f"{'-' * 30} {'-' * 8} {'-' * 8}")
    lines.append(f"{'TOTAL':<30} {grand_total:>8} {grand_this_world:>8}")
    lines.append("```")

    footer_bits = [
        f"{world_label} detail JSONs on disk: **{this_world_detail_count}**",
        f"Local raid_history.json cache for {world_label}: **{local_count}**",
    ]
    lines.append(" • ".join(footer_bits))

    if not counts_total:
        lines.append(
            f"\n*Note: traverser index unavailable — Total/{col_label} columns are 0. "
            "See `$bosspollstatus` for the diagnostic.*"
        )

    await ctx.send("\n".join(lines))


# ─── Per-server setup commands ────────────────────────────────────────────
# These commands have NO guild_ids restriction so they work in any server the
# bot is invited to. Each gates with is_server_setup_authorized so only admins
# or the configured setup_role can change settings.

@client.command(aliases=['setceltichero', 'setworldid', 'setceltherosserver'])
async def setworld(ctx, *, world_token: str = None):
    """Configure this Discord server to track a Celtic Heroes world for the boss
    leaderboard. Accepts either a numeric world ID or a known world name.

    Examples:
        $setworld 15
        $setworld gwydion
        $setworld Epona

    Run `$listworlds` to see which names are recognised. Requires Discord
    administrator OR a 'Winston Admin' / 'REDALiCE' role OR (if previously set)
    this server's configured setup_role."""
    if ctx.guild is None:
        await ctx.send("This command can't be used in DMs.")
        return
    if world_token is None or not str(world_token).strip():
        await ctx.send("Usage: `$setworld <world_id_or_name>` — e.g. `$setworld 15` or `$setworld gwydion`.")
        return
    entry = get_server_entry(ctx.guild.id)
    if not is_server_setup_authorized(ctx.author, entry):
        await ctx.send("You don't have permission to configure this server.")
        return
    wid, canon = resolve_world(world_token)
    if wid is None or wid <= 0:
        known = ", ".join(sorted(CH_WORLDS.keys())) or "(none seeded yet)"
        await ctx.send(
            f"Couldn't resolve `{world_token}` to a world. Pass a positive integer "
            f"or one of the known names: {known}. Run `$listworlds` for the full list."
        )
        return
    set_server_entry(ctx.guild.id, world_id=wid)
    try:
        initialize_posted_fights_if_needed(world_id=wid)
    except Exception:
        logger.exception(f"Could not seed posted_fights for world {wid}")
    display = display_world(wid)
    await ctx.send(
        f"Server configured for **{display}** (world `{wid}`). "
        f"Use `$setchannel #channel` to enable auto-posting of boss kills, or "
        f"`$lbhelp` to see available commands."
    )


@client.command(aliases=['setbosschannel', 'setautopost', 'setleaderboardchannel'])
async def setchannel(ctx, channel: discord.TextChannel = None):
    """Set the channel where boss-kill damage charts are auto-posted.
    With no argument, defaults to the channel where this command was run.
    Use `$setchanneloff` to disable auto-posting."""
    if ctx.guild is None:
        await ctx.send("This command can't be used in DMs.")
        return
    entry = get_server_entry(ctx.guild.id)
    if not is_server_setup_authorized(ctx.author, entry):
        await ctx.send("You don't have permission to configure this server.")
        return
    if not entry or not entry.get("world_id"):
        if is_gwydion_guild(ctx.guild.id):
            # Gwydion guilds always implicitly have world 15; allow setchannel
            # to seed an entry on their behalf.
            entry = set_server_entry(ctx.guild.id, world_id=GWYDION_WORLD_ID)
        else:
            await ctx.send("Configure a world first with `$setworld <world_id_or_name>`.")
            return
    if channel is None:
        channel = ctx.channel
    set_server_entry(ctx.guild.id, channel_id=channel.id)
    await ctx.send(f"Auto-post channel set to {channel.mention}.")


@client.command(aliases=['unsetchannel', 'disableautopost'])
async def setchanneloff(ctx):
    """Disable boss-kill auto-posting in this server (clears the channel)."""
    if ctx.guild is None:
        await ctx.send("This command can't be used in DMs.")
        return
    entry = get_server_entry(ctx.guild.id)
    if not is_server_setup_authorized(ctx.author, entry):
        await ctx.send("You don't have permission to configure this server.")
        return
    if not entry:
        await ctx.send("This server has no leaderboard configuration to update.")
        return
    set_server_entry(ctx.guild.id, channel_id=0)
    await ctx.send("Auto-posting disabled. Query commands still work; "
                   "run `$setchannel #channel` to re-enable auto-posts.")


@client.command(aliases=['setadminrole', 'setbotrole'])
async def setsetuprole(ctx, *, role_name: str = None):
    """Set the role name allowed to run setup/admin commands for this server's
    leaderboard. Pass no argument or `off` to clear. Discord admins, 'Winston Admin',
    and 'REDALiCE' always retain access regardless of this setting."""
    if ctx.guild is None:
        await ctx.send("This command can't be used in DMs.")
        return
    entry = get_server_entry(ctx.guild.id)
    if not is_server_setup_authorized(ctx.author, entry):
        await ctx.send("You don't have permission to configure this server.")
        return
    if not entry:
        await ctx.send("Configure a world first with `$setworld <world_id_or_name>`.")
        return
    clean = (role_name or "").strip()
    if not clean or clean.lower() == "off":
        set_server_entry(ctx.guild.id, setup_role="")
        await ctx.send("Setup role cleared. Only Discord admins / Winston Admin / REDALiCE can configure now.")
        return
    set_server_entry(ctx.guild.id, setup_role=clean)
    await ctx.send(f"Setup role set to `{clean}`. Members with that role can now configure the leaderboard.")


@client.command(aliases=['leaderboardconfig', 'lbconfig'])
async def serverinfo(ctx):
    """Shows this server's leaderboard configuration."""
    if ctx.guild is None:
        await ctx.send("This command can't be used in DMs.")
        return
    entry = get_server_entry(ctx.guild.id)
    # Synthesize a virtual entry for Gwydion guilds even before $setworld runs
    if not entry and is_gwydion_guild(ctx.guild.id):
        entry = {
            "world_id": GWYDION_WORLD_ID,
            "channel_id": GWYDION_AUTO_POST_CHANNEL_ID,
            "setup_role": None,
            "added_at": "(default — Gwydion legacy guild)",
        }
    if not entry:
        await ctx.send(
            "This server has no leaderboard configuration yet. "
            "An admin can run `$setworld <world_id_or_name>` to set it up. "
            "Run `$lbhelp` to see all available leaderboard commands, or "
            "`$listworlds` for known world names."
        )
        return
    wid = entry.get("world_id")
    cid = entry.get("channel_id")
    role = entry.get("setup_role") or "(none — only Discord admins / Winston Admin / REDALiCE)"
    channel_str = f"<#{cid}>" if cid else "(none — auto-posting disabled)"
    posted_count = len(await sheet_call(load_posted_fights, wid)) if wid else 0
    history_count = len(await sheet_call(load_raid_history, wid)) if wid else 0
    lines = [
        f"**Leaderboard Configuration for {ctx.guild.name}**",
        f"World: **{display_world(wid)}** (id `{wid}`)",
        f"Auto-post channel: {channel_str}",
        f"Setup role: `{role}`",
        f"Posted fights tracked: `{posted_count}`",
        f"Local raid records: `{history_count}`",
    ]
    await ctx.send("\n".join(lines))


@client.command(aliases=['worldlist', 'worlds'])
async def listworlds(ctx):
    """Lists known Celtic Heroes world names recognised by `$setworld`."""
    if not CH_WORLDS:
        await ctx.send(
            "No world names are seeded yet — `$setworld` only accepts numeric IDs. "
            "Bot owner can add entries to CH_WORLDS in the source."
        )
        return
    lines = ["**Known Celtic Heroes world names** (use with `$setworld`):", "```"]
    pad = max(len(name) for name in CH_WORLDS) + 2
    for name in sorted(CH_WORLDS):
        lines.append(f"{name.ljust(pad)} {CH_WORLDS[name]}")
    lines.append("```")
    lines.append("Names are case-insensitive and spaces/apostrophes are ignored.")
    lines.append("Numeric IDs also work: `$setworld 15`.")
    await ctx.send("\n".join(lines))


@client.command(aliases=['clearserver', 'forgetserver'])
async def resetserver(ctx):
    """Clear this server's leaderboard configuration. Does NOT delete the world's
    shared posted_fights / raid_history data — those may be in use by other guilds
    on the same world."""
    if ctx.guild is None:
        await ctx.send("This command can't be used in DMs.")
        return
    entry = get_server_entry(ctx.guild.id)
    if not is_server_setup_authorized(ctx.author, entry):
        await ctx.send("You don't have permission to configure this server.")
        return
    if remove_server_entry(ctx.guild.id):
        await ctx.send(
            "Server configuration cleared. Auto-posting stopped. Query commands "
            "will prompt for `$setworld` again."
        )
    else:
        await ctx.send("No configuration to clear.")


print("Starting bot")

client.run(TOKEN)