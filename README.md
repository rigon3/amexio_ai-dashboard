# amexio_ai-dashboard
HR dashboard with AI elements for Amexio

Running the LLM model and Streamlit for testing the summaries.

1. Place the Excel files in backend/data/
2. Run uvicorn main:app --reload from backend/
3. Run streamlit run app.py from frontend/
4. Have Ollama running with llama3.1:8b pulled

for the ML model:
1. For budget forecasting, add a serialized model at backend/models/training_budget_forecast.pkl or set TRAINING_BUDGET_MODEL_PATH before starting the backend
2. Call GET /forecast to read the current forecast payload