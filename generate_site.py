"""
generate_site.py

Renders results.json (curated companies) and, if present, ai_results.json
(weekly AI picks) into a single static index.html with charts. No build
step, no framework - the output file works as-is on GitHub Pages.

Usage:
    python3 dcf_engine.py companies.json results.json
    python3 dcf_engine.py ai_picks.json ai_results.json      # optional
    python3 generate_site.py
"""

import json
import os

PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Teardown &mdash; Challenger Auto Valuations</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Barlow+Condensed:wght@500;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0B1B22;
    --bg-panel: #0F2530;
    --line: #1E3D49;
    --cyan: #5EEAD4;
    --amber: #F5A623;
    --text: #DCEBEE;
    --text-dim: #7FA3AC;
    --red: #E8664B;
    --green: #6EE7A8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    background-image:
      linear-gradient(var(--line) 1px, transparent 1px),
      linear-gradient(90deg, var(--line) 1px, transparent 1px);
    background-size: 48px 48px;
    background-attachment: fixed;
    color: var(--text);
    font-family: 'Space Mono', monospace;
    line-height: 1.5;
  }
  h1, h2, h3, .display {
    font-family: 'Barlow Condensed', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  header {
    padding: 64px 24px 40px;
    max-width: 1000px;
    margin: 0 auto;
    border-bottom: 1px solid var(--line);
  }
  header .eyebrow {
    color: var(--cyan);
    font-size: 13px;
    letter-spacing: 0.15em;
    margin-bottom: 12px;
  }
  header h1 {
    font-size: 56px;
    font-weight: 700;
    margin: 0 0 12px;
    color: var(--text);
  }
  header p {
    color: var(--text-dim);
    max-width: 620px;
    font-size: 15px;
  }
  main {
    max-width: 1000px;
    margin: 0 auto;
    padding: 40px 24px 100px;
  }
  .summary-card {
    background: var(--bg-panel);
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 24px 28px;
    margin-bottom: 16px;
  }
  .summary-title {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 16px;
  }
  .card {
    background: var(--bg-panel);
    border: 1px solid var(--line);
    border-radius: 2px;
    margin-bottom: 32px;
    position: relative;
  }
  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 24px 28px 16px;
    border-bottom: 1px solid var(--line);
  }
  .ticker-block .ticker {
    font-size: 32px;
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 700;
    color: var(--cyan);
    letter-spacing: 0.02em;
  }
  .ticker-block .name {
    color: var(--text-dim);
    font-size: 13px;
  }
  .fair-value {
    text-align: right;
  }
  .fair-value .label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .fair-value .num {
    font-size: 28px;
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 700;
  }
  .fair-value .price-compare {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 2px;
  }
  .flag {
    display: inline-block;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 3px 8px;
    border-radius: 2px;
    margin-top: 6px;
  }
  .flag.ai {
    background: rgba(245, 166, 35, 0.12);
    color: var(--amber);
    border: 1px solid rgba(245, 166, 35, 0.4);
  }
  .flag.user {
    background: rgba(94, 234, 212, 0.1);
    color: var(--cyan);
    border: 1px solid rgba(94, 234, 212, 0.35);
  }
  .thesis {
    padding: 20px 28px;
    color: var(--text);
    font-size: 14px;
    border-bottom: 1px solid var(--line);
    background: rgba(0,0,0,0.15);
  }
  .thesis.placeholder { color: var(--text-dim); font-style: italic; }
  .grid-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    padding: 20px 28px;
    gap: 24px;
    border-bottom: 1px solid var(--line);
  }
  .stat .label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
  }
  .stat .val { font-size: 15px; }
  .chart-wrap { padding: 20px 28px; border-bottom: 1px solid var(--line); }
  .chart-title { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; }
  .chart-canvas-box { position: relative; height: 180px; }
  .sens-wrap { padding: 20px 28px; }
  .sens-title { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; }
  table { border-collapse: collapse; font-size: 12px; width: 100%; }
  th, td { border: 1px solid var(--line); padding: 6px 10px; text-align: center; }
  th { color: var(--cyan); font-weight: 400; }
  td.center-cell { color: var(--amber); font-weight: 700; }
  section.section-label {
    font-size: 12px;
    color: var(--text-dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin: 56px 0 20px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  section.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--line);
  }
  footer {
    max-width: 1000px;
    margin: 0 auto;
    padding: 24px;
    color: var(--text-dim);
    font-size: 12px;
    border-top: 1px solid var(--line);
  }
</style>
</head>
<body>
<header>
  <div class="eyebrow">// TEARDOWN &mdash; VALUATION LOGS</div>
  <h1>Challenger Auto, Priced.</h1>
  <p>DCF models on the EV/challenger auto names I actually have a view on. I write the thesis and set the assumptions; the model math and this page are AI-assisted. Every number below traces back to an assumption you can see &mdash; nothing is hidden in a black box.</p>
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


def fmt(n, prefix="", suffix="", dec=2):
    if n is None:
        return "&mdash;"
    return f"{prefix}{n:,.{dec}f}{suffix}"


def render_card(r, idx):
    val = r["valuation"]
    thesis_class = "placeholder" if r["thesis_author"] != "user" or r["thesis"].startswith("REPLACE ME") else ""
    flag_class = "user" if r["thesis_author"] == "user" and not r["thesis"].startswith("REPLACE ME") else "ai"
    flag_text = "Your thesis" if flag_class == "user" else "AI default &mdash; needs your review"

    price_compare = ""
    cp = r["assumptions"].get("current_price")
    vps = val.get("value_per_share")
    if cp and vps is not None:
        upside = (vps / cp - 1) * 100
        arrow = "&#9650;" if upside >= 0 else "&#9660;"
        color = "var(--green)" if upside >= 0 else "var(--red)"
        price_compare = f'<div class="price-compare">vs current ${cp:,.2f} &middot; <span style="color:{color};">{arrow} {abs(upside):.1f}%</span></div>'

    sens = r["sensitivity"]
    header_row = "".join(f"<th>{tg*100:.1f}%</th>" for tg in sens["terminal_growth_range"])
    body_rows = ""
    for wacc, row in zip(sens["wacc_range"], sens["grid"]):
        cells = "".join(
            f'<td class="{"center-cell" if abs(wacc - r["assumptions"]["wacc"]) < 1e-9 and abs(tg - r["assumptions"]["terminal_growth"]) < 1e-9 else ""}">{fmt(v, prefix="$")}</td>'
            for tg, v in zip(sens["terminal_growth_range"], row)
        )
        body_rows += f"<tr><th>{wacc*100:.1f}%</th>{cells}</tr>"

    chart_id = f"chart-{idx}"

    return f"""
<div class="card">
  <div class="card-head">
    <div class="ticker-block">
      <div class="ticker">{r['ticker']}</div>
      <div class="name">{r['name']}</div>
    </div>
    <div class="fair-value">
      <div class="label">Fair value / share</div>
      <div class="num">{fmt(val['value_per_share'], prefix='$')}</div>
      {price_compare}
      <div class="flag {flag_class}">{flag_text}</div>
    </div>
  </div>
  <div class="thesis {thesis_class}">{r['thesis']}</div>
  <div class="grid-row">
    <div class="stat"><div class="label">Enterprise value</div><div class="val">{fmt(val['enterprise_value'], prefix='$', suffix='M', dec=0)}</div></div>
    <div class="stat"><div class="label">WACC</div><div class="val">{r['assumptions']['wacc']*100:.1f}%</div></div>
    <div class="stat"><div class="label">Terminal growth</div><div class="val">{r['assumptions']['terminal_growth']*100:.1f}%</div></div>
  </div>
  <div class="chart-wrap">
    <div class="chart-title">5-year projection &mdash; revenue (bars) vs free cash flow (line)</div>
    <div class="chart-canvas-box"><canvas id="{chart_id}"></canvas></div>
  </div>
  <div class="sens-wrap">
    <div class="sens-title">Value / share &mdash; WACC (rows) &times; terminal growth (cols)</div>
    <table>
      <tr><th></th>{header_row}</tr>
      {body_rows}
    </table>
  </div>
</div>
"""


def render_summary_chart(all_results):
    rows = []
    for r in all_results:
        cp = r["assumptions"].get("current_price")
        vps = r["valuation"].get("value_per_share")
        if cp and vps is not None:
            rows.append((r["ticker"], (vps / cp - 1) * 100))
    if not rows:
        return ""
    return """
<div class="summary-card">
  <div class="summary-title">Fair value vs current price &mdash; upside/downside by ticker</div>
  <div class="chart-canvas-box" style="height:220px;"><canvas id="summary-chart"></canvas></div>
</div>
"""


def build_chart_script(cards_data, summary_rows):
    """cards_data: list of (chart_id, ticker, years, revenues, fcfs).
    summary_rows: list of (ticker, upside_pct)."""
    lines = ["<script>"]
    lines.append("Chart.defaults.color = '#7FA3AC';")
    lines.append("Chart.defaults.font.family = \"'Space Mono', monospace\";")
    lines.append("Chart.defaults.font.size = 10;")

    for chart_id, ticker, years, revenues, fcfs in cards_data:
        lines.append(f"""
new Chart(document.getElementById('{chart_id}'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(years)},
    datasets: [
      {{
        type: 'bar',
        label: 'Revenue ($M)',
        data: {json.dumps([round(v) for v in revenues])},
        backgroundColor: 'rgba(94, 234, 212, 0.35)',
        borderColor: '#5EEAD4',
        borderWidth: 1,
        yAxisID: 'y'
      }},
      {{
        type: 'line',
        label: 'FCF ($M)',
        data: {json.dumps([round(v) for v in fcfs])},
        borderColor: '#F5A623',
        backgroundColor: '#F5A623',
        tension: 0.3,
        yAxisID: 'y1'
      }}
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{ legend: {{ labels: {{ boxWidth: 10 }} }} }},
    scales: {{
      y: {{ position: 'left', grid: {{ color: '#1E3D49' }}, title: {{ display: true, text: 'Revenue' }} }},
      y1: {{ position: 'right', grid: {{ display: false }}, title: {{ display: true, text: 'FCF' }} }}
    }}
  }}
}});
""")

    if summary_rows:
        tickers = [t for t, _ in summary_rows]
        values = [round(v, 1) for _, v in summary_rows]
        colors = ["'#6EE7A8'" if v >= 0 else "'#E8664B'" for v in values]
        lines.append(f"""
new Chart(document.getElementById('summary-chart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(tickers)},
    datasets: [{{
      label: 'Upside / downside (%)',
      data: {json.dumps(values)},
      backgroundColor: [{",".join(colors)}]
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ color: '#1E3D49' }}, ticks: {{ callback: (v) => v + '%' }} }},
      y: {{ grid: {{ display: false }} }}
    }}
  }}
}});
""")

    lines.append("</script>")
    return "\n".join(lines)


def load_results(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def main():
    curated = load_results("results.json")
    ai_picks = load_results("ai_results.json")

    all_results = curated + ai_picks
    cards_data = []
    for i, r in enumerate(all_results):
        proj = r["projection"]
        years = [f"Y{n+1}" for n in range(len(proj["revenues"]))]
        cards_data.append((f"chart-{i}", r["ticker"], years, proj["revenues"], proj["fcfs"]))

    summary_rows = []
    for r in all_results:
        cp = r["assumptions"].get("current_price")
        vps = r["valuation"].get("value_per_share")
        if cp and vps is not None:
            summary_rows.append((r["ticker"], (vps / cp - 1) * 100))

    html = PAGE_HEAD
    html += render_summary_chart(all_results)

    html += '<section class="section-label">Curated coverage</section>'
    for i, r in enumerate(curated):
        html += render_card(r, i)

    if ai_picks:
        html += '<section class="section-label">This week\'s AI picks &mdash; unreviewed</section>'
        offset = len(curated)
        for j, r in enumerate(ai_picks):
            html += render_card(r, offset + j)

    html += build_chart_script(cards_data, summary_rows)
    html += PAGE_TAIL

    with open("index.html", "w") as f:
        f.write(html)
    print("Wrote index.html")


if __name__ == "__main__":
    main()
