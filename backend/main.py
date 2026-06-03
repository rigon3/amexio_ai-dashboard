from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys
import os

from data import aggregate_training_budget
from llm import generate_summary

# Add model folder to path so predict.py can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'model'))
from predict import forecast

# Paths
DATA_DIR = Path(__file__).parent / "data"
MODEL_PATH = Path(__file__).parent.parent / "model" / "model_random_forest.pkl"

# App must be defined before any routes
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/data")
def data():
    return aggregate_training_budget()


@app.post("/summary")
def summary():
    data = aggregate_training_budget()
    try:
        result = generate_summary(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")
    return result


@app.get("/forecast")
def get_forecast():
    try:
        result = forecast(
           excel_path=str(DATA_DIR / "IKB_overview_export.xlsx"),
            model_path=str(MODEL_PATH)
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast error: {e}")