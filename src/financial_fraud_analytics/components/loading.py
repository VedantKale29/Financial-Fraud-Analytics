import sys
import pandas as pd
from sqlalchemy import create_engine

from financial_fraud_analytics.utils.utils import get_database_uri
from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class DataLoading:

    def __init__(self, config):

        self.config = config


    def load(self, file_path):

        try:

            logger.info("Loading to warehouse")

            uri = get_database_uri(self.config)

            engine = create_engine(uri)

            df = pd.read_csv(file_path)

            df.to_sql(
                "fact_transactions",
                engine,
                if_exists="replace",
                index=False,
            )

            logger.info("Loading done")

        except Exception as e:

            raise DataPlatformException(
                "Loading failed",
                "LOADING",
                sys
            )