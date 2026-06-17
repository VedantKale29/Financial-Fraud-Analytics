"""
Consume Kafka -> Bronze parquet via Spark Structured Streaming.
Prereq: Kafka running and producer has published messages.
Needs the Kafka connector JAR (provided via --packages or spark.jars.packages).
Run:  python scripts/run_streaming_local.py
"""
from financial_fraud_analytics.config.configuration import ConfigurationManager
from financial_fraud_analytics.components.streaming_consumer import StreamingConsumer
from financial_fraud_analytics.utils.spark_session import get_spark_session
from financial_fraud_analytics.logger.logging import get_logger

logger = get_logger()


def main():
    cm = ConfigurationManager()
    spark = get_spark_session(cm.get_spark_config(), with_kafka=True)
    try:
        StreamingConsumer(cm.get_kafka_config(), cm.get_streaming_config(), spark).run()
        print("Streaming batch complete -> Bronze")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()