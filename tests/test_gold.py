"""
Phase 6 — Gold marts + star schema. Each test maps to a success criterion.
Enrichment determinism is tested directly; mart aggregations are tested against a
hand-computed controlled input so the numbers are exact, not approximate.

Run:  pytest tests/test_gold.py -v
"""
import types
import pandas as pd
import pytest
from pathlib import Path

pyspark = pytest.importorskip("pyspark")
from pyspark.sql import SparkSession

from financial_fraud_analytics.components.enrichment import EnrichmentProcessor
from financial_fraud_analytics.components.gold_builder import GoldBuilder
from financial_fraud_analytics.config.configuration import ConfigurationManager


@pytest.fixture(scope="module")
def spark():
    s = (SparkSession.builder.master("local[1]").appName("test")
         .config("spark.ui.enabled", "false")
         .config("spark.sql.shuffle.partitions", 1).getOrCreate())
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


def _enrich_cfg(silver, enriched):
    return types.SimpleNamespace(
        silver_path=silver, enriched_path=enriched, compression="snappy",
        partition_cols=["dt"], base_date="2024-01-01", num_customers=100,
        num_merchants=50,
        categories=["grocery", "travel", "electronics", "dining"],
        states=["CA", "NY", "TX"])


def _gold_cfg(enriched, gold):
    return types.SimpleNamespace(
        enriched_path=enriched, gold_path=gold, compression="snappy",
        top_n_merchants=10, high_risk_min_fraud=1)


def _write_silver(spark, silver, rows=10):
    pdf = pd.DataFrame({
        "transaction_id": range(rows), "customer_id": 1, "account_id": 1,
        "date_key": [float(i) for i in range(rows)],
        "amount": [10.0*(i+1) for i in range(rows)],
        "is_fraud": [i % 2 for i in range(rows)], "dt": "2026-06-02",
    })
    (spark.createDataFrame(pdf).write.mode("overwrite")
        .partitionBy("dt").parquet(str(silver / "transactions")))


# ---------- Criterion: enrichment adds dimensions, deterministically ----------
def test_enrichment_adds_dimensions(tmp_path, spark):
    _write_silver(spark, tmp_path/"silver", rows=10)
    out = EnrichmentProcessor(_enrich_cfg(tmp_path/"silver", tmp_path/"enriched"),
                              spark).enrich()
    e = spark.read.parquet(out).toPandas()
    for col in ["merchant_id", "category", "state", "event_time", "event_date", "event_hour"]:
        assert col in e.columns


def test_enrichment_is_deterministic(tmp_path, spark):
    _write_silver(spark, tmp_path/"silver", rows=10)
    cfg = _enrich_cfg(tmp_path/"silver", tmp_path/"enriched")
    EnrichmentProcessor(cfg, spark).enrich()
    a = spark.read.parquet(str(tmp_path/"enriched"/"transactions")).toPandas().sort_values("transaction_id")
    # transaction_id 0 -> M0, category[0], state[0]; same mapping every run
    row0 = a[a.transaction_id == 0].iloc[0]
    assert row0["merchant_id"] == "M0"
    assert row0["category"] == "grocery"
    assert row0["state"] == "CA"


def test_enrichment_event_time_from_base_date(tmp_path, spark):
    _write_silver(spark, tmp_path/"silver", rows=3)
    cfg = _enrich_cfg(tmp_path/"silver", tmp_path/"enriched")
    EnrichmentProcessor(cfg, spark).enrich()
    e = spark.read.parquet(str(tmp_path/"enriched"/"transactions")).toPandas()
    # date_key=0 -> event_time == base_date midnight
    row0 = e[e.transaction_id == 0].iloc[0]
    assert str(row0["event_date"]) == "2024-01-01"


# ---------- helper: build a controlled enriched frame for exact mart math ----------
def _controlled_enriched(spark):
    # 4 rows, hand-computable:
    #  cat A: 2 txns, 1 fraud -> rate 0.5 ; cat B: 2 txns, 0 fraud -> rate 0.0
    pdf = pd.DataFrame({
        "transaction_id": [1, 2, 3, 4],
        "customer_id": [10, 10, 20, 20],
        "merchant_id": ["M1", "M1", "M2", "M2"],
        "category": ["A", "A", "B", "B"],
        "state": ["CA", "CA", "NY", "NY"],
        "amount": [100.0, 100.0, 50.0, 50.0],
        "is_fraud": [1, 0, 0, 0],
        "event_date": ["2024-01-01"]*4,
        "event_hour": [9, 9, 10, 10],
    })
    return spark.createDataFrame(pdf)


# ---------- Criterion: fraud_rate_by_category exact ----------
def test_fraud_rate_by_category_exact(tmp_path, spark):
    df = _controlled_enriched(spark)
    g = GoldBuilder(_gold_cfg(tmp_path/"e", tmp_path/"g"), spark)
    res = {r["category"]: r for r in g.fraud_rate_by_category(df).collect()}
    assert res["A"]["txn_count"] == 2 and res["A"]["fraud_count"] == 1
    assert abs(res["A"]["fraud_rate"] - 0.5) < 1e-9
    assert res["B"]["fraud_count"] == 0 and abs(res["B"]["fraud_rate"]) < 1e-9


# ---------- Criterion: daily_customer_spend exact ----------
def test_daily_customer_spend_exact(tmp_path, spark):
    df = _controlled_enriched(spark)
    g = GoldBuilder(_gold_cfg(tmp_path/"e", tmp_path/"g"), spark)
    res = {r["customer_id"]: r for r in g.daily_customer_spend(df).collect()}
    assert abs(res[10]["total_spend"] - 200.0) < 1e-9   # 100 + 100
    assert abs(res[20]["total_spend"] - 100.0) < 1e-9   # 50 + 50
    assert res[10]["txn_count"] == 2


# ---------- Criterion: top_merchants ranked by total_amount ----------
def test_top_merchants_ranking(tmp_path, spark):
    df = _controlled_enriched(spark)
    g = GoldBuilder(_gold_cfg(tmp_path/"e", tmp_path/"g"), spark)
    rows = g.top_merchants(df).collect()
    assert rows[0]["merchant_id"] == "M1"               # 200 > 100
    assert abs(rows[0]["total_amount"] - 200.0) < 1e-9


# ---------- Criterion: high_risk_customers filters by fraud threshold ----------
def test_high_risk_customers_filter(tmp_path, spark):
    df = _controlled_enriched(spark)
    g = GoldBuilder(_gold_cfg(tmp_path/"e", tmp_path/"g"), spark)
    rows = {r["customer_id"]: r for r in g.high_risk_customers(df).collect()}
    assert 10 in rows                                   # customer 10 has 1 fraud
    assert 20 not in rows                               # customer 20 has 0 fraud


# ---------- Criterion: star schema (fact row count == input, dims distinct) ----------
def test_star_schema_fact_and_dims(tmp_path, spark):
    df = _controlled_enriched(spark)
    g = GoldBuilder(_gold_cfg(tmp_path/"e", tmp_path/"g"), spark)
    assert g.fact_transactions(df).count() == 4
    assert g.dim_merchant(df).count() == 2              # M1, M2
    assert g.dim_customer(df).count() == 2              # 10, 20
    assert g.dim_date(df).count() == 1                  # one event_date


# ---------- Criterion: full build writes all marts as parquet ----------
def test_gold_build_writes_all_marts(tmp_path, spark):
    _write_silver(spark, tmp_path/"silver", rows=10)
    EnrichmentProcessor(_enrich_cfg(tmp_path/"silver", tmp_path/"enriched"), spark).enrich()
    GoldBuilder(_gold_cfg(tmp_path/"enriched", tmp_path/"gold"), spark).build()
    for name in ["merchant_hourly_metrics", "daily_customer_spend",
                 "fraud_rate_by_category", "fraud_rate_by_state",
                 "top_merchants", "high_risk_customers",
                 "dim_merchant", "dim_customer", "dim_date", "fact_transactions"]:
        assert list((tmp_path/"gold"/name).rglob("*.parquet")), f"{name} not written"


# ---------- Criterion: config-driven (manager builds both configs) ----------
def test_gold_configs_are_config_driven():
    cm = ConfigurationManager()
    ec = cm.get_enrichment_config()
    gc = cm.get_gold_config()
    assert ec.num_merchants == 50
    assert ec.base_date == "2024-01-01"
    assert gc.top_n_merchants == 10
    assert gc.gold_path.as_posix() == "data/processed/gold"