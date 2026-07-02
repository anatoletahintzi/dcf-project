"""
add_company.py

Adds a new company to companies.json automatically - no manual JSON
editing. Creates the entry with sensible default assumptions (which you
should still tune to your real view) and pulls real revenue/debt/shares/
price the same way fetch_financials.py does.

Usage:
    python3 add_company.py TSLA
    python3 add_company.py TSLA NIO XPEV        # multiple at once
"""

import sys
import json

DEFAULT_ASSUMPTIONS = {
    "revenue_growth": [0.15, 0.13, 0.11, 0.09, 0.07],
    "ebitda_margin": [0.05, 0.07, 0.09, 0.10, 0.11],
    "tax_rate": 0.21,
    "da_pct_revenue": 0.05,
    "capex_pct_revenue": 0.08,
    "nwc_pct_revenue_change": 0.04,
    "wacc": 0.11,
    "terminal_growth": 0.025,
}


def add_ticker(ticker, companies):
    from fetch_financials import fetch_company as _fetch_real

    ticker = ticker.upper()
    if any(c["ticker"] == ticker for c in companies):
        print(f"  {ticker} already in companies.json - skipped. Edit it directly if you want to change it.")
        return False

    entry = {
        "ticker": ticker,
        "name": ticker,
        "thesis": "REPLACE ME: your 2-4 sentence view. Why does growth/margin do what you assumed below? What's the market missing?",
        "thesis_author": "user",
        "current_price": None,
    }
    entry.update(DEFAULT_ASSUMPTIONS)

    try:
        real = _fetch_real(ticker)
        entry["name"] = real["name"]
        entry["base_revenue_musd"] = real["base_revenue_musd"]
        entry["net_debt_musd"] = real["net_debt_musd"]
        entry["shares_out_musd"] = real["shares_out_musd"]
        entry["current_price"] = real["current_price"]
        if real["base_revenue_musd"] is None:
            entry["_note"] = "No SEC data found - likely a foreign private issuer (20-F filer). Fill in financials manually."
        else:
            entry["_note"] = f"Financials auto-pulled from SEC EDGAR ({real['_source']['revenue_period_end']}) + Yahoo Finance."
    except Exception as e:
        entry["base_revenue_musd"] = None
        entry["net_debt_musd"] = None
        entry["shares_out_musd"] = None
        entry["_note"] = f"Auto-fetch failed ({e}) - fill in financials manually."

    companies.append(entry)
    print(f"  Added {ticker} ({entry['name']}). Revenue: {entry.get('base_revenue_musd')}, "
          f"Net debt: {entry.get('net_debt_musd')}, Shares: {entry.get('shares_out_musd')}, "
          f"Price: {entry.get('current_price')}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 add_company.py TICKER [TICKER2 ...]")
        sys.exit(1)

    path = "companies.json"
    try:
        with open(path) as f:
            companies = json.load(f)
    except FileNotFoundError:
        companies = []

    added_any = False
    for ticker in sys.argv[1:]:
        if add_ticker(ticker, companies):
            added_any = True

    if added_any:
        with open(path, "w") as f:
            json.dump(companies, f, indent=2)
        print(f"\nSaved {path}. Now go edit the thesis/growth/margin fields for your new companies, "
              f"then run dcf_engine.py and generate_site.py as usual.")
    else:
        print("\nNothing new to add.")


if __name__ == "__main__":
    main()
