from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

MODEL_ENV_VAR = "TRAINING_BUDGET_MODEL_PATH"
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "training_budget_forecast.pkl"

FEATURE_NAMES = [
	"budget_line_1",
	"budget_line_2",
	"budget_line_3",
	"budget_line_4",
	"department_budget_total",
	"department_spent",
	"department_remaining",
	"department_utilisation_pct",
	"share_of_total_spent_pct",
	"department_count",
	"highest_department_utilisation_pct",
	"lowest_department_utilisation_pct",
	"average_department_utilisation_pct",
]


class StubTrainingBudgetModel:
	"""Fallback model used until a trained artifact is available."""

	is_stub = True

	def predict(self, rows: list[list[float]]) -> list[float]:
		results: list[float] = []
		for row in rows:
			# Per-department features according to FEATURE_NAMES
			budget1 = float(row[0])
			budget2 = float(row[1])
			budget3 = float(row[2])
			budget4 = float(row[3])
			dept_total = float(row[4])
			dept_spent = float(row[5])
			dept_remaining = float(row[6])
			dept_util = float(row[7])
			share_of_total = float(row[8])
			department_count = max(float(row[9]) if len(row) > 9 else 1.0, 1.0)
			highest_department_utilisation_pct = float(row[10]) if len(row) > 10 else dept_util
			lowest_department_utilisation_pct = float(row[11]) if len(row) > 11 else dept_util
			average_department_utilisation_pct = float(row[12]) if len(row) > 12 else dept_util

			# Simple heuristic combining line budgets and utilisation signals
			line_sum = budget1 + budget2 + budget3 + budget4
			utilisation_pressure = dept_util / 100.0
			spread_pressure = max(highest_department_utilisation_pct - lowest_department_utilisation_pct, 0.0) / 100.0

			base = dept_total
			base += line_sum * 0.05
			base += dept_spent * 0.06
			base += dept_remaining * 0.04
			base += dept_total * utilisation_pressure * 0.03
			base += dept_total * spread_pressure * 0.02
			base += dept_total * (average_department_utilisation_pct / 100.0) / department_count * 0.01

			results.append(round(base, 2))

		return results


def _resolve_model_path(model_path: str | Path | None = None) -> Path:
	if model_path is not None:
		return Path(model_path)

	env_value = os.getenv(MODEL_ENV_VAR)
	if env_value:
		return Path(env_value)

	return DEFAULT_MODEL_PATH


def _load_serialized_model(model_path: Path) -> Any:
	with model_path.open("rb") as handle:
		return pickle.load(handle)


def load_training_budget_model(model_path: str | Path | None = None) -> tuple[Any, Path, bool]:
	"""Load a saved model if it exists, otherwise return the stub model."""

	resolved_path = _resolve_model_path(model_path)
	if resolved_path.exists():
		try:
			return _load_serialized_model(resolved_path), resolved_path, False
		except Exception:
			return StubTrainingBudgetModel(), resolved_path, True

	return StubTrainingBudgetModel(), resolved_path, True


def build_features_for_department(snapshot: dict, department: dict) -> list[float]:
	departments = snapshot.get("by_department", [])
	utilisation_values = [float(d.get("utilisation_pct", 0.0)) for d in departments]

	department_count = float(len(departments)) if departments else 1.0
	highest_utilisation = max(utilisation_values) if utilisation_values else 0.0
	lowest_utilisation = min(utilisation_values) if utilisation_values else 0.0
	average_utilisation = sum(utilisation_values) / department_count if department_count else 0.0

	return [
		float(department.get("budget_line_1", 0.0)),
		float(department.get("budget_line_2", 0.0)),
		float(department.get("budget_line_3", 0.0)),
		float(department.get("budget_line_4", 0.0)),
		float(department.get("budget", 0.0)),
		float(department.get("spent", 0.0)),
		float(department.get("remaining", 0.0)),
		float(department.get("utilisation_pct", 0.0)),
		float(department.get("share_of_total_spent_pct", 0.0)),
		department_count,
		highest_utilisation,
		lowest_utilisation,
		average_utilisation,
	]


def forecast_training_budget(snapshot: dict, model_path: str | Path | None = None) -> dict:
	"""Forecast per-department next training budget using configured model or stub.

	Returns a dict with `forecast_budget` (company-level) and
	`by_department_forecasts` listing per-department forecasts.
	"""

	model, resolved_path, is_stub = load_training_budget_model(model_path)

	departments = snapshot.get("by_department", [])
	feature_rows = [build_features_for_department(snapshot, d) for d in departments]

	# Predict for all departments in one batch
	predictions = model.predict(feature_rows)

	# Normalize predictions to list
	if not isinstance(predictions, (list, tuple)):
		predictions = [predictions]

	by_dept = []
	for dept, pred in zip(departments, predictions):
		by_dept.append(
			{
				"name": dept.get("name"),
				"forecast_budget": float(pred),
				"input_features": dict(zip(FEATURE_NAMES, build_features_for_department(snapshot, dept))),
			}
		)

	# Company-level forecast: sum of department forecasts as a simple aggregation
	company_forecast = round(sum(d["forecast_budget"] for d in by_dept), 2) if by_dept else 0.0

	return {
		"period": "next_period",
		"forecast_budget": company_forecast,
		"model_ready": not is_stub,
		"model_path": str(resolved_path),
		"model_source": "serialized_model" if not is_stub else "stub_fallback",
		"by_department_forecasts": by_dept,
		"note": (
			"Stub forecast in use because no trained model artifact was found yet."
			if is_stub
			else "Forecast generated from the loaded model artifact."
		),
	}
