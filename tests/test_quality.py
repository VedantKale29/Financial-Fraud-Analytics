import pandas as pd
from pathlib import Path


def test_no_null_values():

    file_path = Path("data/raw/transactions.csv")

    df = pd.read_csv(file_path)

    assert df.isnull().sum().sum() == 0



def test_amount_positive():

    file_path = Path("data/processed/bronze/transactions_clean.csv")

    df = pd.read_csv(file_path)

    assert (df["amount"] >= 0).all()



def test_has_fraud_column():

    file_path = Path("data/processed/bronze/transactions_clean.csv")

    df = pd.read_csv(file_path)

    assert "is_fraud" in df.columns