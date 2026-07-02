# Teardown — Challenger Auto Valuation Site

Live site: https://anatoletahintzi.github.io/dcf-project/

## What's here
- `companies.json` — curated coverage (Rivian, Lucid, Polestar, NIO, Tesla, Ford, GM). Each entry has real financial inputs pulled from SEC filings, plus my own growth/margin/WACC assumptions and thesis.
- `fetch_financials.py` — pulls revenue, net debt, shares outstanding, and live price for any US-listed ticker automatically, straight from **SEC EDGAR** (financials) and **Yahoo Finance** (live price). No login, no API key, no manual lookup needed.
- `dcf_engine.py` — the DCF mechanics only (discounting, terminal value, sensitivity table). Never invents an assumption — everything it uses comes from `companies.json`.
- `weekly_picks.py` — draws tickers from a watchlist and fills flat consensus-style default assumptions, flagged `ai_default` until reviewed.
- `generate_site.py` — renders `results.json` into `index.html`.

## Workflow

Run these in order from a terminal, in the project folder:

    python3 fetch_financials.py RIVN LCID PSNY NIO TSLA F GM
    python3 dcf_engine.py companies.json
    python3 generate_site.py

Edit `companies.json` in between the first and second command to set your own growth/margin assumptions and write your thesis.

## Data sources
- Financial statements (revenue, debt, shares outstanding): **SEC EDGAR**, free public API, no key required.
- Live prices: **Yahoo Finance** public chart endpoint, free, no key required.
- Note: foreign private issuers that file Form 20-F instead of 10-K (e.g. Polestar) generally aren't available through SEC's structured data API — those get entered manually, clearly noted in `companies.json`.

## Deployment
Live on GitHub Pages, deployed from the `main` branch. Free custom domain support available if I want to add one later — just needs a purchased domain pointed at GitHub via DNS.

## The honesty line this is built around
Every card shows a flag: **"Your thesis"** (cyan) or **"AI default — needs your review"** (amber). If I can't defend exactly which numbers are mine and why, that card isn't ready to show anyone.

---
Anatole Tahintzi · USC Marshall, Class of 2029
