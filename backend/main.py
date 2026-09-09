from fastapi import FastAPI
from tasks.daily_ingest import run_daily_ingest

app = FastAPI()

@app.get("/run-daily-ingest")
def run_daily_ingest_endpoint():
    return run_daily_ingest()

@app.get("/")
def root():
    return {"status": "backend ok"}

