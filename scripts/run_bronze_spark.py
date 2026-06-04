"""
Bronze stage on Spark.
Flow: raw CSV -> transformation (clean CSV) -> Spark bronze writer -> parquet.
Run:  python scripts/run_bronze_spark.py
"""
from financial_fraud_analytics.config.configuration import ConfigurationManager
from financial_fraud_analytics.components.transformation import DataTransformation
from financial_fraud_analytics.components.bronze_writer_spark import BronzeWriterSpark
from financial_fraud_analytics.utils.spark_session import get_spark_session
from financial_fraud_analytics.logger.logging import get_logger

logger = get_logger()


def main():
    cm = ConfigurationManager()
    tcfg = cm.get_transformation_config()
    raw_file = tcfg.raw_path / "transactions.csv"
    clean_csv = DataTransformation(tcfg).transform(raw_file)

    spark_cfg = cm.get_spark_config()
    spark = get_spark_session(spark_cfg)
    try:
        out = BronzeWriterSpark(cm.get_bronze_config(), spark_cfg, spark).write(clean_csv)
        logger.info(f"Bronze(spark) complete -> {out}")
        print(f"Bronze parquet written to: {out}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()