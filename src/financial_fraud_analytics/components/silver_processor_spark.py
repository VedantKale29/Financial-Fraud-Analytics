import sys

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()

# map our contract dtype strings -> Spark cast types
_SPARK_TYPE = {
    "int64": "bigint",
    "float64": "double",
    "string": "string",
}


class SilverProcessorSpark:
    """
    Spark equivalent of SilverProcessor. Same rules, same order:
        schema enforce -> null handling -> validity -> watermark -> dedup -> reconcile.
    """

    def __init__(self, config, spark_config, spark):
        self.config = config
        self.spark_config = spark_config
        self.spark = spark

    def _enforce_schema(self, df):
        missing = [c for c in self.config.schema if c not in df.columns]
        if missing:
            raise DataPlatformException(
                f"Schema violation: missing columns {missing}", "SILVER", sys
            )
        for col, dtype in self.config.schema.items():
            spark_type = _SPARK_TYPE.get(dtype, dtype)
            df = df.withColumn(col, df[col].cast(spark_type))
        return df

    def process(self, bronze_dir=None):
        try:
            from pyspark.sql import functions as F
            logger.info("SILVER(spark): starting")

            source = bronze_dir or str(self.config.bronze_path / "transactions")
            df = self.spark.read.parquet(str(source))
            bronze_rows = df.count()
            logger.info(f"SILVER(spark): read {bronze_rows} bronze rows from {source}")

            # 1. schema enforcement
            df = self._enforce_schema(df)
            logger.info("SILVER(spark): schema enforced")

            # 2. null handling
            before = df.count()
            df = df.dropna(subset=self.config.not_null_columns)
            dropped_null = before - df.count()
            logger.info(f"SILVER(spark): dropped {dropped_null} rows with nulls")

            # 3. validity
            before = df.count()
            df = df.filter(F.col("amount") >= self.config.min_amount)
            dropped_invalid = before - df.count()
            logger.info(f"SILVER(spark): dropped {dropped_invalid} invalid-amount rows")

            # 4. watermark (late-arrival rejection vs latest dt in batch)
            dropped_late = 0
            if "dt" in df.columns and df.count() > 0:
                max_dt = df.agg(F.max(F.to_date("dt")).alias("m")).collect()[0]["m"]
                if max_dt is not None:
                    before = df.count()
                    df = df.filter(
                        F.to_date("dt") >= F.date_sub(F.lit(max_dt),
                                                       self.config.watermark_days)
                    )
                    dropped_late = before - df.count()
            logger.info(f"SILVER(spark): dropped {dropped_late} late-arriving rows")

            # 5. deduplication
            before = df.count()
            df = df.dropDuplicates(self.config.dedup_keys)
            silver_rows = df.count()
            dropped_dupes = before - silver_rows
            ratio = (dropped_dupes / before) if before else 0.0
            logger.info(
                f"SILVER(spark): dropped {dropped_dupes} duplicates "
                f"(ratio={ratio:.4f}) on {self.config.dedup_keys}"
            )

            if silver_rows > bronze_rows:
                raise DataPlatformException(
                    f"Reconciliation failed: silver={silver_rows} > bronze={bronze_rows}",
                    "SILVER", sys,
                )
            logger.info(
                f"SILVER(spark): reconciliation OK  bronze={bronze_rows} -> silver={silver_rows} "
                f"(nulls={dropped_null}, invalid={dropped_invalid}, "
                f"late={dropped_late}, dupes={dropped_dupes})"
            )

            output_dir = str(self.config.silver_path / "transactions")
            (df.coalesce(self.spark_config.output_files_per_partition)
               .write.mode("overwrite")
               .partitionBy(*self.config.partition_cols)
               .option("compression", self.config.compression)
               .parquet(output_dir))
            logger.info(f"SILVER(spark): wrote parquet to {output_dir}")
            logger.info("SILVER(spark): finished")
            return output_dir

        except DataPlatformException:
            raise
        except Exception:
            raise DataPlatformException("Silver(spark) processing failed", "SILVER", sys)