import sys
import json
import time
import numpy as np
import pandas as pd

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


def _json_default(o):
    # make numpy scalars JSON-serializable as native numbers
    if isinstance(o, np.generic):
        return o.item()
    return str(o)


class KafkaProducer:
    """
    Streams transaction rows from a CSV into a Kafka topic as JSON messages.
    Config-driven; delivery callbacks; optional real-time throttle.
    `producer` can be injected (for tests); otherwise built from config.
    """

    def __init__(self, config, producer=None):
        self.config = config
        self._producer = producer

    def _delivery_report(self, err, msg):
        if err is not None:
            logger.error(f"KAFKA: delivery failed: {err}")

    def _get_producer(self):
        if self._producer is None:
            from financial_fraud_analytics.utils.kafka_factory import get_producer
            self._producer = get_producer(self.config)
        return self._producer

    def produce_from_csv(self, csv_path):
        try:
            logger.info(f"KAFKA: producing from {csv_path}")
            df = pd.read_csv(csv_path)
            producer = self._get_producer()
            topic = self.config.topic

            sent = 0
            for record in df.to_dict(orient="records"):
                payload = json.dumps(record, default=_json_default).encode("utf-8")
                producer.produce(topic, value=payload, callback=self._delivery_report)
                producer.poll(0)  # serve delivery callbacks
                sent += 1
                if self.config.throttle_ms:
                    time.sleep(self.config.throttle_ms / 1000.0)

            producer.flush()
            logger.info(f"KAFKA: produced {sent} messages to topic '{topic}'")
            return sent

        except Exception:
            raise DataPlatformException("Kafka produce failed", "KAFKA", sys)