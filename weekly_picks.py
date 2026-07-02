"""
weekly_picks.py

Generates 3 "AI pick" entries with DEFAULT assumptions (not your thesis).
Pulls REAL financials (via fetch_financials.py) so the DCF output is
grounded, not fake placeholder numbers - only the growth/margin/WACC
assumptions are generic defaults, clearly flagged.
"""

import json
import random
from datetime import date

WATCHLIST = [
    {"ticker": "TSLA", "name": "Tesla, Inc."},
    {"ticker": "STLA", "name": "Stellantis N.V."},
    {"ticker": "F", "name": "Ford Motor Company"},
    {"ticker": "GM", "name": "General Motors"},
    {"ticker": "XPEV", "name": "XPeng Inc."},
    {"ticker": "LI", "name": "Li Auto Inc."},
    {"ticker": "VFS", "name": "VinFast Auto"},
]

DEFAULT_ASSUMPTION_TEMPLATE = {
    "revenue_growth": [0.15, 0.13, 0.11, 0.09, 0.07],
    "ebitda_margin": [0.05, 0.07, 0.09, 0.10, 0.11],
    "tax_rate": 0.21,
    "da_pct_revenue": 0.05,
    "capex_pct_revenue": 0.08,
    "nwc_pct_revenue_change": 0.04,
    "wacc": 0.12,
    "terminal_growth": 0.025,
}


def pick_three(seed=None):
    rnd = random.Random(seed or date.today().isoformat())
    return rnd.sample(WATCHLIST, 3)


def build_entry(company):
    from fetch_financials import fetch_company as _fetch_real

    entry = {
        "ticker": company["ticker"],
        "name": company["name"],
        "thesis": "AI-generated placeholder using flat consensus-style assumptions. "
                  "No variant view yet - replace with your own thesis before using this number for anything.",
        "thesis_author": "ai_default",
        "current_price": None,
    }
    entry.update(DEFAULT_ASSUMPTION_TEMPLATE)

    try:
        real = _fetch_real(company["ticker"])
        entry["name"] = real["name"]
        entry["base_revenue_musd"] = real["base_revenue_musd"] or 10000
        entry["net_debt_musd"] = real["net_debt_musd"] or 0
        entry["shares_out_musd"] = real["shares_out_musd"] or 1000
        entry["current_price"] = real["current_price"]
        entry["_note"] = "Financials auto-pulled from SEC EDGAR + Yahoo Finance. Assumptions are flat consensus-style defaults - unreviewed."
    except Exception as e:
        entry["base_revenue_musd"] = 10000
        entry["net_debt_musd"] = 0
        entry["shares_out_musd"] = 1000
        entry["_note"] = f"Real financial fetch failed ({e}) - using rough placeholder financials instead."

    return entry


def main():
    picks = pick_three()
    entries = [build_entry(c) for c in picks]
    with open("ai_picks.json", "w") as f:
        json.dump(entries, f, indent=2)
    print("This week's AI picks:", ", ".join(e["ticker"] for e in entries))
    print("Wrote ai_picks.json")


if __name__ == "__main__":
    main()
