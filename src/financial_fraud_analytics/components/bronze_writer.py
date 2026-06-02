import sys
import pandas as pd
from datetime import datetime, timezone

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class BronzeWriter:
    """
    Promotes the cleaned Bronze CSV into a partitioned Parquet lake table.

    One job only:
        clean CSV  ->  add ingestion-date partition (dt)  ->  partitioned parquet
        ->  read back  ->  reconcile row count
    """

    def __init__(self, config):
        self.config = config

    def write(self, input_file):
        try:
            logger.info("BRONZE: starting parquet write")

            df = pd.read_csv(input_file)
            source_rows = len(df)
            logger.info(f"BRONZE: read {source_rows} rows from {input_file}")

            # ingestion-date partition (arrival date, UTC) — Bronze convention
            ingestion_dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            df["dt"] = ingestion_dt
            logger.info(f"BRONZE: tagged partition dt={ingestion_dt}")

            output_dir = self.config.bronze_path / "transactions"

            # idempotent reload: overwrite this partition's data, never append duplicates
            df.to_parquet(
                output_dir,
                engine="pyarrow",
                compression=self.config.compression,
                partition_cols=self.config.partition_cols,
                index=False,
                existing_data_behavior="delete_matching",
            )
            logger.info(f"BRONZE: wrote parquet to {output_dir}")

            # ---- reconciliation: read back and confirm no rows lost ----
            written = pd.read_parquet(output_dir, engine="pyarrow")
            written_rows = len(written)

            if written_rows != source_rows:
                raise DataPlatformException(
                    f"Row count mismatch: source={source_rows} written={written_rows}",
                    "BRONZE",
                    sys,
                )

            logger.info(
                f"BRONZE: reconciliation OK ({written_rows} rows preserved)"
            )
            logger.info("BRONZE: parquet write finished")

            return output_dir

        except DataPlatformException:
            raise
        except Exception:
            raise DataPlatformException("Bronze parquet write failed", "BRONZE", sys)