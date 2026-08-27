from datetime import timedelta

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from storage_utils import read_parquet_dataset, write_parquet

FORECAST_DAYS = 7
MINIMUM_HISTORY = 7


def main() -> None:
    weather = read_parquet_dataset("gold/daily")
    weather["date"] = pd.to_datetime(weather["date"])
    forecasts = []

    for city, city_rows in weather.groupby("city"):
        series = city_rows.sort_values("date").dropna(subset=["avg_temp"])
        if len(series) < MINIMUM_HISTORY:
            print(f"Skipping {city}: need {MINIMUM_HISTORY} daily records, found {len(series)}.")
            continue

        temperatures = series["avg_temp"].astype(float).reset_index(drop=True)
        model = ExponentialSmoothing(temperatures, trend="add", initialization_method="estimated")
        values = model.fit(optimized=True).forecast(FORECAST_DAYS)
        start_date = series["date"].max() + timedelta(days=1)

        for offset, value in enumerate(values):
            forecasts.append({
                "city": city,
                "forecast_date": (start_date + timedelta(days=offset)).date().isoformat(),
                "forecast_temp": round(float(value), 2),
                "model": "holt_exponential_smoothing",
            })

    if not forecasts:
        print("No forecasts produced. Collect at least 7 days of Gold data per city.")
        return

    write_parquet(pd.DataFrame(forecasts), "forecasts/temperature_forecasts.parquet")
    print(f"Wrote {len(forecasts)} forecast records to forecasts/temperature_forecasts.parquet")


if __name__ == "__main__":
    main()
