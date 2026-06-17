import sys

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


def get_producer(config):
    """Build a confluent-kafka Producer from config (lazy import so the module
    loads even where the client/broker is absent)."""
    try:
        from confluent_kafka import Producer
        producer = Producer({
            "bootstrap.servers": config.bootstrap_servers,
            "client.id": config.client_id,
        })
        logger.info(f"KAFKA: producer ready (servers={config.bootstrap_servers})")
        return producer
    except Exception:
        raise DataPlatformException("Failed to create Kafka producer", "KAFKA", sys)