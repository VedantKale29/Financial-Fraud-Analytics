"""
Execution entry point for the Silver stage.

Flow:
    Bronze parquet -> silver processor -> Silver parquet

Prerequisite: run scripts/run_bronze_local.py first so Bronze parquet exists.

Run from project root:
    python scripts/run_silver_local.py
"""
from financial_fraud_analytics.config.configuration import ConfigurationManager
from financial_fraud_analytics.components.silver_processor import SilverProcessor
from financial_fraud_analytics.logger.logging import get_logger

logger = get_logger()


def main():
    cm = ConfigurationManager()
    silver_config = cm.get_silver_config()
    output = SilverProcessor(silver_config).process()
    logger.info(f"Silver stage complete -> {output}")
    print(f"Silver parquet written to: {output}")


if __name__ == "__main__":
    main()