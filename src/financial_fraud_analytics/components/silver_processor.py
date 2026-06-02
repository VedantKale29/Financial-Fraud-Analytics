import sys
import pandas as pd

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class SilverProcessor:
    """
    Bronze parquet -> clean, conformed, deduplicated Silver parquet.

    One job only. Applies, in order:
        1. schema enforcement   (columns present + cast to contract types)
        2. null handling        (drop rows null in not_null_columns)
        3. validity             (amount >= min_amount)
        4. watermark            (reject events older than watermark_days vs latest dt)
        5. deduplication        (on dedup_keys, keep first)
    Then writes partitioned parquet and reconciles silver_rows <= bronze_rows,
    logging exactly how many rows each rule dropped.
    """

    def __init__(self, config):
        self.config = config

    def _enforce_schema(self, df):
        # all contract columns must be present
        missing = [c for c in self.config.schema if c not in df.columns]
        if missing:
            raise DataPlatformException(
                f"Schema violation: missing columns {missing}", "SILVER", sys
            )
        # cast each column to its contract dtype
        for col, dtype in self.config.schema.items():
            try:
                df[col] = df[col].astype(dtype)
            except Exception:
                raise DataPlatformException(
                    f"Schema violation: cannot cast '{col}' to {dtype}", "SILVER", sys
                )
        return df

    def process(self, bronze_dir=None):
        try:
            logger.info("SILVER: starting")

            source = bronze_dir or (self.config.bronze_path / "transactions")
            df = pd.read_parquet(source, engine="pyarrow")
            bronze_rows = len(df)
            logger.info(f"SILVER: read {bronze_rows} bronze rows from {source}")

            # 1. schema enforcement
            df = self._enforce_schema(df)
            logger.info("SILVER: schema enforced")

            # 2. null handling
            before = len(df)
            df = df.dropna(subset=self.config.not_null_columns)
            dropped_null = before - len(df)
            logger.info(f"SILVER: dropped {dropped_null} rows with nulls")

            # 3. validity
            before = len(df)
            df = df[df["amount"] >= self.config.min_amount]
            dropped_invalid = before - len(df)
            logger.info(f"SILVER: dropped {dropped_invalid} invalid-amount rows")

            # 4. watermark (late-arrival rejection)
            dropped_late = 0
            if "dt" in df.columns and len(df) > 0:
                # parquet restores partition cols as unordered Categorical;
                # cast to str first so to_datetime yields a plain datetime Series
                dt = pd.to_datetime(df["dt"].astype(str))
                cutoff = dt.max() - pd.Timedelta(days=self.config.watermark_days)
                before = len(df)
                df = df[(dt >= cutoff).to_numpy()]
                dropped_late = before - len(df)
            logger.info(f"SILVER: dropped {dropped_late} late-arriving rows")

            # 5. deduplication
            before = len(df)
            df = df.drop_duplicates(subset=self.config.dedup_keys, keep="first")
            dropped_dupes = before - len(df)
            ratio = (dropped_dupes / before) if before else 0.0
            logger.info(
                f"SILVER: dropped {dropped_dupes} duplicates "
                f"(ratio={ratio:.4f}) on {self.config.dedup_keys}"
            )

            silver_rows = len(df)

            # reconciliation: silver can only shrink relative to bronze
            if silver_rows > bronze_rows:
                raise DataPlatformException(
                    f"Reconciliation failed: silver={silver_rows} > bronze={bronze_rows}",
                    "SILVER", sys,
                )
            logger.info(
                f"SILVER: reconciliation OK  bronze={bronze_rows} -> silver={silver_rows} "
                f"(nulls={dropped_null}, invalid={dropped_invalid}, "
                f"late={dropped_late}, dupes={dropped_dupes})"
            )

            output_dir = self.config.silver_path / "transactions"
            df.to_parquet(
                output_dir,
                engine="pyarrow",
                compression=self.config.compression,
                partition_cols=self.config.partition_cols,
                index=False,
                existing_data_behavior="delete_matching",
            )
            logger.info(f"SILVER: wrote parquet to {output_dir}")
            logger.info("SILVER: finished")

            return output_dir

        except DataPlatformException:
            raise
        except Exception:
            raise DataPlatformException("Silver processing failed", "SILVER", sys)