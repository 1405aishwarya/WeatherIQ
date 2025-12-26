# spark_config.py
from pyspark.sql import SparkSession

def get_spark_session(app_name: str):
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.jars.packages", "org.apache.spark:spark-hadoop-cloud_2.13:4.0.1") \
        .config("spark.local.dir", "C:/tmp/spark") \
        .config("spark.hadoop.fs.s3a.buffer.dir", "C:/tmp/s3a_buffer") \
        .getOrCreate()