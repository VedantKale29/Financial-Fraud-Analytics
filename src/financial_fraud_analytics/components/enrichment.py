import sys

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class EnrichmentProcessor:
    """
    Silver -> Enriched.  Adds the business dimensions Gold needs.

    IMPORTANT (honesty): merchant_id / category / state / customer_id are
    DETERMINISTICALLY DERIVED from transaction_id, and event_time is built from
    a configured base_date + date_key seconds. These are SYNTHETIC dimensions for
    demonstrating dimensional modeling; they have no real relationship to is_fraud.
    """

    def __init__(self, config, spark):
        self.config = config
        self.spark = spark

    def enrich(self, silver_dir=None):
        try:
            from pyspark.sql import functions as F
            logger.info("ENRICH: starting")

            source = silver_dir or str(self.config.silver_path / "transactions")
            df = self.spark.read.parquet(str(source))
            rows = df.count()
            logger.info(f"ENRICH: read {rows} silver rows from {source}")

            n_m = self.config.num_merchants
            n_c = self.config.num_customers
            cats = self.config.categories
            states = self.config.states

            cat_arr = F.array(*[F.lit(c) for c in cats])
            state_arr = F.array(*[F.lit(s) for s in states])

            tid = F.col("transaction_id")

            df = (
                df
                # synthetic customer spread (overrides the constant Silver value)
                .withColumn("customer_id", (tid % F.lit(n_c)).cast("long"))
                .withColumn("merchant_id", F.concat(F.lit("M"), (tid % F.lit(n_m)).cast("int")))
                .withColumn("category", F.element_at(cat_arr, ((tid % F.lit(len(cats))) + 1).cast("int")))
                .withColumn("state", F.element_at(state_arr, ((tid % F.lit(len(states))) + 1).cast("int")))
                # event_time = base_date + date_key seconds
                .withColumn(
                    "event_time",
                    F.from_unixtime(
                        F.unix_timestamp(F.lit(self.config.base_date), "yyyy-MM-dd")
                        + F.col("date_key").cast("long")
                    ).cast("timestamp"),
                )
                .withColumn("event_date", F.to_date("event_time"))
                .withColumn("event_hour", F.hour("event_time"))
            )

            output_dir = str(self.config.enriched_path / "transactions")
            (df.write.mode("overwrite")
               .partitionBy(*self.config.partition_cols)
               .option("compression", self.config.compression)
               .parquet(output_dir))
            logger.info(f"ENRICH: wrote {rows} enriched rows to {output_dir}")
            logger.info("ENRICH: finished")
            return output_dir

        except Exception:
            raise DataPlatformException("Enrichment failed", "ENRICH", sys)