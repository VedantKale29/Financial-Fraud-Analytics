"""
Execution entry point for the Bronze Parquet stage.

Flow:
    raw CSV -> transformation (clean CSV) -> bronze writer (partitioned parquet)

Run from project root:
    python scripts/run_bronze_local.py
"""
from financial_fraud_analytics.config.configuration import ConfigurationManager
from financial_fraud_analytics.components.transformation import DataTransformation
from financial_fraud_analytics.components.bronze_writer import BronzeWriter
from financial_fraud_analytics.logger.logging import get_logger

logger = get_logger()


def main():
    cm = ConfigurationManager()

    # produce the clean CSV (existing transformation component)
    transformation_config = cm.get_transformation_config()
    raw_file = transformation_config.raw_path / "transactions.csv"
    clean_csv = DataTransformation(transformation_config).transform(raw_file)

    # promote it to partitioned parquet (new bronze component)
    bronze_config = cm.get_bronze_config()
    output = BronzeWriter(bronze_config).write(clean_csv)

    logger.info(f"Bronze stage complete -> {output}")
    print(f"Bronze parquet written to: {output}")


if __name__ == "__main__":
    main()