from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from storage_utils import read_parquet_dataset

app = FastAPI(title="WeatherIQ API", version="1.0.0")


class WeatherRecord(BaseModel):
    city: str
    date: str
    avg_temp: float | None = None
    avg_humidity: float | None = None
    avg_pressure: float | None = None
    avg_wind_speed: float | None = None


@lru_cache(maxsize=1)
def gold_data() -> pd.DataFrame:
    data = read_parquet_dataset("gold/daily")
    data["date"] = data["date"].astype(str)
    return data


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/cities", response_model=list[str])
def cities() -> list[str]:
    return sorted(gold_data()["city"].dropna().unique().tolist())


@app.get("/weather/{city}", response_model=list[WeatherRecord])
def weather(city: str, limit: int = Query(default=30, ge=1, le=365)) -> list[dict]:
    records = gold_data().loc[gold_data()["city"].str.lower() == city.lower()].sort_values("date").tail(limit)
    if records.empty:
        raise HTTPException(status_code=404, detail=f"No Gold data found for {city}.")
    columns = [field for field in WeatherRecord.model_fields if field in records.columns]
    return records[columns].where(pd.notna(records[columns]), None).to_dict(orient="records")


@app.get("/anomalies/{city}")
def anomalies(city: str) -> list[dict]:
    try:
        data = read_parquet_dataset("anomalies")
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Run anomaly_detection.py first.") from error
    data["date"] = data["date"].astype(str)
    records = data.loc[(data["city"].str.lower() == city.lower()) & data["is_anomaly"]]
    return records.where(pd.notna(records), None).to_dict(orient="records")


@app.get("/forecasts/{city}")
def forecasts(city: str) -> list[dict]:
    try:
        data = read_parquet_dataset("forecasts")
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Run forecast_weather.py after collecting 7 days of data.") from error
    records = data.loc[data["city"].str.lower() == city.lower()].sort_values("forecast_date")
    return records.where(pd.notna(records), None).to_dict(orient="records")


@app.post("/refresh-cache")
def refresh_cache() -> dict:
    gold_data.cache_clear()
    return {"message": "Gold-data cache cleared."}
