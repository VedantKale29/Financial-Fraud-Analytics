"""
Modular tests for Phase 2 — Bronze Parquet (BronzeWriter component).
Each test maps to a Phase 2 success criterion, so a failure points to one guarantee.

Run:  pytest tests/test_bronze_writer.py -v
"""
import sys
import types
import pandas as pd
import pytest
from pathlib import Path

from financial_fraud_analytics.components.bronze_writer import BronzeWriter
from financial_fraud_analytics.exception.exception import DataPlatformException
from financial_fraud_analytics.config.configuration import ConfigurationManager


# ---------- helpers ----------
def _clean_csv(path: Path, rows: int = 5):
    """Bronze-shaped clean CSV (post-transformation)."""
    pd.DataFrame({
        "transaction_id": range(rows),
        "customer_id": 1,
        "account_id": 1,
        "date_key": [float(i) for i in range(rows)],
        "amount": [10.0 * (i + 1) for i in range(rows)],
        "is_fraud": [0, 1, 0, 1, 0][:rows],
    }).to_csv(path, index=False)
    return rows


def _bronze_cfg(bronze_path: Path):
    return types.SimpleNamespace(
        bronze_path=bronze_path,
        file_format="parquet",
        compression="snappy",
        partition_cols=["dt"],
    )


# ---------- Criterion: Bronze written as Parquet, reads back ----------
def test_bronze_writes_parquet_and_reads_back(tmp_path):
    src = tmp_path / "clean.csv"
    _clean_csv(src)
    out = BronzeWriter(_bronze_cfg(tmp_path / "bronze")).write(src)

    df = pd.read_parquet(out, engine="pyarrow")
    assert len(df) == 5
    # at least one physical .parquet file exists under the dataset dir
    assert list(Path(out).rglob("*.parquet")), "no parquet files written"


# ---------- Criterion: partitioned by dt=YYYY-MM-DD ----------
def test_bronze_partitioned_by_dt(tmp_path):
    src = tmp_path / "clean.csv"
    _clean_csv(src)
    out = BronzeWriter(_bronze_cfg(tmp_path / "bronze")).write(src)

    part_dirs = [p.name for p in Path(out).iterdir() if p.is_dir()]
    assert any(d.startswith("dt=") for d in part_dirs), f"no dt= partition: {part_dirs}"


# ---------- Criterion: row counts preserved (reconciliation) ----------
def test_bronze_row_count_preserved(tmp_path):
    src = tmp_path / "clean.csv"
    n = _clean_csv(src, rows=5)
    out = BronzeWriter(_bronze_cfg(tmp_path / "bronze")).write(src)
    assert len(pd.read_parquet(out, engine="pyarrow")) == n


# ---------- Criterion: idempotent reload (no duplicate accumulation) ----------
def test_bronze_reload_is_idempotent(tmp_path):
    src = tmp_path / "clean.csv"
    _clean_csv(src, rows=5)
    cfg = _bronze_cfg(tmp_path / "bronze")
    w = BronzeWriter(cfg)
    w.write(src)
    out = w.write(src)  # run twice, same partition
    # same-partition rewrite must not double the rows
    assert len(pd.read_parquet(out, engine="pyarrow")) == 5


# ---------- Criterion: dt partition column is present in data ----------
def test_bronze_has_dt_column(tmp_path):
    src = tmp_path / "clean.csv"
    _clean_csv(src)
    out = BronzeWriter(_bronze_cfg(tmp_path / "bronze")).write(src)
    df = pd.read_parquet(out, engine="pyarrow")
    assert "dt" in df.columns


# ---------- Criterion: failure is raised as DataPlatformException ----------
def test_bronze_bad_input_raises(tmp_path):
    cfg = _bronze_cfg(tmp_path / "bronze")
    with pytest.raises(DataPlatformException):
        BronzeWriter(cfg).write(tmp_path / "does_not_exist.csv")


# ---------- Criterion: config-driven (manager builds BronzeConfig from yaml) ----------
def test_bronze_config_is_config_driven():
    cfg = ConfigurationManager().get_bronze_config()
    assert cfg.file_format == "parquet"
    assert cfg.compression == "snappy"
    assert cfg.partition_cols == ["dt"]
    assert cfg.bronze_path.as_posix() == "data/processed/bronze"