# Teardown — Challenger Auto Valuation Site

## What's here
- `companies.json` — your curated coverage (Rivian, Lucid, Polestar, NIO). **Assumptions in here are placeholders** — replace `base_revenue_musd`, `net_debt_musd`, `shares_out_musd` with real numbers from each company's latest 10-Q/10-K, and replace every `thesis` field with your actual 2-4 sentence view (why growth/margins do what you assumed).
- `dcf_engine.py` — the mechanics only. Takes assumptions in, produces enterprise value / equity value / value per share / sensitivity table out. Never invents an assumption.
- `weekly_picks.py` — draws 3 tickers from a fixed challenger-auto watchlist and fills flat consensus-style defaults, clearly flagged `ai_default`. Produces `ai_picks.json`. Run its own DCF pass separately, or graduate a pick into `companies.json` once you've written a real thesis for it.
- `generate_site.py` — renders `results.json` into `index.html`. No framework, no build step.
- `index.html` — the current rendered site (built from the placeholder data — regenerate after you edit `companies.json`).

## Workflow
```
# 1. Edit companies.json: real financials + your thesis
# 2. Run the DCF
python3 dcf_engine.py companies.json      # -> results.json

# 3. (optional) generate this week's AI picks
python3 weekly_picks.py                    # -> ai_picks.json
python3 dcf_engine.py ai_picks.json         # -> overwrites results.json — merge manually if you want both curated + AI picks in one build

# 4. Build the site
python3 generate_site.py                   # -> index.html
```

## Deploying
Cheapest path: push this folder to a GitHub repo, enable **GitHub Pages** on it (Settings → Pages → deploy from branch), done — free hosting. Point a custom domain ($10–15/yr from Namecheap/Porkbun) at it later if you want firstname-lastname.com instead of a github.io URL.

## Data note
This environment has no live market-data access, so `companies.json` ships with rough placeholder financials (clearly marked `_note`) — treat every number as illustrative until you swap in real 10-Q/10-K figures. On your own machine, `yfinance` (`pip install yfinance`) is the easiest way to pull `base_revenue_musd`, `net_debt_musd`, and `shares_out_musd` automatically — happy to wire that in if you want the fetch automated too.

## The honesty line this is built around
Every card on the site shows a flag: **"Your thesis"** (cyan) or **"AI default — needs your review"** (amber). That's not decorative — it's the thing that makes this defensible in an interview. If you can't look at a card and say exactly which numbers are yours and why, fix that before it goes live.

## Auto-pulling financials (fetch_financials.py)

Pulls revenue, net debt, and shares outstanding straight from SEC EDGAR — free, public, no login. Works for any US-listed ticker.

1. Open `fetch_financials.py`, find `YOUR_EMAIL = "your_email@example.com"` near the top, put your real email in. (SEC requires this in every request — it's how they identify who's calling their API. It's not sent anywhere else.)
2. Run:
   ```
   python3 fetch_financials.py RIVN LCID PSNY NIO
   ```
3. It prints what it found and automatically updates `base_revenue_musd`, `net_debt_musd`, and `shares_out_musd` in `companies.json` — your `thesis` and growth/margin/WACC assumptions are left untouched.
4. `current_price` isn't in SEC filings (they're not updated daily) — grab that one number manually from Google Finance.
5. Then run the usual pipeline: `dcf_engine.py` → `generate_site.py`.

Works for any ticker, not just your 4 curated names — this is also what `weekly_picks.py` should eventually call to fill in real numbers instead of placeholders (currently a manual step; say the word if you want them wired together).
