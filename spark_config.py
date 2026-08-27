from pyspark.sql import SparkSession
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
SPARK_LOCAL_DIR = os.getenv("SPARK_LOCAL_DIR", tempfile.gettempdir())

if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
    raise RuntimeError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be set.")

def get_spark_session(app_name: str):
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT) \
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.jars.packages", "org.apache.spark:spark-hadoop-cloud_2.13:4.0.1") \
        .config("spark.local.dir", SPARK_LOCAL_DIR) \
        .config("spark.hadoop.fs.s3a.buffer.dir", SPARK_LOCAL_DIR) \
        .getOrCreate()
