from datetime import datetime, timezone

from sklearn.ensemble import IsolationForest

from storage_utils import read_parquet_dataset, write_parquet

FEATURES = ["avg_temp", "avg_humidity", "avg_pressure", "avg_wind_speed"]
MINIMUM_HISTORY = 10


def main() -> None:
    weather = read_parquet_dataset("gold/daily")
    weather["date"] = weather["date"].astype(str)
    weather["is_anomaly"] = False
    weather["anomaly_score"] = 0.0

    for city, city_rows in weather.groupby("city"):
        valid_rows = city_rows.dropna(subset=FEATURES)
        if len(valid_rows) < MINIMUM_HISTORY:
            print(f"Skipping {city}: need {MINIMUM_HISTORY} daily records, found {len(valid_rows)}.")
            continue

        model = IsolationForest(contamination="auto", random_state=42)
        predictions = model.fit_predict(valid_rows[FEATURES])
        scores = model.decision_function(valid_rows[FEATURES])
        weather.loc[valid_rows.index, "is_anomaly"] = predictions == -1
        weather.loc[valid_rows.index, "anomaly_score"] = scores

    weather["processed_at"] = datetime.now(timezone.utc).isoformat()
    write_parquet(weather, "anomalies/weather_anomalies.parquet")
    print(f"Wrote {weather['is_anomaly'].sum()} anomalies to anomalies/weather_anomalies.parquet")


if __name__ == "__main__":
    main()
