"""
weekly_picks.py

Generates 3 "AI pick" entries with DEFAULT assumptions (not your thesis).
These get merged into the site clearly flagged as "AI default - unreviewed"
until you edit them in companies.json (moving them from ai_picks.json into
your curated file, with your own thesis and assumptions).

This is deliberately dumb about picking: it draws from a fixed watchlist
pool rather than "whatever's trending," so the picks stay in the same
challenger-auto lane as your curated names instead of turning into a
random ticker-of-the-week grab bag.

In your own environment (with network access) you'd wire base_revenue,
net_debt, shares_out here from a real data source (yfinance, a broker API,
etc). This script ships with the same placeholder-financials pattern as
companies.json - replace before trusting any output.
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
    {"ticker": "FSR_LEGACY", "name": "(retired - do not use, Fisker delisted)"},
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
    pool = [c for c in WATCHLIST if "retired" not in c["name"]]
    rnd = random.Random(seed or date.today().isoformat())
    return rnd.sample(pool, 3)


def build_entry(company):
    entry = {
        "ticker": company["ticker"],
        "name": company["name"],
        "thesis": "AI-generated placeholder using flat consensus-style assumptions. "
                  "No variant view yet - replace with your own thesis before using this number for anything.",
        "thesis_author": "ai_default",
        "base_revenue_musd": 10000,   # placeholder - replace with real trailing revenue
        "net_debt_musd": 0,           # placeholder
        "shares_out_musd": 1000,      # placeholder
        "current_price": None,
    }
    entry.update(DEFAULT_ASSUMPTION_TEMPLATE)
    entry["_note"] = "FULLY PLACEHOLDER - this ticker was auto-picked and has no real financials wired in yet."
    return entry


def main():
    picks = pick_three()
    entries = [build_entry(c) for c in picks]
    with open("ai_picks.json", "w") as f:
        json.dump(entries, f, indent=2)
    print("This week's AI picks:", ", ".join(e["ticker"] for e in entries))
    print("Wrote ai_picks.json - run dcf_engine.py against it separately,")
    print("or merge into companies.json once you've added a real thesis + real financials.")


if __name__ == "__main__":
    main()
