import os

import boto3
import pandas as pd
import s3fs
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
BUCKET = os.getenv("MINIO_BUCKET", "climate-lakehouse")

if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
    raise RuntimeError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be set.")


def get_filesystem() -> s3fs.S3FileSystem:
    return s3fs.S3FileSystem(
        client_kwargs={"endpoint_url": MINIO_ENDPOINT},
        key=MINIO_ACCESS_KEY,
        secret=MINIO_SECRET_KEY,
    )


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    )


def read_parquet_dataset(prefix: str) -> pd.DataFrame:
    fs = get_filesystem()
    files = [path for path in fs.find(f"{BUCKET}/{prefix}") if path.endswith(".parquet")]
    if not files:
        raise FileNotFoundError(f"No Parquet files found at s3://{BUCKET}/{prefix}")
    return pd.concat([pd.read_parquet(path, filesystem=fs) for path in files], ignore_index=True)


def write_parquet(dataframe: pd.DataFrame, key: str) -> None:
    fs = get_filesystem()
    with fs.open(f"{BUCKET}/{key}", "wb") as file:
        dataframe.to_parquet(file, index=False)
