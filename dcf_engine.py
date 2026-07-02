"""
dcf_engine.py

A DCF engine that separates "mechanics" (this file) from "assumptions"
(companies.json). The idea: this script never invents a growth rate,
margin target, or WACC. Those come from the JSON file, and for the
curated companies they should be YOUR view, with a one-line rationale.

Usage:
    python3 dcf_engine.py companies.json results.json
"""

import json
import sys
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class DCFAssumptions:
    ticker: str
    name: str
    thesis: str
    thesis_author: str
    base_revenue_musd: float
    revenue_growth: List[float]
    ebitda_margin: List[float]
    tax_rate: float
    da_pct_revenue: float
    capex_pct_revenue: float
    nwc_pct_revenue_change: float
    wacc: float
    terminal_growth: float
    net_debt_musd: float
    shares_out_musd: float
    current_price: float = None


def project_fcf(a: DCFAssumptions) -> Dict:
    years = len(a.revenue_growth)
    revenues = []
    rev = a.base_revenue_musd
    for g in a.revenue_growth:
        rev = rev * (1 + g)
        revenues.append(rev)

    fcfs = []
    prev_rev = a.base_revenue_musd
    for i in range(years):
        rev = revenues[i]
        ebitda = rev * a.ebitda_margin[i]
        da = rev * a.da_pct_revenue
        ebit = ebitda - da
        nopat = ebit * (1 - a.tax_rate)
        capex = rev * a.capex_pct_revenue
        delta_rev = rev - prev_rev
        delta_nwc = delta_rev * a.nwc_pct_revenue_change
        fcf = nopat + da - capex - delta_nwc
        fcfs.append(fcf)
        prev_rev = rev

    return {"revenues": revenues, "fcfs": fcfs}


def discount_and_value(a: DCFAssumptions, fcfs: List[float]) -> Dict:
    pv_fcfs = [fcf / ((1 + a.wacc) ** t) for t, fcf in enumerate(fcfs, start=1)]

    terminal_fcf = fcfs[-1] * (1 + a.terminal_growth)
    terminal_value = terminal_fcf / (a.wacc - a.terminal_growth)
    pv_terminal = terminal_value / ((1 + a.wacc) ** len(fcfs))

    enterprise_value = sum(pv_fcfs) + pv_terminal
    equity_value = enterprise_value - a.net_debt_musd
    value_per_share = equity_value / a.shares_out_musd if a.shares_out_musd else None

    result = {
        "pv_fcfs": pv_fcfs,
        "sum_pv_fcfs": sum(pv_fcfs),
        "terminal_value": terminal_value,
        "pv_terminal_value": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "value_per_share": value_per_share,
        "pct_ev_from_terminal": pv_terminal / enterprise_value if enterprise_value else None,
    }
    if a.current_price:
        result["current_price"] = a.current_price
        result["upside_pct"] = (value_per_share / a.current_price - 1) if value_per_share else None
    return result


def sensitivity_table(a: DCFAssumptions, wacc_range, terminal_growth_range) -> List[List[float]]:
    base = project_fcf(a)
    grid = []
    for w in wacc_range:
        row = []
        for tg in terminal_growth_range:
            a2 = DCFAssumptions(**{**a.__dict__, "wacc": w, "terminal_growth": tg})
            val = discount_and_value(a2, base["fcfs"])
            row.append(round(val["value_per_share"], 2) if val["value_per_share"] else None)
        grid.append(row)
    return grid


def run_company(record: Dict) -> Dict:
    a = DCFAssumptions(**{k: v for k, v in record.items() if k in DCFAssumptions.__dataclass_fields__})
    proj = project_fcf(a)
    val = discount_and_value(a, proj["fcfs"])
    wacc_range = [round(a.wacc - 0.02, 3), round(a.wacc - 0.01, 3), a.wacc,
                  round(a.wacc + 0.01, 3), round(a.wacc + 0.02, 3)]
    tg_range = [round(a.terminal_growth - 0.01, 3), a.terminal_growth, round(a.terminal_growth + 0.01, 3)]
    sens = sensitivity_table(a, wacc_range, tg_range)

    return {
        "ticker": a.ticker,
        "name": a.name,
        "thesis": a.thesis,
        "thesis_author": a.thesis_author,
        "assumptions": record,
        "projection": proj,
        "valuation": val,
        "sensitivity": {
            "wacc_range": wacc_range,
            "terminal_growth_range": tg_range,
            "grid": sens,
        },
    }


def main():
    infile = sys.argv[1] if len(sys.argv) > 1 else "companies.json"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "results.json"
    with open(infile) as f:
        companies = json.load(f)

    results = [run_company(c) for c in companies]

    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)

    for r in results:
        vps = r["valuation"]["value_per_share"]
        flag = "" if r["thesis_author"] == "user" else "  [AI DEFAULT - NEEDS YOUR REVIEW]"
        print(f"{r['ticker']:6s} fair value/share: ${vps:,.2f}{flag}")

    print(f"\nWrote {outfile}")


if __name__ == "__main__":
    main()
