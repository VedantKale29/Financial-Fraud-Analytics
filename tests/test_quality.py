import pandas as pd
from pathlib import Path

from financial_fraud_analytics.utils.utils import read_yaml
from financial_fraud_analytics.constants.constants import CONFIG_FILE_PATH

_config = read_yaml(CONFIG_FILE_PATH)
RAW = Path(_config["paths"]["raw"])
BRONZE = Path(_config["paths"]["bronze"])


def test_no_null_values():
    df = pd.read_csv(RAW / "transactions.csv")
    assert df.isnull().sum().sum() == 0


def test_amount_positive():
    df = pd.read_csv(BRONZE / "transactions_clean.csv")
    assert (df["amount"] >= 0).all()


def test_has_fraud_column():
    df = pd.read_csv(BRONZE / "transactions_clean.csv")
    assert "is_fraud" in df.columns