from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import sys

# Get the configured Spark session (with MinIO settings from spark_config.py)
spark = None
try:
    from spark_config import get_spark_session
    spark = get_spark_session("BronzeToSilver")
except Exception as e:
    print("ERROR: Failed to create Spark session:", str(e))
    sys.exit(1)

# Quick test to force Spark context initialization — fails fast if something's wrong
try:
    spark.range(1).count()  # This triggers the Java backend immediately
    print("Spark session initialized successfully!")
except Exception as e:
    print("ERROR: Spark context failed to initialize:", str(e))
    sys.exit(1)

# Read from bronze layer
try:
    df = spark.read.parquet("s3a://climate-lakehouse/bronze/")
    record_count = df.count()
    print(f"Successfully read {record_count} records from bronze layer.")
    if record_count == 0:
        print("WARNING: No data in bronze layer. Run ingest.py first!")
except Exception as e:
    print("ERROR: Failed to read from bronze layer (check MinIO running + data exists):", str(e))
    sys.exit(1)

# Cleaning and transformation
try:
    df_clean = (df
        .dropDuplicates(["timestamp", "city"])
        .na.drop(subset=["temp", "humidity"])
        .withColumn("temp", col("temp").cast("double"))
        .withColumn("humidity", col("humidity").cast("integer"))
    )
    clean_count = df_clean.count()
    print(f"After cleaning: {clean_count} records remain.")
    
    # Debug: Show sample data before writing
    if clean_count > 0:
        print("Sample of cleaned data to be written to silver:")
        df_clean.show(10, truncate=False)
    else:
        print("No records left after cleaning. Nothing to write.")
except Exception as e:
    print("ERROR: Failed during data cleaning:", str(e))
    sys.exit(1)

# Write to silver layer (without partitioning to avoid MinIO issues)
try:
    if clean_count > 0:
        (df_clean
         .write
         .mode("overwrite")  # Overwrite for clean development runs
         .option("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")  # Ensures commit
         .parquet("s3a://climate-lakehouse/silver/"))
        print("Successfully wrote cleaned data to silver layer!")
    else:
        print("No data to write — skipping silver write.")
except Exception as e:
    print("ERROR: Failed to write to silver layer:", str(e))
    sys.exit(1)

# Graceful shutdown
spark.stop()
print("Bronze → Silver job completed successfully!")