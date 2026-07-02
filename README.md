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
