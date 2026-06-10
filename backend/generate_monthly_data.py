"""
generate_monthly_data.py — Synthetic monthly training-budget exports

Each opleiding_export file represents ONE month. This script takes the single
base file (opleiding_export_synthetic.xlsx) and produces 12 monthly files for
2026, keeping the employee roster (names, IDs, monthly allocation) stable while
varying the draws (Budget #1-#4) and Resterend per month following a seasonal
utilisation pattern.

Output: backend/data/opleiding_monthly/opleiding_export_YYYY-MM_synthetic.xlsx

Run once:
    python generate_monthly_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_FILE = Path(__file__).parent / "data" / "opleiding_export_synthetic.xlsx"
OUT_DIR = Path(__file__).parent / "data" / "opleiding_monthly"
YEAR = 2026

# Average share of the monthly budget that gets drawn, per month.
# Models a realistic training cycle: Q1/autumn pushes, summer + December lulls.
MONTHLY_FACTOR = {
    1: 0.58, 2: 0.55, 3: 0.62,
    4: 0.50, 5: 0.48, 6: 0.40,
    7: 0.30, 8: 0.28, 9: 0.55,
    10: 0.60, 11: 0.52, 12: 0.38,
}

COLUMNS = [
    "Voornaam", "Tussenvoegsel", "Achternaam", "Odoo/SAP ID",
    "Totaal opleidingsbudget",
    "Budget #1", "Budget #2", "Budget #3", "Budget #4",
    "Resterend budget",
]

rng = np.random.default_rng(42)  # fixed seed -> reproducible files


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = pd.read_excel(BASE_FILE)
    roster = base[["Voornaam", "Tussenvoegsel", "Achternaam",
                   "Odoo/SAP ID", "Totaal opleidingsbudget"]].copy()
    n = len(roster)

    for month in range(1, 13):
        df = roster.copy()
        factor = MONTHLY_FACTOR[month]
        totaal = df["Totaal opleidingsbudget"].to_numpy(dtype=float)

        # 85% of employees draw training in a given month
        trains = rng.random(n) < 0.85
        # per-employee utilisation centred on the month's factor
        util = np.clip(rng.normal(factor, 0.12, n), 0.0, 0.98)
        util[~trains] = 0.0
        drawn_total = totaal * util

        # split each employee's drawn amount across up to 4 events
        weights = rng.random((n, 4))
        keep = rng.random((n, 4)) < 0.7   # not everyone has all 4 draws
        keep[:, 0] = True                  # at least one draw if they trained
        weights *= keep
        wsum = weights.sum(axis=1, keepdims=True)
        wsum[wsum == 0] = 1.0
        draws = np.round((weights / wsum) * drawn_total[:, None], 2)
        draws[~trains] = 0.0

        for i in range(4):
            df[f"Budget #{i + 1}"] = draws[:, i]
        df["Resterend budget"] = np.round(totaal - draws.sum(axis=1), 2).clip(min=0)

        df = df[COLUMNS]
        out = OUT_DIR / f"opleiding_export_{YEAR}-{month:02d}_synthetic.xlsx"
        df.to_excel(out, index=False)

        util_pct = round(draws.sum() / totaal.sum() * 100, 1)
        print(f"{out.name}  utilisation ~ {util_pct}%")


if __name__ == "__main__":
    main()
