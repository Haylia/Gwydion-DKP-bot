"""Pure bid-resolution logic for the standalone Gwydion bid tool.

No Discord, no gspread, no Tkinter — just data in, winners out. This is the
piece that decides who wins each item, so it is the piece that gets unit tests
(see test_bid_resolver.py). The GUI, the live-sheet reader and the gear-rules /
history layers sit on top of it.

Resolution model
================
For each item, bids are sorted highest-first and each candidate is run through a
chain of GATES. A bid that fails a gate is hard-blocked and the next bidder is
promoted. The gates (in order):

  * affordability  — bid > bidder's Current KP in that pool
  * level          — bidder level < the item's required level
  * RBPP %         — bidder's 30-day RBPP % < the item's required %
  * lifetime RBPP  — bidder's RBPP Earned < the item's required points
  * weekly cap     — bidder already won `cap` items in this pool (rolling 7 days)

The top `qty` survivors each win one copy and each pays their own bid. An exact
tie for a winning slot is FLAGGED for a manual roll (never auto-broken).

Two things are FLAGGED, not blocked:
  * main/alt       — an alt wins while a main also bid on the same item
  * KP overrun     — a bidder's combined wins in a pool exceed their balance

The named bidder always pays (a "for <recipient>" bid is paid by the bidder,
exactly like the bot's $sendbid / $deduct); the recipient only rides along to the
output line and is NOT used for gates or the cap.

Inputs
======
`lookup(pool, name)` (optional) returns a dict describing the toon, or None /
{"canonical": None,...} when the name is unknown:
    {
      "canonical":   real roster name, or None if unknown
      "suggestions": [near-miss names]            (when canonical is None)
      "balance":     Current KP in `pool`, or None if no row in that pool
      "level":       roster level (int) or None
      "is_main":     True/False/None
      "main_name":   the player's main toon name (str) or None
      "rbpp_pct":    30-day RBPP as a FRACTION (0.15 == 15%) or None
      "rbpp_earned": lifetime RBPP points (float) or None
    }
Pass lookup=None to resolve "offline": only amount/qty/tie are applied, no gates.

`rules` is a GearRules instance (gear_rules.py) or None (no item requirements).
`week_counts` is {(bidder_lower, POOL): prior_count}; pass it to enable the
weekly cap, omit/None to disable it.
"""

from collections import defaultdict

WEEKLY_CAP_DEFAULT = 4


def _norm_amount(value):
    try:
        return int(round(float(str(value).strip())))
    except (TypeError, ValueError):
        raise ValueError(f"bad bid amount: {value!r}")


def _item_key(item):
    return " ".join(str(item).split()).lower()


def _fmt_num(n):
    try:
        f = float(n)
    except (TypeError, ValueError):
        return str(n)
    return str(int(f)) if f == int(f) else str(f)


def _fmt_pct(frac):
    """0.155 -> '16%' (rounded). None -> '?'."""
    if frac is None:
        return "?"
    return f"{round(frac * 100)}%"


def resolve_bids(bids, lookup=None, rules=None, week_counts=None, cap_limit=None):
    warnings = []
    cap_enabled = week_counts is not None
    cap_limit = cap_limit if cap_limit is not None else (
        rules.weekly_cap if rules is not None else WEEKLY_CAP_DEFAULT
    )
    cap_counter = defaultdict(int)
    if week_counts:
        for (nm, pool), cnt in week_counts.items():
            cap_counter[(nm.lower(), pool.upper())] = cnt

    _cache = {}

    def info_for(pool, name):
        if lookup is None:
            return None
        key = (pool.upper(), name.strip().lower())
        if key not in _cache:
            _cache[key] = lookup(pool, name)
        return _cache[key]

    # ── Group bids by item, preserving first-seen order ─────────────────────
    order, groups, meta = [], {}, {}
    for raw in bids:
        item = str(raw.get("item", "")).strip()
        bidder = str(raw.get("bidder", "")).strip()
        if not item or not bidder:
            continue
        pool = str(raw.get("kp", "")).strip().upper()
        try:
            qty = max(1, int(raw.get("qty", 1) or 1))
        except (TypeError, ValueError):
            qty = 1
        for_player = str(raw.get("for_player", "") or "").strip()
        try:
            amount = _norm_amount(raw.get("amount"))
        except ValueError as e:
            warnings.append(f"Skipped bid on {item!r}: {e}")
            continue

        key = _item_key(item)
        if key not in groups:
            order.append(key)
            groups[key] = []
            override = {
                "min_level": raw.get("min_level"),
                "min_rbpp_pct": raw.get("min_rbpp_pct"),
                "min_rbpp_earned": raw.get("min_rbpp_earned"),
                "is_helm": raw.get("is_helm"),
            }
            req = rules.requirements_for(item, pool, override) if rules else None
            meta[key] = {"item": item, "kp": pool, "qty": qty, "req": req}
        else:
            m = meta[key]
            if m["kp"] != pool:
                warnings.append(f"{item!r} has mixed KP pools ({m['kp']} vs {pool}); using {m['kp']}.")
            if m["qty"] != qty:
                warnings.append(f"{item!r} has mixed quantities ({m['qty']} vs {qty}); using {m['qty']}.")

        info = info_for(meta[key]["kp"], bidder)
        groups[key].append({
            "bidder": bidder, "for_player": for_player, "amount": amount, "info": info,
        })

    # ── First pass: validity + static gates, per item ───────────────────────
    # We resolve items in descending order of their top bid so that when the
    # weekly cap forces a bidder to give something up, they keep their most
    # expensive win. Results are rendered back in input order afterwards.
    prepared = {}
    for key in order:
        m = meta[key]
        pool, req = m["kp"], m["req"]
        invalid, valid = [], []
        for b in groups[key]:
            info = b["info"]
            if lookup is not None:
                if not info or info.get("canonical") is None:
                    reason = "unknown player"
                    sugg = (info or {}).get("suggestions") or []
                    if sugg:
                        reason += " (did you mean: " + ", ".join(sugg) + "?)"
                    invalid.append({"bidder": b["bidder"], "amount": b["amount"], "reason": reason})
                    continue
                if info.get("balance") is None:
                    invalid.append({"bidder": info["canonical"], "amount": b["amount"],
                                    "reason": f"no {pool} record"})
                    continue
            valid.append(b)
        valid.sort(key=lambda x: x["amount"], reverse=True)

        # Static gates (order-independent): affordability, level, RBPP %, lifetime.
        passed, blocked = [], []
        for b in valid:
            reason = _static_gate(b["info"], req, pool, b["amount"], lookup)
            if reason:
                who = (b["info"] or {}).get("canonical") or b["bidder"]
                blocked.append({"bidder": who, "amount": b["amount"], "reason": reason})
            else:
                passed.append(b)
        prepared[key] = {"passed": passed, "blocked": blocked, "invalid": invalid}

    process_order = sorted(
        order,
        key=lambda k: prepared[k]["passed"][0]["amount"] if prepared[k]["passed"] else -1,
        reverse=True,
    )

    # ── Second pass: cap gate + qty + tie, awarding in process_order ────────
    results_by_key = {}
    pool_commit = defaultdict(list)   # (name_lower, pool) -> [(key, amount)]
    pool_balance = {}                 # (name_lower, pool) -> balance
    pool_display = {}                 # (name_lower, pool) -> display name

    for key in process_order:
        m = meta[key]
        pool, qty, req = m["kp"], m["qty"], m["req"]
        prep = prepared[key]
        passed, blocked, invalid = list(prep["passed"]), list(prep["blocked"]), prep["invalid"]

        # Pick winners by walking the gate-passing list, applying the rolling
        # weekly cap live; a capped bidder is blocked and the next is promoted.
        winners, tied, open_slots, losers = _select_with_cap(
            passed, qty, pool, cap_enabled, cap_counter, cap_limit, blocked
        )

        status = "resolved"
        if not (winners or tied):
            status = "no_valid_bids"
        elif tied:
            status = "tie"

        result = {
            "item": m["item"], "kp": pool, "qty": qty, "req": req,
            "status": status,
            "winners": [_winrow(b) for b in winners],
            "tied": [_winrow(b) for b in tied],
            "open_slots": open_slots,
            "blocked": blocked, "invalid": invalid,
            "losers": [{"bidder": _name(b), "amount": b["amount"]} for b in losers],
            "flags": [],
        }

        # Commit clear winners for the cumulative-overrun check.
        for b in winners:
            nm = _name(b).lower()
            pool_commit[(nm, pool)].append((key, b["amount"]))
            pool_display[(nm, pool)] = _name(b)
            if b["info"] and b["info"].get("balance") is not None:
                pool_balance[(nm, pool)] = b["info"]["balance"]

        # main/alt FLAG (all items): an alt won while a main also bid here.
        if lookup is not None and winners:
            mains_bid = [b for b in groups[key]
                         if b["info"] and b["info"].get("is_main")]
            for w in winners:
                if w["info"] and w["info"].get("is_main") is False and mains_bid:
                    main_names = sorted({b["info"]["canonical"] for b in mains_bid})
                    result["flags"].append(
                        f"alt {_name(w)} won over main(s) who bid: {', '.join(main_names)}"
                    )
                    break

        results_by_key[key] = result

    # ── Third pass: cumulative KP overrun FLAG (per bidder per pool) ─────────
    if lookup is not None:
        for (nm, pool), commits in pool_commit.items():
            balance = pool_balance.get((nm, pool))
            if balance is None:
                continue
            total = sum(amt for _k, amt in commits)
            if total > balance:
                for item_key, _amt in commits:
                    results_by_key[item_key]["flags"].append(
                        f"OVERRUN: {pool_display.get((nm, pool), nm)} won "
                        f"{_fmt_num(total)} {pool} total but only has {_fmt_num(balance)}"
                    )

    return {"items": [results_by_key[k] for k in order], "warnings": warnings}


# ── Gate helpers ────────────────────────────────────────────────────────────
def _static_gate(info, req, pool, amount, lookup):
    """Return a block reason string, or None if the bid passes the static gates.
    Each gate is skipped when the data needed to judge it is absent."""
    if lookup is None or not info:
        return None
    bal = info.get("balance")
    if bal is not None and amount > bal:
        return f"can't afford — only has {_fmt_num(bal)} {pool}"
    if req:
        lvl_req = req.get("min_level")
        if lvl_req and info.get("level") is not None and info["level"] < lvl_req:
            return f"level {info['level']} < {int(lvl_req)} required"
        pct_req = req.get("min_rbpp_pct")
        if pct_req and info.get("rbpp_pct") is not None and info["rbpp_pct"] < pct_req / 100.0:
            return f"RBPP {_fmt_pct(info['rbpp_pct'])} < {int(pct_req)}% required"
        earn_req = req.get("min_rbpp_earned")
        if earn_req and info.get("rbpp_earned") is not None and info["rbpp_earned"] < earn_req:
            return (f"lifetime RBPP {_fmt_num(info['rbpp_earned'])} "
                    f"< {int(earn_req)} required")
    return None


def _select_with_cap(passed, qty, pool, cap_enabled, cap_counter, cap_limit, blocked):
    """Choose up to `qty` winners from the gate-passing list, applying the weekly
    cap live and detecting an exact tie at the cutoff.

    Returns (winners, tied, open_slots, losers). Increments cap_counter for each
    awarded winner and appends cap blocks to `blocked`.
    """
    # Apply the cap as a live gate first, so the "available" list already
    # excludes capped bidders; this keeps tie detection honest.
    available = []
    for b in passed:
        nm = _name(b).lower()
        if cap_enabled and cap_counter[(nm, pool)] + _pending(available, nm, pool) >= cap_limit:
            blocked.append({"bidder": _name(b), "amount": b["amount"],
                            "reason": f"weekly cap ({cap_limit}) reached in {pool}"})
            continue
        available.append(b)

    if not available:
        return [], [], 0, []

    if len(available) <= qty:
        winners, tied, open_slots, losers = available, [], 0, []
    else:
        boundary = available[qty - 1]["amount"]
        nxt = available[qty]["amount"]
        if boundary == nxt:
            clear = [b for b in available if b["amount"] > boundary]
            tied = [b for b in available if b["amount"] == boundary]
            losers = [b for b in available if b["amount"] < boundary]
            winners, open_slots = clear, qty - len(clear)
        else:
            winners, tied, open_slots = available[:qty], [], 0
            losers = available[qty:]

    for b in winners:
        cap_counter[(_name(b).lower(), pool)] += 1
    return winners, tied, open_slots, losers


def _pending(available, nm, pool):
    """How many already-awarded-this-item slots a bidder holds (rare: same bidder
    twice on one item)."""
    return sum(1 for b in available if _name(b).lower() == nm)


def _name(b):
    return (b["info"] or {}).get("canonical") or b["bidder"] if b.get("info") is not None else b["bidder"]


def _winrow(b):
    info = b.get("info") or {}
    return {
        "bidder": info.get("canonical") or b["bidder"],
        "for_player": b["for_player"],
        "amount": b["amount"],
        "info": b.get("info"),
    }


def collect_winners(resolved):
    """Flatten resolved output into winning lines for bid_history.commit_winners.
    Tied/blocked entries are excluded — only decided winners are recorded."""
    out = []
    for res in resolved["items"]:
        for w in res["winners"]:
            out.append({
                "bidder": w["bidder"], "kp": res["kp"], "item": res["item"],
                "amount": w["amount"], "for_player": w["for_player"],
            })
    return out


# ── Output formatting (the template-style block + flags) ────────────────────
def format_results(resolved):
    lines = []
    for res in resolved["items"]:
        item, kp = res["item"], res["kp"]

        if res["status"] == "no_valid_bids":
            lines.append(f"⚠ {item} ({kp}) — no eligible bids")
            _append_drops(lines, res)
            _append_unclassified(lines, res)
            lines.append("")
            continue

        for w in res["winners"]:
            who = f"{w['bidder']} for {w['for_player']}" if w["for_player"] else w["bidder"]
            lines.append(f"{who} - {item}")
            lines.append(f"({_fmt_num(w['amount'])} {kp})")

        if res["status"] == "tie":
            tied = ", ".join(f"{t['bidder']} ({_fmt_num(t['amount'])})" for t in res["tied"])
            slot = "slot" if res["open_slots"] == 1 else "slots"
            lines.append(f"⚠ TIE on {item} ({kp}) — manual roll for {res['open_slots']} "
                         f"{slot} between: {tied}")

        for flag in res["flags"]:
            lines.append(f"⚠ {flag}")

        _append_drops(lines, res)
        _append_unclassified(lines, res)
        lines.append("")

    for w in resolved["warnings"]:
        lines.append(f"⚠ {w}")

    return "\n".join(lines).rstrip() + "\n"


def _append_drops(lines, res):
    for d in res["blocked"]:
        lines.append(f"   ✗ {d['bidder']} bid {_fmt_num(d['amount'])} — blocked ({d['reason']})")
    for iv in res["invalid"]:
        lines.append(f"   ✗ {iv['bidder']} bid {_fmt_num(iv['amount'])} — {iv['reason']}")


def _append_unclassified(lines, res):
    """Note items the gear rules couldn't classify, so the council knows the tool
    applied no requirement gate to them."""
    req = res.get("req")
    if req is not None and not req.get("matched"):
        lines.append(f"   ℹ no gear rule matched {res['item']!r} — requirements not checked")
