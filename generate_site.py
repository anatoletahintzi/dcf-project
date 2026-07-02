import json

PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Teardown &mdash; Challenger Auto Valuations</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Barlow+Condensed:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  :root { --bg: #0B1B22; --bg-panel: #0F2530; --line: #1E3D49; --cyan: #5EEAD4; --amber: #F5A623; --text: #DCEBEE; --text-dim: #7FA3AC; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); background-image: linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px); background-size: 48px 48px; background-attachment: fixed; color: var(--text); font-family: 'Space Mono', monospace; line-height: 1.5; }
  h1, h2, h3 { font-family: 'Barlow Condensed', sans-serif; text-transform: uppercase; letter-spacing: 0.03em; }
  header { padding: 64px 24px 40px; max-width: 1000px; margin: 0 auto; border-bottom: 1px solid var(--line); }
  header .eyebrow { color: var(--cyan); font-size: 13px; letter-spacing: 0.15em; margin-bottom: 12px; }
  header h1 { font-size: 56px; font-weight: 700; margin: 0 0 12px; color: var(--text); }
  header p { color: var(--text-dim); max-width: 620px; font-size: 15px; }
  main { max-width: 1000px; margin: 0 auto; padding: 40px 24px 100px; }
  .card { background: var(--bg-panel); border: 1px solid var(--line); border-radius: 2px; margin-bottom: 32px; }
  .card-head { display: flex; justify-content: space-between; align-items: baseline; padding: 24px 28px 16px; border-bottom: 1px solid var(--line); }
  .ticker-block .ticker { font-size: 32px; font-family: 'Barlow Condensed', sans-serif; font-weight: 700; color: var(--cyan); }
  .ticker-block .name { color: var(--text-dim); font-size: 13px; }
  .fair-value { text-align: right; }
  .fair-value .label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.1em; }
  .fair-value .num { font-size: 28px; font-family: 'Barlow Condensed', sans-serif; font-weight: 700; }
  .flag { display: inline-block; font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; padding: 3px 8px; border-radius: 2px; margin-top: 6px; }
  .flag.ai { background: rgba(245, 166, 35, 0.12); color: var(--amber); border: 1px solid rgba(245, 166, 35, 0.4); }
  .flag.user { background: rgba(94, 234, 212, 0.1); color: var(--cyan); border: 1px solid rgba(94, 234, 212, 0.35); }
  .thesis { padding: 20px 28px; font-size: 14px; border-bottom: 1px solid var(--line); background: rgba(0,0,0,0.15); }
  .thesis.placeholder { color: var(--text-dim); font-style: italic; }
  .grid-row { display: grid; grid-template-columns: 1fr 1fr 1fr; padding: 20px 28px; gap: 24px; border-bottom: 1px solid var(--line); }
  .stat .label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }
  .stat .val { font-size: 15px; }
  .sens-wrap { padding: 20px 28px; }
  .sens-title { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; }
  table { border-collapse: collapse; font-size: 12px; width: 100%; }
  th, td { border: 1px solid var(--line); padding: 6px 10px; text-align: center; }
  th { color: var(--cyan); font-weight: 400; }
  td.center-cell { color: var(--amber); font-weight: 700; }
  section.section-label { font-size: 12px; color: var(--text-dim); letter-spacing: 0.15em; text-transform: uppercase; margin: 56px 0 20px; display: flex; align-items: center; gap: 12px; }
  section.section-label::after { content: ''; flex: 1; height: 1px; background: var(--line); }
  footer { max-width: 1000px; margin: 0 auto; padding: 24px; color: var(--text-dim); font-size: 12px; border-top: 1px solid var(--line); }
</style>
</head>
<body>
<header>
  <div class="eyebrow">// TEARDOWN &mdash; VALUATION LOGS</div>
  <h1>Challenger Auto, Priced.</h1>
  <p>DCF models on the EV/challenger auto names I have a view on. I write the thesis and set the assumptions; the model math and this page are AI-assisted.</p>
</header>
<main>
"""

PAGE_TAIL = """
</main>
<footer>
  <div>Built with a Python DCF engine + AI-assisted tooling. Assumptions and theses marked USER are mine; AI DEFAULT entries are unreviewed placeholders, not opinions. Not investment advice.</div>
  <div style="margin-top:10px;">
    Anatole Tahintzi &middot; USC Marshall, Class of 2029 &middot;
    <a href="mailto:tahintzi@usc.edu" style="color:var(--cyan);text-decoration:none;">tahintzi@usc.edu</a> &middot;
    <a href="https://www.linkedin.com/in/anatole-tahintzi" target="_blank" rel="noopener" style="color:var(--cyan);text-decoration:none;">LinkedIn</a>
  </div>
  <div style="margin-top:10px;color:var(--text-dim);">
    Data sources: live prices via Yahoo Finance &middot; financial statements via SEC EDGAR
  </div>
</footer>
</body>
</html>
"""

def fmt(n, prefix="", dec=2):
    if n is None:
        return "&mdash;"
    return f"{prefix}{n:,.{dec}f}"


def render_card(r):
    val = r["valuation"]
    is_placeholder = r["thesis_author"] != "user" or r["thesis"].startswith("REPLACE ME")
    thesis_class = "placeholder" if is_placeholder else ""
    flag_class = "ai" if is_placeholder else "user"
    flag_text = "AI default &mdash; needs your review" if is_placeholder else "Your thesis"

    sens = r["sensitivity"]
    header_row = "".join(f"<th>{tg*100:.1f}%</th>" for tg in sens["terminal_growth_range"])
    body_rows = ""
    for wacc, row in zip(sens["wacc_range"], sens["grid"]):
        cells = "".join(f'<td>{fmt(v, prefix="$")}</td>' for v in row)
        body_rows += f"<tr><th>{wacc*100:.1f}%</th>{cells}</tr>"

    return f"""
<div class="card">
  <div class="card-head">
    <div class="ticker-block"><div class="ticker">{r['ticker']}</div><div class="name">{r['name']}</div></div>
    <div class="fair-value">
      <div class="label">Fair value / share</div>
      <div class="num">{fmt(val['value_per_share'], prefix='$')}</div>
      <div class="flag {flag_class}">{flag_text}</div>
    </div>
  </div>
  <div class="thesis {thesis_class}">{r['thesis']}</div>
  <div class="grid-row">
    <div class="stat"><div class="label">Enterprise value</div><div class="val">{fmt(val['enterprise_value'], prefix='$', dec=0)}M</div></div>
    <div class="stat"><div class="label">WACC</div><div class="val">{r['assumptions']['wacc']*100:.1f}%</div></div>
    <div class="stat"><div class="label">Terminal growth</div><div class="val">{r['assumptions']['terminal_growth']*100:.1f}%</div></div>
  </div>
  <div class="sens-wrap">
    <div class="sens-title">Value / share &mdash; WACC (rows) x terminal growth (cols)</div>
    <table><tr><th></th>{header_row}</tr>{body_rows}</table>
  </div>
</div>
"""


def main():
    with open("results.json") as f:
        results = json.load(f)
    curated = [r for r in results if r["thesis_author"] == "user"]
    html = PAGE_HEAD + '<section class="section-label">Curated coverage</section>'
    for r in curated:
        html += render_card(r)
    html += PAGE_TAIL
    with open("index.html", "w") as f:
        f.write(html)
    print("Wrote index.html")


if __name__ == "__main__":
    main()