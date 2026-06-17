"""
Publish transactions to Kafka.
Prereq: Kafka running (docker compose up -d) + clean CSV exists.
Run:  python scripts/run_producer.py
"""
from financial_fraud_analytics.config.configuration import ConfigurationManager
from financial_fraud_analytics.components.transformation import DataTransformation
from financial_fraud_analytics.components.kafka_producer import KafkaProducer
from financial_fraud_analytics.logger.logging import get_logger

logger = get_logger()


def main():
    cm = ConfigurationManager()
    tcfg = cm.get_transformation_config()
    clean_csv = DataTransformation(tcfg).transform(tcfg.raw_path / "transactions.csv")

    sent = KafkaProducer(cm.get_kafka_config()).produce_from_csv(clean_csv)
    print(f"Produced {sent} messages")


if __name__ == "__main__":
    main()