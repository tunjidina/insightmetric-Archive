from datetime import date
from pipeline import fetch_trends, score_sentiment, predict_recurrence
from storage import save_daily_results

def run_daily_ingest():
    trends = fetch_trends()
    scored = score_sentiment(trends)
    predictions = predict_recurrence(scored)
    save_daily_results(date.today(), predictions)
    return {"status": "completed", "date": str(date.today())}
