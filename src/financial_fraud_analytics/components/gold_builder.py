import sys

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class GoldBuilder:
    """
    Enriched -> Gold business marts + star schema.

    Marts:  merchant_hourly_metrics, daily_customer_spend, fraud_rate_by_category,
            fraud_rate_by_state, top_merchants, high_risk_customers
    Star:   dim_merchant, dim_customer, dim_date, fact_transactions

    Mart builders are public methods taking a DataFrame, so each aggregation is
    independently testable. build() reads once and writes them all.
    """

    def __init__(self, config, spark):
        self.config = config
        self.spark = spark

    # ---------------- marts ----------------
    def merchant_hourly_metrics(self, df):
        from pyspark.sql import functions as F
        return (df.groupBy("merchant_id", "event_date", "event_hour")
                  .agg(F.count("*").alias("txn_count"),
                       F.round(F.sum("amount"), 2).alias("total_amount"),
                       F.sum("is_fraud").alias("fraud_count"),
                       F.round(F.avg("is_fraud"), 4).alias("fraud_rate")))

    def daily_customer_spend(self, df):
        from pyspark.sql import functions as F
        return (df.groupBy("customer_id", "event_date")
                  .agg(F.round(F.sum("amount"), 2).alias("total_spend"),
                       F.count("*").alias("txn_count"),
                       F.round(F.avg("amount"), 2).alias("avg_amount")))

    def fraud_rate_by_category(self, df):
        from pyspark.sql import functions as F
        return (df.groupBy("category")
                  .agg(F.count("*").alias("txn_count"),
                       F.sum("is_fraud").alias("fraud_count"),
                       F.round(F.avg("is_fraud"), 4).alias("fraud_rate"))
                  .orderBy(F.desc("fraud_rate")))

    def fraud_rate_by_state(self, df):
        from pyspark.sql import functions as F
        return (df.groupBy("state")
                  .agg(F.count("*").alias("txn_count"),
                       F.sum("is_fraud").alias("fraud_count"),
                       F.round(F.avg("is_fraud"), 4).alias("fraud_rate"))
                  .orderBy(F.desc("fraud_rate")))

    def top_merchants(self, df):
        from pyspark.sql import functions as F
        return (df.groupBy("merchant_id")
                  .agg(F.count("*").alias("txn_count"),
                       F.round(F.sum("amount"), 2).alias("total_amount"),
                       F.sum("is_fraud").alias("fraud_count"))
                  .orderBy(F.desc("total_amount"))
                  .limit(self.config.top_n_merchants))

    def high_risk_customers(self, df):
        from pyspark.sql import functions as F
        return (df.groupBy("customer_id")
                  .agg(F.count("*").alias("txn_count"),
                       F.sum("is_fraud").alias("fraud_count"),
                       F.round(F.avg("is_fraud"), 4).alias("fraud_rate"))
                  .filter(F.col("fraud_count") >= self.config.high_risk_min_fraud)
                  .orderBy(F.desc("fraud_count")))

    # ---------------- star schema ----------------
    def dim_merchant(self, df):
        # one row per merchant (category/state vary per txn, so they live on the fact)
        return df.select("merchant_id").distinct()

    def dim_customer(self, df):
        return df.select("customer_id").distinct()

    def dim_date(self, df):
        from pyspark.sql import functions as F
        return (df.select("event_date").distinct()
                  .withColumn("year", F.year("event_date"))
                  .withColumn("month", F.month("event_date"))
                  .withColumn("day", F.dayofmonth("event_date"))
                  .withColumn("day_of_week", F.dayofweek("event_date"))
                  .withColumn("is_weekend", F.dayofweek("event_date").isin(1, 7)))

    def fact_transactions(self, df):
        return df.select("transaction_id", "customer_id", "merchant_id",
                         "category", "state", "event_date", "amount", "is_fraud")

    # ---------------- orchestration ----------------
    def build(self, enriched_dir=None):
        try:
            logger.info("GOLD: starting")
            source = enriched_dir or str(self.config.enriched_path / "transactions")
            df = self.spark.read.parquet(str(source)).cache()
            logger.info(f"GOLD: read {df.count()} enriched rows from {source}")

            marts = {
                "merchant_hourly_metrics": self.merchant_hourly_metrics(df),
                "daily_customer_spend": self.daily_customer_spend(df),
                "fraud_rate_by_category": self.fraud_rate_by_category(df),
                "fraud_rate_by_state": self.fraud_rate_by_state(df),
                "top_merchants": self.top_merchants(df),
                "high_risk_customers": self.high_risk_customers(df),
                "dim_merchant": self.dim_merchant(df),
                "dim_customer": self.dim_customer(df),
                "dim_date": self.dim_date(df),
                "fact_transactions": self.fact_transactions(df),
            }

            for name, mart_df in marts.items():
                out = str(self.config.gold_path / name)
                (mart_df.coalesce(1).write.mode("overwrite")
                        .option("compression", self.config.compression).parquet(out))
                logger.info(f"GOLD: wrote {name} ({mart_df.count()} rows) -> {out}")

            df.unpersist()
            logger.info("GOLD: finished")
            return str(self.config.gold_path)

        except Exception:
            raise DataPlatformException("Gold build failed", "GOLD", sys)