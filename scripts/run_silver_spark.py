"""
Silver stage on Spark.
Prerequisite: Bronze parquet exists (run run_bronze_spark.py first).
Run:  python scripts/run_silver_spark.py
"""
from financial_fraud_analytics.config.configuration import ConfigurationManager
from financial_fraud_analytics.components.silver_processor_spark import SilverProcessorSpark
from financial_fraud_analytics.utils.spark_session import get_spark_session
from financial_fraud_analytics.logger.logging import get_logger

logger = get_logger()


def main():
    cm = ConfigurationManager()
    spark_cfg = cm.get_spark_config()
    spark = get_spark_session(spark_cfg)
    try:
        out = SilverProcessorSpark(cm.get_silver_config(), spark_cfg, spark).process()
        logger.info(f"Silver(spark) complete -> {out}")
        print(f"Silver parquet written to: {out}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()