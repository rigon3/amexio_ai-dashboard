import re
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
MONTHLY_DIR = DATA_DIR / "opleiding_monthly"

_FILE_RE = re.compile(r"opleiding_export_(\d{4})-(\d{2})_synthetic\.xlsx$")

# Module-level cache: the combined monthly data is built once and reused.
_combined_cache: pd.DataFrame | None = None


def _load_combined() -> pd.DataFrame:
    """Load every monthly opleiding file, tag each row with its month, and
    join department from medewerkers. Cached after first call."""
    global _combined_cache
    if _combined_cache is not None:
        return _combined_cache

    med = pd.read_excel(DATA_DIR / "medewerkers_overzicht_synthetic.xlsx")
    med = med[["Odoo/SAP ID", "Afdeling"]]

    frames = []
    for path in sorted(MONTHLY_DIR.glob("opleiding_export_*_synthetic.xlsx")):
        m = _FILE_RE.search(path.name)
        if not m:
            continue
        month = f"{m.group(1)}-{m.group(2)}"  # "YYYY-MM"
        df = pd.read_excel(path)
        df["month"] = month
        df["spent"] = df[["Budget #1", "Budget #2", "Budget #3", "Budget #4"]].sum(axis=1)
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No monthly opleiding files found in {MONTHLY_DIR}")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.merge(med, on="Odoo/SAP ID", how="left")
    _combined_cache = combined
    return combined


def available_months() -> list[str]:
    """Sorted list of months present on disk, e.g. ['2026-01', ..., '2026-12']."""
    return sorted(_load_combined()["month"].unique().tolist())


def _months_for_period(period: str, month: str | None) -> tuple[list[str], str]:
    """Resolve which months to include and a human-readable label.

    period: 'monthly' | 'quarterly' | 'yearly'
    month:  anchor 'YYYY-MM' (defaults to the latest available month)
    """
    months = available_months()
    anchor = month if (month and month in months) else months[-1]
    year, mon = anchor.split("-")
    mon_int = int(mon)

    if period == "monthly":
        included = [anchor]
        label = datetime.strptime(anchor, "%Y-%m").strftime("%B %Y")
    elif period == "quarterly":
        q = (mon_int - 1) // 3                       # 0..3
        q_months = [f"{year}-{m:02d}" for m in range(q * 3 + 1, q * 3 + 4)]
        included = [m for m in q_months if m in months]
        label = f"Q{q + 1} {year}"
    elif period == "yearly":
        included = [m for m in months if m.startswith(year)]
        label = year
    else:
        raise ValueError(f"Unknown period: {period!r}")

    return included, label


def aggregate_training_budget(period: str = "monthly", month: str | None = None) -> dict:
    """Aggregate training budget data for the requested period.

    period: 'monthly' (default) | 'quarterly' | 'yearly'
    month:  anchor month 'YYYY-MM'; defaults to the latest available month
    """
    combined = _load_combined()
    months_included, label = _months_for_period(period, month)
    df = combined[combined["month"].isin(months_included)]

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
            "utilisation_pct": float(row["utilisation_pct"]),
            "share_of_total_spent_pct": float(round(row["spent"] / total_spent * 100, 1)) if total_spent else 0.0,
        }
        for _, row in dept.iterrows()
    ]

    return {
        "period": period,
        "period_label": label,
        "months_included": months_included,
        "available_months": available_months(),
        "total_budget": float(round(total_budget, 2)),
        "total_spent": float(round(total_spent, 2)),
        "total_remaining": float(round(total_remaining, 2)),
        "utilisation_pct": float(utilisation_pct),
        "by_department": by_department,
    }


def aggregate_employees() -> dict:
    """Workforce composition snapshot from the medewerkers file."""
    med = pd.read_excel(DATA_DIR / "medewerkers_overzicht_synthetic.xlsx")
    total = len(med)

    active = int(med["Actief"].apply(bool).sum())
    fulltime = int((med["Fulltime / parttime (%)"] >= 100).sum())

    dept_counts = med["Afdeling"].value_counts()
    by_department = [
        {
            "name": str(name),
            "count": int(count),
            "share_pct": float(round(count / total * 100, 1)) if total else 0.0,
        }
        for name, count in dept_counts.items()
    ]

    gender = {str(k): int(v) for k, v in med["Man/vrouw"].value_counts().items()}

    return {
        "total_employees": total,
        "active": active,
        "inactive": total - active,
        "department_count": int(med["Afdeling"].nunique()),
        "fulltime": fulltime,
        "parttime": total - fulltime,
        "avg_age": float(round(med["Leeftijd"].mean(), 1)),
        "gender_split": gender,
        "by_department": by_department,
    }
