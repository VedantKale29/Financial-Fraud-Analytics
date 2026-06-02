import pandas as pd
from pathlib import Path

from financial_fraud_analytics.utils.utils import read_yaml
from financial_fraud_analytics.constants.constants import SCHEMA_FILE_PATH


def test_schema_columns():

    schema = read_yaml(SCHEMA_FILE_PATH)

    file_path = Path("data/processed/bronze/transactions_clean.csv")

    df = pd.read_csv(file_path)

    expected_columns = schema["facts"]["fact_transactions"]["columns"]

    for col in expected_columns:

        assert col in df.columns