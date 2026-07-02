"""
fetch_financials.py
Pulls DCF inputs (revenue, debt, cash, shares, price) for any ticker from
SEC EDGAR + Yahoo Finance, no login needed.
"""

import sys
import json
import csv
import io
import ssl
import urllib.request
import time

YOUR_NAME = "Anatole Tahintzi"
YOUR_EMAIL = "tahintzi@usc.edu"   # <-- type your real email between the quotes
HEADERS = {"User-Agent": f"{YOUR_NAME} {YOUR_EMAIL}"}

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]
CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
DEBT_TAGS_LONG = ["LongTermDebtNoncurrent", "LongTermDebt"]
DEBT_TAGS_CURRENT = ["LongTermDebtCurrent", "DebtCurrent"]
SHARES_TAGS = [
    "CommonStockSharesOutstanding",
    "EntityCommonStockSharesOutstanding",
]

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
    """Pulls the live/most-recent market price from Yahoo Finance's public
    chart endpoint - free, no login, no API key."""
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


def latest_value(facts, tags, unit="USD", taxonomy="us-gaap", max_age_days=550, require_annual=False):
    """require_annual=True restricts to facts covering a ~full year
    (350-380 day span) - without this, revenue can grab a single
    quarter's figure just because it's the most recent."""
    import datetime
    today = datetime.date.today()
    for tag in tags:
        try:
            entries = facts["facts"][taxonomy][tag]["units"][unit]
        except KeyError:
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
        return best["val"], best["end"], f"{taxonomy}:{tag}"
    return None, None, None


def fetch_company(ticker):
    print(f"\n--- {ticker} ---")
    cik = get_cik_for_ticker(ticker)
    facts = fetch_json(FACTS_URL.format(cik=cik))
    company_name = facts.get("entityName", ticker)

    rev, rev_date, rev_tag = latest_value(facts, REVENUE_TAGS, require_annual=True)
    cash, cash_date, _ = latest_value(facts, CASH_TAGS)
    debt_long, _, _ = latest_value(facts, DEBT_TAGS_LONG)
    debt_current, _, _ = latest_value(facts, DEBT_TAGS_CURRENT)

    shares, shares_date, shares_tag = latest_value(facts, ["EntityCommonStockSharesOutstanding"], unit="shares", taxonomy="dei")
    if shares is None:
        shares, shares_date, shares_tag = latest_value(facts, SHARES_TAGS, unit="shares")

    total_debt = (debt_long or 0) + (debt_current or 0)
    net_debt = total_debt - (cash or 0)
    price = fetch_price(ticker)

    result = {
        "ticker": ticker.upper(),
        "name": company_name,
        "base_revenue_musd": round(rev / 1_000_000, 1) if rev else None,
        "net_debt_musd": round(net_debt / 1_000_000, 1) if (cash or total_debt) else None,
        "shares_out_musd": round(shares / 1_000_000, 1) if shares else None,
        "current_price": price,
        "_source": {"revenue_tag": rev_tag, "revenue_period_end": rev_date, "shares_period_end": shares_date},
    }

    print(f"  Name:              {company_name}")
    print(f"  Revenue ($M):      {result['base_revenue_musd']}  (as of {rev_date}, tag: {rev_tag})")
    print(f"  Net debt ($M):     {result['net_debt_musd']}")
    print(f"  Shares out (M):    {result['shares_out_musd']}  (as of {shares_date}, tag: {shares_tag})")
    if price is not None:
        print(f"  Current price:     ${price}  (live from Yahoo Finance)")
    else:
        print("  Current price:     not found automatically - enter manually")
    if rev is None and shares is None:
        print("  [note] No data - likely a foreign private issuer (20-F filer, e.g. Polestar).")

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
        print(f"Results were still printed above. Fix {path} and re-run.")
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
    if "@" not in YOUR_EMAIL or "PUT_YOUR_EMAIL_HERE" in YOUR_EMAIL:
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