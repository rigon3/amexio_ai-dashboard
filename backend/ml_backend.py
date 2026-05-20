from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

MODEL_ENV_VAR = "TRAINING_BUDGET_MODEL_PATH"
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "training_budget_forecast.pkl"

FEATURE_NAMES = [
	"total_budget",
	"total_spent",
	"total_remaining",
	"utilisation_pct",
	"department_count",
	"highest_department_utilisation_pct",
	"lowest_department_utilisation_pct",
	"average_department_utilisation_pct",
]


class StubTrainingBudgetModel:
	"""Fallback model used until a trained artifact is available."""

	is_stub = True

	def predict(self, rows: list[list[float]]) -> list[float]:
		row = rows[0]
		total_budget = float(row[0])
		total_spent = float(row[1])
		total_remaining = float(row[2])
		utilisation_pct = float(row[3])
		department_count = max(float(row[4]), 1.0)
		highest_department_utilisation_pct = float(row[5])
		lowest_department_utilisation_pct = float(row[6])
		average_department_utilisation_pct = float(row[7])

		utilisation_pressure = utilisation_pct / 100.0
		spread_pressure = max(highest_department_utilisation_pct - lowest_department_utilisation_pct, 0.0) / 100.0
		department_pressure = average_department_utilisation_pct / 100.0 / department_count

		fallback_budget = total_budget
		fallback_budget += total_spent * 0.08
		fallback_budget += total_remaining * 0.12
		fallback_budget += total_budget * utilisation_pressure * 0.05
		fallback_budget += total_budget * spread_pressure * 0.03
		fallback_budget += total_budget * department_pressure * 0.02

		return [round(fallback_budget, 2)]


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


def build_forecast_features(snapshot: dict) -> list[float]:
	departments = snapshot.get("by_department", [])
	utilisation_values = [float(department.get("utilisation_pct", 0.0)) for department in departments]

	department_count = float(len(departments))
	highest_utilisation = max(utilisation_values) if utilisation_values else 0.0
	lowest_utilisation = min(utilisation_values) if utilisation_values else 0.0
	average_utilisation = sum(utilisation_values) / department_count if department_count else 0.0

	return [
		float(snapshot.get("total_budget", 0.0)),
		float(snapshot.get("total_spent", 0.0)),
		float(snapshot.get("total_remaining", 0.0)),
		float(snapshot.get("utilisation_pct", 0.0)),
		department_count,
		float(highest_utilisation),
		float(lowest_utilisation),
		float(average_utilisation),
	]


def forecast_training_budget(snapshot: dict, model_path: str | Path | None = None) -> dict:
	"""Forecast the next training budget using the configured model or a stub."""

	model, resolved_path, is_stub = load_training_budget_model(model_path)
	features = build_forecast_features(snapshot)

	prediction = model.predict([features])
	forecast_budget = float(prediction[0]) if isinstance(prediction, (list, tuple)) else float(prediction)

	return {
		"period": "next_period",
		"forecast_budget": round(forecast_budget, 2),
		"model_ready": not is_stub,
		"model_path": str(resolved_path),
		"model_source": "serialized_model" if not is_stub else "stub_fallback",
		"input_features": dict(zip(FEATURE_NAMES, features)),
		"note": (
			"Stub forecast in use because no trained model artifact was found yet."
			if is_stub
			else "Forecast generated from the loaded model artifact."
		),
	}
