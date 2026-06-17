import sys

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


def get_spark_session(config, with_kafka=False):
    """
    Build a config-driven SparkSession.
    Only `master` changes between local and EMR — business code stays identical.
    """
    try:
        import os
        # Spark launches its Python workers via PYSPARK_PYTHON; on Windows the
        # default 'python3' does not exist (only python.exe), which fails task
        # execution with 'CreateProcess error=2'. Pin both to THIS interpreter.
        os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
        os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

        from pyspark.sql import SparkSession

        builder = (
            SparkSession.builder
            .appName(config.app_name)
            .master(config.master)
            .config("spark.sql.shuffle.partitions", config.shuffle_partitions)
            .config("spark.ui.enabled", "false")
        )
        # Kafka connector only when explicitly needed (streaming job),
        # so batch jobs (bronze/silver/gold) never touch Maven.
        packages = getattr(config, "jars_packages", None)
        if with_kafka and packages:
            builder = builder.config("spark.jars.packages", packages)
        spark = (
            builder.getOrCreate()
        )
        spark.sparkContext.setLogLevel("ERROR")
        logger.info(f"SPARK: session ready (master={config.master})")
        return spark

    except Exception:
        raise DataPlatformException("Failed to create SparkSession", "SPARK", sys)