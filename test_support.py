"""Shared test harness for the Gwydion DKP bot (test-only, never deployed).

The bot is a single file (host requirement) that opens Google Sheets at import
time, so it can't be imported in a test. Instead we `ast.parse` the source — which
parses but does NOT execute it — and lift the exact source of individual top-level
functions / constant assignments, then exec just those into a controlled namespace.
Tests therefore run against the *actual shipped source* with zero drift and no
credentials.

Usage:
    from test_support import load
    ns = load(["safe_float", "safe_int"])
    assert ns["safe_float"]("50%") == 50.0

`load(names, **inject)` pulls each named function/assignment from the bot source (in
file order, so intra-file dependencies resolve) and execs them with a namespace
seeded by BASE_NS plus any `inject`ed values (fixtures, or globals you want to
override such as a file path). Raises LookupError if a requested name no longer
exists in the source — a cheap guard against silent drift when the bot is
refactored.
"""

import ast
import os
import re
import json
import math
import difflib
from datetime import datetime as dt, timedelta, timezone, time as dtime, date  # noqa: F401

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gwydion dkp.py")
with open(SRC, "r", encoding="utf-8") as _f:
    SOURCE = _f.read()
TREE = ast.parse(SOURCE)

# Stdlib names / aliases the bot file has in scope at module level, so extracted
# functions that reference them resolve.
BASE_NS = {
    "re": re, "os": os, "json": json, "math": math, "difflib": difflib,
    "dt": dt, "timedelta": timedelta, "timezone": timezone, "dtime": dtime,
}


def load(names, **inject):
    """Exec the named top-level functions/constants into a fresh namespace.

    `inject` supplies fixtures or overrides any global (e.g. a temp file path).
    """
    want = list(names)
    found = set()
    pieces = []
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name in want:
            pieces.append(ast.get_source_segment(SOURCE, node))
            found.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in want:
                    pieces.append(ast.get_source_segment(SOURCE, node))
                    found.add(t.id)
    missing = [n for n in want if n not in found and n not in inject]
    if missing:
        raise LookupError(f"names not found in '{os.path.basename(SRC)}': {missing}")
    ns = dict(BASE_NS)
    ns.update(inject)
    exec(compile("\n\n".join(pieces), SRC, "exec"), ns)
    return ns
