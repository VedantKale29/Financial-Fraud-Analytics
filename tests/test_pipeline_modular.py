"""
Modular test suite for the current batch ETL pipeline.
Each STAGE is tested in isolation so a failure points to one component.
No real database and no real Kaggle file are required:
  - synthetic data mimics the Kaggle creditcard schema (Time, V1.., Amount, Class)
  - the DB load is monkeypatched (no Postgres needed)
Run:  pytest tests/test_pipeline_modular.py -v
"""
import sys
import types
import pandas as pd
import pytest
from pathlib import Path

from financial_fraud_analytics.components.extraction import DataExtraction
from financial_fraud_analytics.components.transformation import DataTransformation
from financial_fraud_analytics.components.loading import DataLoading
from financial_fraud_analytics.exception.exception import DataPlatformException
from financial_fraud_analytics.utils.utils import get_database_uri, read_yaml, create_directories
from financial_fraud_analytics.config.configuration import ConfigurationManager
from financial_fraud_analytics.constants.constants import CONFIG_FILE_PATH


# ---------- shared fixtures ----------
def _make_kaggle_like_csv(path: Path, rows: int = 5):
    """Build a tiny dataframe shaped like the Kaggle creditcard fraud dataset."""
    df = pd.DataFrame({
        "Time":   [float(i) for i in range(rows)],
        "V1":     [0.1 * i for i in range(rows)],
        "Amount": [10.0 * (i + 1) for i in range(rows)],
        "Class":  [0, 1, 0, 1, 0][:rows],
    })
    df.to_csv(path, index=False)
    return df


# ============================================================
# STAGE 0 — UTILS (pure functions, no I/O dependencies)
# ============================================================
def test_get_database_uri_builds_correct_postgres_string():
    cfg = {"database": {"user": "postgres", "password": "root",
                        "host": "localhost", "port": 5432, "db": "banking"}}
    uri = get_database_uri(cfg)
    assert uri == "postgresql://postgres:root@localhost:5432/banking"

def test_get_database_uri_missing_key_raises_dataplatform_exception():
    with pytest.raises(DataPlatformException):
        get_database_uri({"database": {"user": "postgres"}})  # missing keys

def test_create_directories(tmp_path):
    target = tmp_path / "a" / "b"
    create_directories([str(target)], verbose=False)
    assert target.exists()


# ============================================================
# STAGE 1 — EXTRACTION
# ============================================================
def test_extraction_writes_output_with_same_row_count(tmp_path):
    src = tmp_path / "source.csv"
    df = _make_kaggle_like_csv(src, rows=5)
    raw_dir = tmp_path / "raw"; raw_dir.mkdir()

    cfg = types.SimpleNamespace(source_file=str(src), raw_path=raw_dir)
    out = DataExtraction(cfg).extract()

    assert Path(out).exists()
    assert len(pd.read_csv(out)) == len(df)

def test_extraction_bad_source_raises(tmp_path):
    cfg = types.SimpleNamespace(source_file=str(tmp_path / "missing.csv"),
                                raw_path=tmp_path)
    with pytest.raises(DataPlatformException):
        DataExtraction(cfg).extract()


# ============================================================
# STAGE 2 — TRANSFORMATION (the real business logic)
# ============================================================
def test_transformation_output_schema_and_renames(tmp_path):
    src = tmp_path / "raw.csv"
    _make_kaggle_like_csv(src, rows=5)
    bronze = tmp_path / "bronze"; bronze.mkdir()

    cfg = types.SimpleNamespace(bronze_path=bronze)
    out = DataTransformation(cfg).transform(src)

    result = pd.read_csv(out)
    expected_cols = ["transaction_id", "customer_id", "account_id",
                     "date_key", "amount", "is_fraud"]
    assert list(result.columns) == expected_cols      # rename + reorder correct
    assert len(result) == 5                            # no rows dropped
    assert result["is_fraud"].isin([0, 1]).all()       # Class -> is_fraud preserved

def test_transformation_transaction_id_is_unique(tmp_path):
    src = tmp_path / "raw.csv"
    _make_kaggle_like_csv(src, rows=5)
    bronze = tmp_path / "bronze"; bronze.mkdir()
    out = DataTransformation(types.SimpleNamespace(bronze_path=bronze)).transform(src)
    result = pd.read_csv(out)
    assert result["transaction_id"].is_unique           # PK integrity


# ============================================================
# STAGE 3 — LOADING (DB mocked: no Postgres needed)
# ============================================================
def test_loading_calls_to_sql_with_fact_table(tmp_path, monkeypatch):
    # build a bronze file to load
    bronze_file = tmp_path / "clean.csv"
    pd.DataFrame({"transaction_id": [0, 1], "amount": [10.0, 20.0],
                  "is_fraud": [0, 1]}).to_csv(bronze_file, index=False)

    calls = {}
    # fake engine + intercept DataFrame.to_sql
    monkeypatch.setattr("financial_fraud_analytics.components.loading.create_engine",
                        lambda uri: "FAKE_ENGINE")
    def fake_to_sql(self, name, con, if_exists=None, index=None):
        calls["table"] = name; calls["if_exists"] = if_exists
    monkeypatch.setattr(pd.DataFrame, "to_sql", fake_to_sql)

    cfg = types.SimpleNamespace(
        db_uri="postgresql://u:p@h:1/d",
        table_name="fact_transactions",
        if_exists="replace",
    )
    DataLoading(cfg).load(bronze_file)
    assert calls["table"] == "fact_transactions"
    assert calls["if_exists"] == "replace"


# ============================================================
# STAGE 4 — CONFIGURATION MANAGER (wiring)
# ============================================================
def test_configuration_manager_builds_ingestion_config():
    cm = ConfigurationManager()
    ic = cm.get_data_ingestion_config()
    assert ic.source_file.as_posix() == "data/raw/transactions.csv"
    tc = cm.get_transformation_config()
    assert tc.bronze_path.as_posix() == "data/processed/bronze"


# ============================================================
# STAGE 5 — CROSS-CHECK: does config path match what the
# existing tests/test_schema.py + test_quality.py expect?
# ============================================================
def test_bronze_path_consistency_between_config_and_tests():
    cfg = read_yaml(CONFIG_FILE_PATH)
    config_bronze = cfg["paths"]["bronze"]                 # standardized location
    tests_expect = "data/processed/bronze"                 # test_schema/test_quality derive from config
    assert config_bronze == tests_expect, (
        f"PATH MISMATCH: pipeline writes bronze to '{config_bronze}', "
        f"but tests/test_schema.py and tests/test_quality.py read from '{tests_expect}'."
    )