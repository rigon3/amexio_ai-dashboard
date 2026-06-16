from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys
import os
import pandas as pd

from data import aggregate_training_budget
from llm import generate_summary

# Add model folder to path so predict.py can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'model'))
from predict import forecast

# Paths
DATA_DIR = Path(__file__).parent / "data"
MODEL_PATH = Path(__file__).parent.parent / "model" / "model_random_forest.pkl"
EMPLOYEE_PATH = DATA_DIR / "medewerkers_overzicht_synthetic.xlsx"

# App must be defined before any routes
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/employees")
def get_employees():
    import pandas as pd
    df = pd.read_excel(EMPLOYEE_PATH)
    df["Naam"] = (df["Voornaam"].fillna("") + " " + df["Tussenvoegsel"].fillna("") + " " + df["Achternaam"].fillna("")).str.strip().str.replace("  ", " ")
    df["status"] = df["Actief"].apply(lambda x: "Active" if x else "Inactive")
    df["Indienstdatum"] = pd.to_datetime(df["Indienstdatum"]).dt.strftime("%d-%m-%Y")
    return df.rename(columns={"Naam":"name","Afdeling":"department","Fulltime / parttime (%)":"contract","Indienstdatum":"start_date","Woonplaats":"city"})[["name","department","contract","start_date","city","status"]].to_dict(orient="records")

@app.get("/data")
def data(period: str = "monthly", month: str | None = None):
    return aggregate_training_budget(period=period, month=month)


@app.post("/summary")
def summary(view: str = "training_budget", period: str = "monthly", month: str | None = None):
    try:
        return generate_summary(view=view, period=period, month=month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {e}")


@app.get("/forecast")
def get_forecast():
    try:
        result = forecast(
           excel_path=str(DATA_DIR / "IKB_overview_export_synthetic.xlsx"),
            model_path=str(MODEL_PATH)
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast error: {e}")
    
    