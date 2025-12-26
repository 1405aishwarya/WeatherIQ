from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, to_date, year, month
from spark_config import get_spark_session
import sys

# Use the configured Spark session from spark_config.py (includes all MinIO fixes)
try:
    spark = get_spark_session("SilverToGold")
except Exception as e:
    print("ERROR: Failed to create Spark session:", str(e))
    sys.exit(1)

# Quick test to ensure Spark starts properly
try:
    spark.range(1).count()
    print("Spark session initialized successfully!")
except Exception as e:
    print("ERROR: Spark context failed to initialize:", str(e))
    sys.exit(1)

# Read from silver layer
try:
    df = spark.read.parquet("s3a://climate-lakehouse/silver/")
    record_count = df.count()
    print(f"Successfully read {record_count} records from silver layer.")
except Exception as e:
    print("ERROR: Failed to read from silver layer:", str(e))
    sys.exit(1)

# Convert timestamp to date
df = df.withColumn("date", to_date("timestamp"))

# Aggregate to daily averages
gold_daily = (df.groupBy("date", "city")
    .agg(
        avg("temp").alias("avg_temp"),
        avg("humidity").alias("avg_humidity"),
        avg("pressure").alias("avg_pressure"),
        avg("wind_speed").alias("avg_wind_speed")
    )
)

# Extract year and month for partitioning
gold_daily = gold_daily.withColumn("year", year("date")) \
                       .withColumn("month", month("date"))

# Debug: Show sample aggregated data
print("Sample of gold daily data:")
gold_daily.show(10, truncate=False)

# Write to gold layer with partitioning
try:
    (gold_daily
     .write
     .mode("overwrite")  # Clean write every time during development
     .partitionBy("year", "month")
     .parquet("s3a://climate-lakehouse/gold/daily/"))
    print("Successfully wrote aggregated data to gold/daily layer!")
except Exception as e:
    print("ERROR: Failed to write to gold layer:", str(e))
    sys.exit(1)

# Stop Spark gracefully
spark.stop()
print("Silver → Gold job completed successfully!")