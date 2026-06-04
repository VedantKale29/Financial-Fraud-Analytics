import sys
from datetime import datetime, timezone

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class BronzeWriterSpark:
    """
    Spark equivalent of BronzeWriter. Same contract:
        clean CSV -> add ingestion-date dt -> partitioned parquet -> reconcile.
    Engine swapped to PySpark; business logic identical.
    """

    def __init__(self, config, spark_config, spark):
        self.config = config
        self.spark_config = spark_config
        self.spark = spark

    def write(self, input_file):
        try:
            from pyspark.sql import functions as F
            logger.info("BRONZE(spark): starting parquet write")

            df = self.spark.read.csv(str(input_file), header=True, inferSchema=True)
            source_rows = df.count()
            logger.info(f"BRONZE(spark): read {source_rows} rows from {input_file}")

            ingestion_dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            df = df.withColumn("dt", F.lit(ingestion_dt))
            logger.info(f"BRONZE(spark): tagged partition dt={ingestion_dt}")

            output_dir = str(self.config.bronze_path / "transactions")

            # coalesce -> control files per partition (small-files fix)
            (df.coalesce(self.spark_config.output_files_per_partition)
               .write.mode("overwrite")
               .partitionBy(*self.config.partition_cols)
               .option("compression", self.config.compression)
               .parquet(output_dir))
            logger.info(f"BRONZE(spark): wrote parquet to {output_dir}")

            written_rows = self.spark.read.parquet(output_dir).count()
            if written_rows != source_rows:
                raise DataPlatformException(
                    f"Row count mismatch: source={source_rows} written={written_rows}",
                    "BRONZE", sys,
                )
            logger.info(f"BRONZE(spark): reconciliation OK ({written_rows} rows preserved)")
            logger.info("BRONZE(spark): finished")
            return output_dir

        except DataPlatformException:
            raise
        except Exception:
            raise DataPlatformException("Bronze(spark) parquet write failed", "BRONZE", sys)