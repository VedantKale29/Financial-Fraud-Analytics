import sys
import pandas as pd

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class DataTransformation:

    def __init__(self, config):

        self.config = config


    def transform(self, input_file):

        try:

            logger.info("Starting transformation")

            df = pd.read_csv(input_file)

            # ===============================
            # rename columns
            # ===============================

            df = df.rename(
                columns={
                    "Amount": "amount",
                    "Class": "is_fraud",
                    "Time": "date_key",
                }
            )

            # ===============================
            # create required columns
            # ===============================

            df["transaction_id"] = df.index

            df["customer_id"] = 1

            df["account_id"] = 1

            # ===============================
            # reorder columns
            # ===============================

            df = df[
                [
                    "transaction_id",
                    "customer_id",
                    "account_id",
                    "date_key",
                    "amount",
                    "is_fraud",
                ]
            ]

            output_file = self.config.bronze_path / "transactions_clean.csv"

            df.to_csv(output_file, index=False)

            logger.info("Transformation finished")

            return output_file

        except Exception as e:

            raise DataPlatformException(
                "Transformation failed",
                "TRANSFORMATION",
                sys,
            )