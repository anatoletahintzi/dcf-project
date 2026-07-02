"""
fetch_financials.py

Type in a ticker, get back the raw inputs a DCF needs, pulled straight from
SEC EDGAR (the government's public filing database - same underlying data
FactSet/CapIQ repackage, just free and requires no login).

Handles foreign private issuers (20-F filers like Ferrari, Polestar) by
falling back to IFRS taxonomy tags and auto-converting non-USD currencies
using the historical FX rate from the actual filing date.

Usage:
    python3 fetch_financials.py RIVN
    python3 fetch_financials.py RIVN LCID PSNY NIO      # multiple at once

IMPORTANT: SEC requires every request to identify who's making it. Fill in
YOUR_EMAIL below before running.
"""

import sys
import json
import csv
import io
import ssl
import datetime
import urllib.request
import time

YOUR_NAME = "Anatole Tahintzi"
YOUR_EMAIL = "tahintzi@usc.edu"   # <-- put your real email here
HEADERS = {"User-Agent": f"{YOUR_NAME} {YOUR_EMAIL}"}

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]
# Foreign private issuers (20-F filers, e.g. Ferrari, Polestar) often use
# the IFRS taxonomy instead of us-gaap, with different tag names.
IFRS_REVENUE_TAGS = [
    "Revenue",
    "RevenueFromContractsWithCustomers",
]
CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
IFRS_CASH_TAGS = ["CashAndCashEquivalents"]
DEBT_TAGS_LONG = ["LongTermDebtNoncurrent", "LongTermDebt"]
DEBT_TAGS_CURRENT = ["LongTermDebtCurrent", "DebtCurrent"]
IFRS_DEBT_TAGS = ["Borrowings", "NoncurrentBorrowings", "CurrentBorrowings", "InterestBearingLoansAndBorrowings"]
SHARES_TAGS = [
    "CommonStockSharesOutstanding",
    "EntityCommonStockSharesOutstanding",
]
# Currencies we know how to auto-convert to USD (extend as needed)
CONVERTIBLE_UNITS = ["EUR", "GBP", "CNY", "USD"]


_UNVERIFIED_CTX = ssl.create_default_context()
_UNVERIFIED_CTX.check_hostname = False
_UNVERIFIED_CTX.verify_mode = ssl.CERT_NONE
_warned_ssl = False


def _urlopen_resilient(req):
    global _warned_ssl
    try:
        return urllib.request.urlopen(req)
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            if not _warned_ssl:
                print("  [warning] SSL certs missing - using unverified fallback.")
                _warned_ssl = True
            return urllib.request.urlopen(req, context=_UNVERIFIED_CTX)
        raise


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with _urlopen_resilient(req) as resp:
        return json.loads(resp.read().decode())


def fetch_price(ticker, verbose=True):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with _urlopen_resilient(req) as resp:
            data = json.loads(resp.read().decode())
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        if verbose:
            print(f"  [debug] Yahoo Finance regularMarketPrice: {price}")
        return float(price)
    except Exception as e:
        if verbose:
            print(f"  [debug] price fetch failed: {type(e).__name__}: {e}")
        return None


def get_cik_for_ticker(ticker):
    data = fetch_json(TICKER_MAP_URL)
    ticker = ticker.upper()
    for row in data.values():
        if row["ticker"] == ticker:
            return str(row["cik_str"]).zfill(10)
    raise ValueError(f"Ticker {ticker} not found in SEC's list.")


def latest_value(facts, tags, units=("USD",), taxonomy="us-gaap", max_age_days=550, require_annual=False):
    """Walk a list of possible XBRL tags AND a list of possible currencies,
    return the most recent value found for the first (tag, unit) combo that
    has DATA THAT'S ACTUALLY RECENT, plus which currency it was reported in."""
    today = datetime.date.today()
    for tag in tags:
        try:
            tag_units = facts["facts"][taxonomy][tag]["units"]
        except KeyError:
            continue
        for unit in units:
            entries = tag_units.get(unit)
            if not entries:
                continue
            pool = entries
            if require_annual:
                def is_annual(e):
                    if "start" not in e or "end" not in e:
                        return False
                    try:
                        start = datetime.date.fromisoformat(e["start"])
                        end = datetime.date.fromisoformat(e["end"])
                    except ValueError:
                        return False
                    return 350 <= (end - start).days <= 380
                pool = [e for e in entries if is_annual(e)]
            pool_sorted = sorted(pool, key=lambda e: e.get("end", ""), reverse=True)
            if not pool_sorted:
                continue
            best = pool_sorted[0]
            try:
                end_date = datetime.date.fromisoformat(best["end"])
            except (ValueError, KeyError):
                continue
            if (today - end_date).days > max_age_days:
                continue
            return best["val"], best["end"], f"{taxonomy}:{tag}", unit
    return None, None, None, None


def fetch_fx_rate(from_currency, to_currency="USD", as_of_date=None, verbose=True):
    """Gets an FX rate via Yahoo Finance. If as_of_date (YYYY-MM-DD) is
    given, pulls the historical rate from around that date (matching the
    filing period) instead of today's rate."""
    if from_currency == to_currency:
        return 1.0

    pair = f"{from_currency}{to_currency}=X"
    if as_of_date:
        target = datetime.date.fromisoformat(as_of_date)
        period1 = int(datetime.datetime.combine(target - datetime.timedelta(days=7), datetime.time()).timestamp())
        period2 = int(datetime.datetime.combine(target + datetime.timedelta(days=3), datetime.time()).timestamp())
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}?period1={period1}&period2={period2}&interval=1d"
    else:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with _urlopen_resilient(req) as resp:
            data = json.loads(resp.read().decode())
        result = data["chart"]["result"][0]
        if as_of_date:
            closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
            rate = closes[-1] if closes else result["meta"]["regularMarketPrice"]
        else:
            rate = result["meta"]["regularMarketPrice"]
        if verbose:
            when = f" (as of ~{as_of_date})" if as_of_date else " (live)"
            print(f"  [debug] FX {from_currency}->{to_currency}: {rate}{when}")
        return float(rate)
    except Exception as e:
        if verbose:
            print(f"  [debug] FX lookup failed for {pair}: {type(e).__name__}: {e}")
        return None


def fetch_company(ticker):
    print(f"\n--- {ticker} ---")
    cik = get_cik_for_ticker(ticker)
    facts = fetch_json(FACTS_URL.format(cik=cik))
    company_name = facts.get("entityName", ticker)

    rev, rev_date, rev_tag, rev_unit = latest_value(facts, REVENUE_TAGS, units=("USD",), require_annual=True)
    if rev is None:
        rev, rev_date, rev_tag, rev_unit = latest_value(
            facts, IFRS_REVENUE_TAGS, units=CONVERTIBLE_UNITS, taxonomy="ifrs-full", require_annual=True
        )

    cash, cash_date, _, cash_unit = latest_value(facts, CASH_TAGS, units=("USD",))
    if cash is None:
        cash, cash_date, _, cash_unit = latest_value(facts, IFRS_CASH_TAGS, units=CONVERTIBLE_UNITS, taxonomy="ifrs-full")

    debt_long, _, _, debt_long_unit = latest_value(facts, DEBT_TAGS_LONG, units=("USD",))
    debt_current, _, _, debt_current_unit = latest_value(facts, DEBT_TAGS_CURRENT, units=("USD",))
    if debt_long is None and debt_current is None:
        debt_long, _, _, debt_long_unit = latest_value(facts, IFRS_DEBT_TAGS, units=CONVERTIBLE_UNITS, taxonomy="ifrs-full")
        debt_current, debt_current_unit = 0, debt_long_unit

    shares, shares_date, shares_tag, _ = latest_value(facts, ["EntityCommonStockSharesOutstanding"], units=("shares",), taxonomy="dei")
    if shares is None:
        shares, shares_date, shares_tag, _ = latest_value(facts, SHARES_TAGS, units=("shares",))

    fx_notes = []
    if rev is not None and rev_unit and rev_unit != "USD":
        fx = fetch_fx_rate(rev_unit, "USD", as_of_date=rev_date)
        if fx:
            fx_notes.append(f"revenue converted {rev_unit}->USD @ {fx:.4f} (as of {rev_date})")
            rev = rev * fx
        else:
            rev = None

    if cash is not None and cash_unit and cash_unit != "USD":
        fx = fetch_fx_rate(cash_unit, "USD", as_of_date=cash_date)
        if fx:
            fx_notes.append(f"cash/debt converted {cash_unit}->USD @ {fx:.4f}")
            cash = cash * fx
        else:
            cash = None

    if debt_long is not None and debt_long_unit and debt_long_unit != "USD":
        fx = fetch_fx_rate(debt_long_unit, "USD", as_of_date=None)
        if fx:
            debt_long = debt_long * fx
            debt_current = (debt_current or 0) * fx
        else:
            debt_long = None

    total_debt = (debt_long or 0) + (debt_current or 0)
    net_debt = total_debt - (cash or 0) if (cash is not None or total_debt) else None
    price = fetch_price(ticker)

    result = {
        "ticker": ticker.upper(),
        "name": company_name,
        "base_revenue_musd": round(rev / 1_000_000, 1) if rev else None,
        "net_debt_musd": round(net_debt / 1_000_000, 1) if net_debt is not None else None,
        "shares_out_musd": round(shares / 1_000_000, 1) if shares else None,
        "current_price": price,
        "_source": {
            "revenue_tag": rev_tag,
            "revenue_period_end": rev_date,
            "shares_period_end": shares_date,
            "fx_conversions": fx_notes,
        },
    }

    print(f"  Name:              {company_name}")
    print(f"  Revenue ($M):      {result['base_revenue_musd']}  (as of {rev_date}, tag: {rev_tag}, original unit: {rev_unit})")
    print(f"  Net debt ($M):     {result['net_debt_musd']}")
    print(f"  Shares out (M):    {result['shares_out_musd']}  (as of {shares_date}, tag: {shares_tag})")
    if price is not None:
        print(f"  Current price:     ${price}  (live from Yahoo Finance)")
    else:
        print("  Current price:     not found automatically - enter that one manually in companies.json")
    if fx_notes:
        for note in fx_notes:
            print(f"  [fx] {note}")
    if rev is None and shares is None:
        print("  [note] No usable data found even after trying IFRS tags and multiple currencies.")
        print("         This filer's XBRL structure isn't covered yet - enter financials manually.")

    return result


def merge_into_companies_json(fetched, path="companies.json"):
    try:
        with open(path) as f:
            content = f.read()
        if not content.strip():
            raise ValueError("file is empty")
        companies = json.loads(content)
    except FileNotFoundError:
        print(f"\n{path} not found - printing results only.")
        return
    except (json.JSONDecodeError, ValueError):
        print(f"\n{path} is empty or not valid JSON - skipping auto-merge.")
        return

    by_ticker = {c["ticker"]: c for c in companies}
    updated = []
    for r in fetched:
        c = by_ticker.get(r["ticker"])
        if not c:
            print(f"  ({r['ticker']} not in {path}, skipped)")
            continue
        for field in ["base_revenue_musd", "net_debt_musd", "shares_out_musd", "current_price"]:
            if r[field] is not None:
                c[field] = r[field]
        c["_note"] = f"Auto-pulled from SEC EDGAR ({r['_source']['revenue_period_end']})."
        updated.append(r["ticker"])

    with open(path, "w") as f:
        json.dump(companies, f, indent=2)
    print(f"\nUpdated {', '.join(updated)} in {path}.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_financials.py TICKER [TICKER2 ...]")
        sys.exit(1)
    if "@" not in YOUR_EMAIL or "example.com" in YOUR_EMAIL:
        print("Edit fetch_financials.py - put your real email in YOUR_EMAIL.")
        sys.exit(1)
    tickers = sys.argv[1:]
    results = []
    for t in tickers:
        try:
            results.append(fetch_company(t))
        except Exception as e:
            print(f"  Failed on {t}: {e}")
        time.sleep(0.3)
    merge_into_companies_json(results)


if __name__ == "__main__":
    main()
