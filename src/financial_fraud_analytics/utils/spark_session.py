import sys

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


def get_spark_session(config):
    """
    Build a config-driven SparkSession.
    Only `master` changes between local and EMR — business code stays identical.
    """
    try:
        from pyspark.sql import SparkSession

        spark = (
            SparkSession.builder
            .appName(config.app_name)
            .master(config.master)
            .config("spark.sql.shuffle.partitions", config.shuffle_partitions)
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("ERROR")
        logger.info(f"SPARK: session ready (master={config.master})")
        return spark

    except Exception:
        raise DataPlatformException("Failed to create SparkSession", "SPARK", sys)