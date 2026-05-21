import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def aggregate_training_budget() -> dict:
    opl = pd.read_excel(DATA_DIR / "opleiding_export_synthetic.xlsx")
    med = pd.read_excel(DATA_DIR / "medewerkers_overzicht_synthetic.xlsx")

    # Keep only what we need from medewerkers before joining
    med = med[["Odoo/SAP ID", "Afdeling"]]

    df = opl.merge(med, on="Odoo/SAP ID", how="left")

    # Total spent = sum of the four budget line items
    df["spent"] = df[["Budget #1", "Budget #2", "Budget #3", "Budget #4"]].sum(axis=1)

    # Company-wide totals
    total_budget = df["Totaal opleidingsbudget"].sum()
    total_spent = df["spent"].sum()
    total_remaining = df["Resterend budget"].sum()
    utilisation_pct = round(total_spent / total_budget * 100, 1) if total_budget else 0

    # Per-department breakdown
    dept = (
        df.groupby("Afdeling")
        .agg(
            budget=("Totaal opleidingsbudget", "sum"),
            spent=("spent", "sum"),
            remaining=("Resterend budget", "sum"),
            budget_line_1=("Budget #1", "sum"),
            budget_line_2=("Budget #2", "sum"),
            budget_line_3=("Budget #3", "sum"),
            budget_line_4=("Budget #4", "sum"),
        )
        .reset_index()
    )
    dept["utilisation_pct"] = (dept["spent"] / dept["budget"] * 100).round(1)
    dept = dept.sort_values("utilisation_pct", ascending=False)

    by_department = [
        {
            "name": row["Afdeling"],
            "budget": float(round(row["budget"], 2)),
            "spent": float(round(row["spent"], 2)),
            "remaining": float(round(row["remaining"], 2)),
            "budget_line_1": float(round(row["budget_line_1"], 2)),
            "budget_line_2": float(round(row["budget_line_2"], 2)),
            "budget_line_3": float(round(row["budget_line_3"], 2)),
            "budget_line_4": float(round(row["budget_line_4"], 2)),
            "utilisation_pct": float(row["utilisation_pct"]),
            "share_of_total_spent_pct": float(round(row["spent"] / total_spent * 100, 1)),
        }
        for _, row in dept.iterrows()
    ]

    return {
        "period": "2026",
        "total_budget": float(round(total_budget, 2)),
        "total_spent": float(round(total_spent, 2)),
        "total_remaining": float(round(total_remaining, 2)),
        "utilisation_pct": float(utilisation_pct),
        "by_department": by_department,
    }
