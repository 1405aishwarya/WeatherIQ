from functools import reduce
import sys

from pyspark.sql.functions import col, lit

from spark_config import get_spark_session
from storage_utils import BUCKET, get_s3_client


EXPECTED_COLUMNS = {
    "city": "string",
    "latitude": "double",
    "longitude": "double",
    "temp": "double",
    "humidity": "integer",
    "pressure": "double",
    "wind_speed": "double",
    "weather_code": "integer",
    "timestamp": "string",
}


def bronze_paths() -> list[str]:
    paginator = get_s3_client().get_paginator("list_objects_v2")
    paths = []
    for page in paginator.paginate(Bucket=BUCKET, Prefix="bronze/"):
        paths.extend(
            f"s3a://{BUCKET}/{item['Key']}"
            for item in page.get("Contents", [])
            if item["Key"].endswith(".parquet")
        )
    return sorted(paths)


def normalize_schema(dataframe):
    available = set(dataframe.columns)
    return dataframe.select(
        *[
            col(name).cast(data_type).alias(name)
            if name in available
            else lit(None).cast(data_type).alias(name)
            for name, data_type in EXPECTED_COLUMNS.items()
        ]
    )


try:
    spark = get_spark_session("BronzeToSilver")
    spark.range(1).count()
    print("Spark session initialized successfully!")
except Exception as error:
    print("ERROR: Failed to create Spark session:", str(error))
    sys.exit(1)

try:
    paths = bronze_paths()
    if not paths:
        raise FileNotFoundError("No Parquet files found in bronze/")
    frames = [normalize_schema(spark.read.parquet(path)) for path in paths]
    df = reduce(lambda left, right: left.unionByName(right), frames)
    record_count = df.count()
    print(f"Successfully read {record_count} records from {len(paths)} Bronze files.")
except Exception as error:
    print("ERROR: Failed to read Bronze files:", str(error))
    spark.stop()
    sys.exit(1)

try:
    validation_rule = (
        col("city").isNotNull()
        & col("timestamp").isNotNull()
        & col("temp").between(-90, 60)
        & col("humidity").between(0, 100)
        & col("pressure").between(800, 1100)
        & col("wind_speed").between(0, 200)
    )
    invalid_df = df.filter(~validation_rule)
    invalid_count = invalid_df.count()
    if invalid_count > 0:
        invalid_df.write.mode("append").parquet(f"s3a://{BUCKET}/quarantine/invalid_weather/")
        print(f"Validation rejected {invalid_count} records.")

    df_clean = df.filter(validation_rule).dropDuplicates(["timestamp", "city"])
    clean_count = df_clean.count()
    if clean_count == 0:
        raise RuntimeError("No valid Bronze records remain after validation.")
    print(f"After cleaning: {clean_count} records remain.")
    df_clean.show(10, truncate=False)
except Exception as error:
    print("ERROR: Failed during data cleaning:", str(error))
    spark.stop()
    sys.exit(1)

try:
    (
        df_clean.write.mode("overwrite")
        .option("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
        .parquet(f"s3a://{BUCKET}/silver/")
    )
    print("Successfully wrote cleaned data to silver layer!")
except Exception as error:
    print("ERROR: Failed to write to silver layer:", str(error))
    spark.stop()
    sys.exit(1)

spark.stop()
print("Bronze to Silver job completed successfully!")
