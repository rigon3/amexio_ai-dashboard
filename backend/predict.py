"""
predict.py — ML Forecast Backend (Improved — 24 features)

Reads the IKB Excel file, builds features, loads trained model,
predicts next month's spending per department, outputs JSON for frontend.

Usage:
    python predict.py                              # prints JSON to terminal
    python predict.py --excel path/to/file.xlsx    # custom Excel path
    python predict.py --model path/to/model.pkl    # custom model path

In your web backend (Flask/FastAPI), import and call:
    from predict import forecast
    result = forecast()   # returns dict, use jsonify(result) for API
"""

import json
import sys
import os
import argparse
import numpy as np
import pandas as pd
import joblib


# CONFIG
DEFAULT_EXCEL = "backend/data/IKB_overview_export_synthetic.xlsx" 
DEFAULT_MODEL = "model/model_random_forest.pkl"

DEPARTMENTS = sorted(["CX", "ECX", "Marketing", "Recruitment", "Sales", "Support"])
DEPT_MAP = {d: i for i, d in enumerate(DEPARTMENTS)}


def read_monthly_data(excel_path):
    """Read IKB Excel and return monthly spending per department."""
    df = pd.read_excel(excel_path)
    monthly = df.groupby(["period", "company_group"])["amount_in_value"].sum().reset_index()
    pivot = monthly.pivot(index="period", columns="company_group", values="amount_in_value").fillna(0)
    pivot.index = pd.to_datetime(pivot.index, format="%Y-%m")
    pivot = pivot.sort_index()
    pivot["Total"] = pivot.sum(axis=1)
    return pivot


def build_features(monthly_df, dept, next_month):
    """Build 24 features for one department for next month."""
    s = monthly_df[dept].values

    # Year-to-date spending
    ytd = 0
    for dt, val in zip(monthly_df.index, monthly_df[dept].values):
        if dt.year == next_month.year:
            ytd += val

    features = pd.DataFrame([{
        # Original 9 features
        "month": next_month.month,
        "year": next_month.year,
        "lag_1": s[-1],
        "lag_2": s[-2],
        "lag_3": s[-3],
        "rolling_avg_3": np.mean(s[-3:]),
        "trend": s[-1] - s[-2],
        "ytd_spend": ytd,
        "dept_code": DEPT_MAP[dept],

        # New: more lags
        "lag_4": s[-4],
        "lag_5": s[-5],
        "lag_6": s[-6],

        # New: longer rolling averages
        "rolling_avg_6": np.mean(s[-6:]),
        "rolling_avg_12": np.mean(s[-12:]),

        # New: volatility
        "rolling_std_3": np.std(s[-3:]),
        "rolling_std_6": np.std(s[-6:]),

        # New: range
        "rolling_min_3": np.min(s[-3:]),
        "rolling_max_3": np.max(s[-3:]),
        "rolling_range_3": np.max(s[-3:]) - np.min(s[-3:]),

        # New: seasonality
        "same_month_last_year": s[-12],

        # New: acceleration
        "acceleration": (s[-1] - s[-2]) - (s[-2] - s[-3]),

        # New: percentage change
        "pct_change_1": ((s[-1] - s[-2]) / s[-2] * 100) if s[-2] != 0 else 0,

        # New: ratio to historical average
        "ratio_to_avg": s[-1] / np.mean(s) if np.mean(s) != 0 else 1,

        # New: quarter
        "quarter": (next_month.month - 1) // 3 + 1,
    }])

    return features


def forecast(excel_path=None, model_path=None):
    """Main function. Reads Excel, predicts, returns dict for frontend."""

    excel_path = excel_path or DEFAULT_EXCEL
    model_path = model_path or DEFAULT_MODEL

    model = joblib.load(model_path)
    monthly = read_monthly_data(excel_path)

    last_month = monthly.index[-1]
    next_month = last_month + pd.DateOffset(months=1)
    avg_monthly_total = monthly["Total"].mean()

    depts = [c for c in monthly.columns if c != "Total"]
    dept_results = []

    for dept in depts:
        features = build_features(monthly, dept, next_month)
        predicted = float(max(model.predict(features)[0], 0))
        current = float(monthly[dept].iloc[-1])

        if current > 0:
            change_pct = round((predicted - current) / current * 100, 1)
        else:
            change_pct = 0.0

        dept_results.append({
            "department": dept,
            "current_spend": round(current, 2),
            "predicted_spend": round(predicted, 2),
            "change_eur": round(predicted - current, 2),
            "change_pct": change_pct,
        })

    dept_results.sort(key=lambda x: x["predicted_spend"], reverse=True)

    total_predicted = sum(d["predicted_spend"] for d in dept_results)
    total_current = sum(d["current_spend"] for d in dept_results)

    spend_change_pct = round((total_predicted - total_current) / total_current * 100, 1) if total_current > 0 else 0.0
    utilisation = round(total_predicted / avg_monthly_total * 100, 1) if avg_monthly_total > 0 else 0
    util_current = round(total_current / avg_monthly_total * 100, 1) if avg_monthly_total > 0 else 0
    util_change = round(utilisation - util_current, 1)

    remaining = round(avg_monthly_total - total_predicted, 2)
    remaining_current = avg_monthly_total - total_current
    remaining_change_pct = round((remaining - remaining_current) / abs(remaining_current) * 100, 1) if remaining_current != 0 else 0.0

    highest = dept_results[0]

    output = {
        "forecast_month": next_month.strftime("%Y-%m"),
        "current_month": last_month.strftime("%Y-%m"),
        "model_used": type(model).__name__,

        "kpi": {
            "predicted_spend": round(total_predicted, 2),
            "predicted_spend_change_pct": spend_change_pct,
            "predicted_utilisation": utilisation,
            "predicted_utilisation_change_pct": util_change,
            "predicted_remaining": remaining,
            "predicted_remaining_change_pct": remaining_change_pct,
            "highest_spender": highest["department"],
            "highest_spender_amount": highest["predicted_spend"],
        },

        "per_department": dept_results,
    }

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ML Forecast: Predict next month department spending")
    parser.add_argument("--excel", default=DEFAULT_EXCEL, help="Path to IKB Excel file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Path to trained model .pkl")
    args = parser.parse_args()

    result = forecast(excel_path=args.excel, model_path=args.model)
    print(json.dumps(result, indent=2, ensure_ascii=False))
