"""
Modular tests for Phase 3 — Silver Parquet (SilverProcessor component).
Each test maps to a Phase 3 success criterion.

Run:  pytest tests/test_silver_processor.py -v
"""
import sys
import types
import pandas as pd
import pytest
from pathlib import Path

from financial_fraud_analytics.components.silver_processor import SilverProcessor
from financial_fraud_analytics.exception.exception import DataPlatformException
from financial_fraud_analytics.config.configuration import ConfigurationManager


SCHEMA = {
    "transaction_id": "int64", "customer_id": "int64", "account_id": "int64",
    "date_key": "float64", "amount": "float64", "is_fraud": "int64",
}


def _silver_cfg(bronze_path: Path, silver_path: Path, watermark_days=2):
    return types.SimpleNamespace(
        bronze_path=bronze_path, silver_path=silver_path,
        compression="snappy", partition_cols=["dt"],
        schema=SCHEMA, primary_key="transaction_id",
        dedup_keys=["transaction_id"],
        not_null_columns=["transaction_id", "amount", "is_fraud"],
        min_amount=0, watermark_days=watermark_days,
    )


def _write_bronze(bronze_path: Path, df: pd.DataFrame):
    out = bronze_path / "transactions"
    df.to_parquet(out, engine="pyarrow", partition_cols=["dt"], index=False,
                  existing_data_behavior="delete_matching")
    return out


def _base_df(rows=5, dt="2026-06-02"):
    return pd.DataFrame({
        "transaction_id": list(range(rows)), "customer_id": [1]*rows,
        "account_id": [1]*rows, "date_key": [float(i) for i in range(rows)],
        "amount": [10.0*(i+1) for i in range(rows)],
        "is_fraud": [0, 1, 0, 1, 0][:rows], "dt": [dt]*rows,
    })


# ---------- Criterion: silver parquet created + reads back ----------
def test_silver_writes_parquet(tmp_path):
    _write_bronze(tmp_path/"bronze", _base_df())
    out = SilverProcessor(_silver_cfg(tmp_path/"bronze", tmp_path/"silver")).process()
    df = pd.read_parquet(out, engine="pyarrow")
    assert len(df) == 5
    assert list(Path(out).rglob("*.parquet"))


# ---------- Criterion: partitioned by dt ----------
def test_silver_partitioned_by_dt(tmp_path):
    _write_bronze(tmp_path/"bronze", _base_df())
    out = SilverProcessor(_silver_cfg(tmp_path/"bronze", tmp_path/"silver")).process()
    parts = [p.name for p in Path(out).iterdir() if p.is_dir()]
    assert any(p.startswith("dt=") for p in parts)


# ---------- Criterion: schema enforcement (types cast to contract) ----------
def test_silver_enforces_types(tmp_path):
    df = _base_df()
    df["amount"] = df["amount"].astype("int64")  # wrong type on input
    _write_bronze(tmp_path/"bronze", df)
    out = SilverProcessor(_silver_cfg(tmp_path/"bronze", tmp_path/"silver")).process()
    result = pd.read_parquet(out, engine="pyarrow")
    assert str(result["amount"].dtype) == "float64"  # coerced to contract


def test_silver_missing_column_raises(tmp_path):
    df = _base_df().drop(columns=["amount"])
    _write_bronze(tmp_path/"bronze", df)
    with pytest.raises(DataPlatformException):
        SilverProcessor(_silver_cfg(tmp_path/"bronze", tmp_path/"silver")).process()


# ---------- Criterion: null handling ----------
def test_silver_drops_nulls(tmp_path):
    df = _base_df(rows=5)
    df.loc[0, "amount"] = None  # one null in a not-null column
    _write_bronze(tmp_path/"bronze", df)
    out = SilverProcessor(_silver_cfg(tmp_path/"bronze", tmp_path/"silver")).process()
    assert len(pd.read_parquet(out, engine="pyarrow")) == 4


# ---------- Criterion: deduplication on transaction_id ----------
def test_silver_deduplicates(tmp_path):
    df = _base_df(rows=5)
    dup = df.iloc[[0]].copy()
    df = pd.concat([df, dup], ignore_index=True)  # 6 rows, one dupe id
    _write_bronze(tmp_path/"bronze", df)
    out = SilverProcessor(_silver_cfg(tmp_path/"bronze", tmp_path/"silver")).process()
    result = pd.read_parquet(out, engine="pyarrow")
    assert result["transaction_id"].is_unique
    assert len(result) == 5


# ---------- Criterion: watermark rejects late arrivals ----------
def test_silver_watermark_drops_stale(tmp_path):
    recent = _base_df(rows=3, dt="2026-06-02")
    stale = _base_df(rows=2, dt="2026-05-01")          # ~32 days old
    stale["transaction_id"] = [100, 101]
    df = pd.concat([recent, stale], ignore_index=True)
    _write_bronze(tmp_path/"bronze", df)
    out = SilverProcessor(_silver_cfg(tmp_path/"bronze", tmp_path/"silver",
                                      watermark_days=2)).process()
    result = pd.read_parquet(out, engine="pyarrow")
    assert len(result) == 3                            # stale rows rejected


# ---------- Criterion: reconciliation (silver <= bronze) ----------
def test_silver_reconciliation_shrinks_only(tmp_path):
    df = _base_df(rows=5)
    _write_bronze(tmp_path/"bronze", df)
    out = SilverProcessor(_silver_cfg(tmp_path/"bronze", tmp_path/"silver")).process()
    assert len(pd.read_parquet(out, engine="pyarrow")) <= 5


# ---------- Criterion: config-driven (manager builds SilverConfig) ----------
def test_silver_config_is_config_driven():
    cfg = ConfigurationManager().get_silver_config()
    assert cfg.dedup_keys == ["transaction_id"]
    assert cfg.watermark_days == 2
    assert cfg.schema["amount"] == "float64"
    assert cfg.silver_path.as_posix() == "data/processed/silver"


# ---------- Regression: watermark must work on dt read back from real parquet ----------
# Parquet restores partition cols as unordered Categorical; .max() used to crash here.
def test_silver_watermark_on_parquet_roundtrip(tmp_path):
    df = _base_df(rows=5)
    bronze_out = _write_bronze(tmp_path / "bronze", df)        # real partitioned write
    # confirm dt really comes back as Categorical (the trigger condition)
    rt = pd.read_parquet(bronze_out, engine="pyarrow")
    assert str(rt["dt"].dtype) == "category"
    # processing must not raise and must preserve the rows
    out = SilverProcessor(_silver_cfg(tmp_path / "bronze", tmp_path / "silver")).process()
    assert len(pd.read_parquet(out, engine="pyarrow")) == 5