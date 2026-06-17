"""
Gold stage on Spark: Silver -> Enriched -> Gold marts + star schema.
Prereq: Silver parquet exists (run the silver stage first).
Run:  python scripts/run_gold_spark.py
"""
from financial_fraud_analytics.config.configuration import ConfigurationManager
from financial_fraud_analytics.components.enrichment import EnrichmentProcessor
from financial_fraud_analytics.components.gold_builder import GoldBuilder
from financial_fraud_analytics.utils.spark_session import get_spark_session
from financial_fraud_analytics.logger.logging import get_logger

logger = get_logger()


def main():
    cm = ConfigurationManager()
    spark = get_spark_session(cm.get_spark_config())
    try:
        EnrichmentProcessor(cm.get_enrichment_config(), spark).enrich()
        out = GoldBuilder(cm.get_gold_config(), spark).build()
        logger.info(f"Gold stage complete -> {out}")
        print(f"Gold marts written under: {out}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()