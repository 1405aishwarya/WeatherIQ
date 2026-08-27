import requests
import pandas as pd
import os
from datetime import datetime, timezone
from io import BytesIO
import boto3
from dotenv import load_dotenv

CITIES = [
    {"city": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"city": "London", "latitude": 51.5072, "longitude": -0.1276},
    {"city": "New York", "latitude": 40.7128, "longitude": -74.0060},
    {"city": "Tokyo", "latitude": 35.6762, "longitude": 139.6503},
    {"city": "Paris", "latitude": 48.8566, "longitude": 2.3522},
    {"city": "Sydney", "latitude": -33.8688, "longitude": 151.2093},
    {"city": "Dubai", "latitude": 25.2048, "longitude": 55.2708},
    {"city": "Singapore", "latitude": 1.3521, "longitude": 103.8198},
    {"city": "Toronto", "latitude": 43.6532, "longitude": -79.3832},
    {"city": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
]

load_dotenv()

BUCKET = os.getenv("MINIO_BUCKET", "climate-lakehouse")
BRONZE_PATH = "bronze/"
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
    raise RuntimeError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be set.")

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

latitudes = ",".join(str(city["latitude"]) for city in CITIES)
longitudes = ",".join(str(city["longitude"]) for city in CITIES)

url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": latitudes,
    "longitude": longitudes,
    "current": (
        "temperature_2m,relative_humidity_2m,surface_pressure,"
        "wind_speed_10m,weather_code"
    ),
    "timezone": "UTC",
}

response = requests.get(url, params=params, timeout=30)
response.raise_for_status()
weather_results = response.json()

if isinstance(weather_results, dict):
    weather_results = [weather_results]

timestamp = datetime.now(timezone.utc).isoformat()
rows = []

for city, result in zip(CITIES, weather_results):
    current = result.get("current", {})

    if not current:
        print(f"Skipping {city['city']}: no weather data returned")
        continue

    rows.append({
        "city": city["city"],
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "temp": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "pressure": current.get("surface_pressure"),
        "wind_speed": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
        "timestamp": timestamp,
    })

if not rows:
    raise RuntimeError("No weather records were returned.")

df = pd.DataFrame(rows)

buffer = BytesIO()
df.to_parquet(buffer, index=False)

file_name = f"weather_{int(datetime.now(timezone.utc).timestamp())}.parquet"
s3.put_object(
    Bucket=BUCKET,
    Key=BRONZE_PATH + file_name,
    Body=buffer.getvalue(),
)

print(f"Uploaded {len(rows)} cities to bronze: {file_name}")
