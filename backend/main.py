from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from data import aggregate_training_budget
from llm import generate_summary

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
