import requests
import pandas as pd
from datetime import datetime
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY = "Delhi"
BUCKET = "climate-lakehouse"
BRONZE_PATH = "bronze/"

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)

url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
r = requests.get(url)
data = r.json()

if r.status_code == 200 and "main" in data:
    row = {
        "city": CITY,
        "temp": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "wind_speed": data["wind"]["speed"],
        "weather": data["weather"][0]["description"],
        "timestamp": datetime.utcnow().isoformat()
    }
    df = pd.DataFrame([row])
    
    # Save to in-memory buffer and upload
    from io import BytesIO
    buffer = BytesIO()
    df.to_parquet(buffer, index=False)  # Parquet is better for Spark than CSV
    
    file_name = f"weather_{int(datetime.utcnow().timestamp())}.parquet"
    s3.put_object(Bucket=BUCKET, Key=BRONZE_PATH + file_name, Body=buffer.getvalue())
    
    print("Uploaded to bronze:", file_name)
else:
    print("Error:", data)