"""
Phase 4 — Spark engine. Each test maps to a Phase 4 success criterion.
The headline test proves Spark output == pandas output on the same input (parity).

Run:  pytest tests/test_spark_parity.py -v
NOTE: requires pyspark + a JVM (Java 8/11/17/21).
"""
import sys
import types
import pandas as pd
import pytest
from pathlib import Path

pyspark = pytest.importorskip("pyspark")  # skip cleanly if Spark/JVM absent
from pyspark.sql import SparkSession

from financial_fraud_analytics.components.bronze_writer import BronzeWriter
from financial_fraud_analytics.components.bronze_writer_spark import BronzeWriterSpark
from financial_fraud_analytics.components.silver_processor import SilverProcessor
from financial_fraud_analytics.components.silver_processor_spark import SilverProcessorSpark
from financial_fraud_analytics.config.configuration import ConfigurationManager


SCHEMA = {
    "transaction_id": "int64", "customer_id": "int64", "account_id": "int64",
    "date_key": "float64", "amount": "float64", "is_fraud": "int64",
}


@pytest.fixture(scope="module")
def spark():
    s = (SparkSession.builder.master("local[1]").appName("test")
         .config("spark.ui.enabled", "false")
         .config("spark.sql.shuffle.partitions", 1).getOrCreate())
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


def _spark_cfg():
    return types.SimpleNamespace(app_name="t", master="local[1]",
                                 shuffle_partitions=1, output_files_per_partition=1)

def _bronze_cfg(p):
    return types.SimpleNamespace(bronze_path=p, file_format="parquet",
                                 compression="snappy", partition_cols=["dt"])

def _silver_cfg(bp, sp):
    return types.SimpleNamespace(
        bronze_path=bp, silver_path=sp, compression="snappy", partition_cols=["dt"],
        schema=SCHEMA, primary_key="transaction_id", dedup_keys=["transaction_id"],
        not_null_columns=["transaction_id", "amount", "is_fraud"],
        min_amount=0, watermark_days=2)

def _clean_csv(path, rows=5):
    pd.DataFrame({
        "transaction_id": range(rows), "customer_id": 1, "account_id": 1,
        "date_key": [float(i) for i in range(rows)],
        "amount": [10.0*(i+1) for i in range(rows)],
        "is_fraud": [0, 1, 0, 1, 0][:rows],
    }).to_csv(path, index=False)


def _norm(df):
    return (df.sort_values("transaction_id").reset_index(drop=True)
              [["transaction_id", "customer_id", "account_id", "date_key", "amount", "is_fraud"]])


# ---------- Criterion: BRONZE parity (spark output == pandas output) ----------
def test_bronze_spark_matches_pandas(tmp_path, spark):
    src = tmp_path / "clean.csv"; _clean_csv(src)

    pout = BronzeWriter(_bronze_cfg(tmp_path/"bp")).write(src)
    pdf = pd.read_parquet(pout, engine="pyarrow")

    sout = BronzeWriterSpark(_bronze_cfg(tmp_path/"bs"), _spark_cfg(), spark).write(src)
    sdf = spark.read.parquet(sout).toPandas()

    assert len(pdf) == len(sdf)
    pd.testing.assert_frame_equal(_norm(pdf), _norm(sdf), check_dtype=False)


# ---------- Criterion: SILVER parity (spark output == pandas output) ----------
def test_silver_spark_matches_pandas(tmp_path, spark):
    # build identical bronze for each engine
    src = tmp_path / "clean.csv"; _clean_csv(src, rows=5)
    BronzeWriter(_bronze_cfg(tmp_path/"bp")).write(src)
    BronzeWriterSpark(_bronze_cfg(tmp_path/"bs"), _spark_cfg(), spark).write(src)

    pout = SilverProcessor(_silver_cfg(tmp_path/"bp", tmp_path/"sp")).process()
    pdf = pd.read_parquet(pout, engine="pyarrow")

    sout = SilverProcessorSpark(_silver_cfg(tmp_path/"bs", tmp_path/"ss"),
                                _spark_cfg(), spark).process()
    sdf = spark.read.parquet(sout).toPandas()

    assert len(pdf) == len(sdf)
    pd.testing.assert_frame_equal(_norm(pdf), _norm(sdf), check_dtype=False)


# ---------- Criterion: small-files handling (coalesce -> N files per partition) ----------
def test_bronze_spark_small_files_controlled(tmp_path, spark):
    src = tmp_path / "clean.csv"; _clean_csv(src, rows=5)
    out = BronzeWriterSpark(_bronze_cfg(tmp_path/"bs"), _spark_cfg(), spark).write(src)
    # one partition (single dt) with output_files_per_partition=1 -> exactly 1 data file
    data_files = list(Path(out).rglob("*.parquet"))
    assert len(data_files) == 1, f"expected 1 file, got {len(data_files)}"


# ---------- Criterion: config-driven SparkSession ----------
def test_spark_config_is_config_driven():
    cfg = ConfigurationManager().get_spark_config()
    assert cfg.master == "local[*]"
    assert cfg.app_name == "financial_fraud_analytics"
    assert cfg.output_files_per_partition == 1