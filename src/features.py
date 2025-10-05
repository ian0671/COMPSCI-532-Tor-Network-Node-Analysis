# join + compute featuresa
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, length

def build_features(relay_path, enrich_path):
    spark = SparkSession.builder.appName("TorFeatures").getOrCreate()
    relays = spark.read.parquet(relay_path)
    enrich = spark.read.json(enrich_path)

    df = relays.join(enrich, "ip", "left")
    df = df.withColumn("is_exit", col("flags").contains("Exit"))
    df = df.withColumn("ip_len", length(col("ip")))
    df.write.mode("overwrite").parquet("data/features/tor_features.parquet")
    spark.stop()
