"""Item-eligibility rules: turn an item name + KP pool into the requirements a
winner must meet (min level, min RBPP %, min lifetime RBPP, helm flag).

Rules live in gear_rules.json (seeded from the clan rules doc, user-editable).
When several rules match an item the STRICTEST wins — numeric requirements take
the max, is_helm is ORed, categories are collected. Per-item overrides entered
in the GUI/CSV take precedence over the matched rules.

Percentages are carried as whole numbers here (15 == 15%); the resolver converts
to a fraction when comparing against the sheet's attendance value.
"""

import json
import os


class GearRules:
    def __init__(self, rules, weekly_cap=4):
        self.rules = rules
        self.weekly_cap = weekly_cap

    @classmethod
    def load(cls, path=None):
        """Load rules from JSON. Defaults to gear_rules.json next to this file.
        A missing file yields an empty (no-requirement) rule set rather than an
        error, so the tool still runs."""
        if path is None:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gear_rules.json")
        if not os.path.isfile(path):
            return cls([], weekly_cap=4)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data.get("rules", []), weekly_cap=int(data.get("weekly_cap", 4)))

    def requirements_for(self, item_name, pool, override=None):
        """Resolve requirements for one item.

        Returns a dict:
          {min_level, min_rbpp_pct, min_rbpp_earned, is_helm,
           categories: [str], matched: [str]}
        Any numeric field is None when no rule/override sets it (= no gate).
        `override` may supply min_level / min_rbpp_pct / min_rbpp_earned / is_helm
        to force values regardless of the matched rules.
        """
        name_l = " ".join(str(item_name).split()).lower()
        pool_u = str(pool).upper()

        req = {
            "min_level": None, "min_rbpp_pct": None, "min_rbpp_earned": None,
            "is_helm": False, "categories": [], "matched": [],
        }

        for rule in self.rules:
            hit = False
            for kw in rule.get("match", []):
                if str(kw).lower() in name_l:
                    hit = True
                    break
            if not hit:
                for p in rule.get("match_pool", []):
                    if str(p).upper() == pool_u:
                        hit = True
                        break
            if not hit:
                continue

            req["matched"].append(rule.get("label", rule.get("match", rule.get("match_pool", "?"))))
            req["min_level"] = _max_opt(req["min_level"], rule.get("min_level"))
            req["min_rbpp_pct"] = _max_opt(req["min_rbpp_pct"], rule.get("min_rbpp_pct"))
            req["min_rbpp_earned"] = _max_opt(req["min_rbpp_earned"], rule.get("min_rbpp_earned"))
            if rule.get("is_helm"):
                req["is_helm"] = True
            cat = rule.get("category")
            if cat and cat not in req["categories"]:
                req["categories"].append(cat)

        # Per-item overrides win outright for whatever fields they specify.
        if override:
            for k in ("min_level", "min_rbpp_pct", "min_rbpp_earned"):
                v = override.get(k)
                if v not in (None, ""):
                    try:
                        req[k] = float(v) if k != "min_level" else int(float(v))
                    except (TypeError, ValueError):
                        pass
            if override.get("is_helm"):
                req["is_helm"] = True

        return req


def _max_opt(current, new):
    """max() that treats None as 'unset'."""
    if new in (None, ""):
        return current
    try:
        new = float(new)
    except (TypeError, ValueError):
        return current
    if current is None:
        return new
    return max(current, new)
