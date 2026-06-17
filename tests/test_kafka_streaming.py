"""
Phase 5 — Kafka + Structured Streaming. Each test maps to a success criterion.

The broker round-trip is NOT exercised here (needs Docker + the Kafka connector JAR).
Instead:
  * producer is tested against an injected fake broker
  * the streaming parse/write/checkpoint/idempotency logic is tested with a Spark
    FILE source standing in for Kafka (identical parse() and write_stream()).

Run:  pytest tests/test_kafka_streaming.py -v
"""
import json
import types
import pandas as pd
import pytest
from pathlib import Path

from financial_fraud_analytics.components.kafka_producer import KafkaProducer
from financial_fraud_analytics.config.configuration import ConfigurationManager

pyspark = pytest.importorskip("pyspark")
from pyspark.sql import SparkSession
from financial_fraud_analytics.components.streaming_consumer import StreamingConsumer


SCHEMA = {
    "transaction_id": "int64", "customer_id": "int64", "account_id": "int64",
    "date_key": "float64", "amount": "float64", "is_fraud": "int64",
}


# ===================== PRODUCER (fake broker) =====================
class FakeProducer:
    def __init__(self): self.messages = []
    def produce(self, topic, value=None, callback=None):
        self.messages.append((topic, value))
        if callback: callback(None, None)        # simulate successful delivery
    def poll(self, t): pass
    def flush(self): pass


def _kafka_cfg():
    return types.SimpleNamespace(
        bootstrap_servers="localhost:9092", topic="transactions",
        client_id="test", starting_offsets="earliest", throttle_ms=0)


def _clean_csv(path, rows=5):
    pd.DataFrame({
        "transaction_id": range(rows), "customer_id": 1, "account_id": 1,
        "date_key": [float(i) for i in range(rows)],
        "amount": [10.0*(i+1) for i in range(rows)],
        "is_fraud": [0, 1, 0, 1, 0][:rows],
    }).to_csv(path, index=False)


def test_producer_sends_one_message_per_row(tmp_path):
    src = tmp_path / "clean.csv"; _clean_csv(src, rows=5)
    fake = FakeProducer()
    sent = KafkaProducer(_kafka_cfg(), producer=fake).produce_from_csv(src)
    assert sent == 5
    assert len(fake.messages) == 5


def test_producer_payload_is_valid_json_with_native_types(tmp_path):
    src = tmp_path / "clean.csv"; _clean_csv(src, rows=3)
    fake = FakeProducer()
    KafkaProducer(_kafka_cfg(), producer=fake).produce_from_csv(src)
    topic, value = fake.messages[0]
    assert topic == "transactions"
    rec = json.loads(value.decode("utf-8"))
    assert set(rec) == set(SCHEMA)                 # all contract columns present
    assert isinstance(rec["transaction_id"], int)  # numpy int -> native int
    assert isinstance(rec["amount"], float)


# ===================== STREAMING (file source == kafka stand-in) =====================
@pytest.fixture(scope="module")
def spark():
    s = (SparkSession.builder.master("local[1]").appName("test")
         .config("spark.ui.enabled", "false")
         .config("spark.sql.shuffle.partitions", 1).getOrCreate())
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


def _streaming_cfg(out, chk):
    return types.SimpleNamespace(
        output_path=out, checkpoint_path=chk, compression="snappy",
        partition_cols=["dt"], trigger_seconds=5, max_offsets_per_trigger=10000,
        schema=SCHEMA)


def _write_json_files(src_dir: Path, rows, start=0):
    src_dir.mkdir(parents=True, exist_ok=True)
    recs = [{"transaction_id": i, "customer_id": 1, "account_id": 1,
             "date_key": float(i), "amount": 10.0*(i+1), "is_fraud": i % 2}
            for i in range(start, start+rows)]
    (src_dir / f"batch_{start}.json").write_text(
        "\n".join(json.dumps(r) for r in recs))


def _file_value_stream(spark, src_dir):
    # a streaming source of raw text lines -> a `value` column, exactly like
    # CAST(value AS STRING) from a Kafka source
    return (spark.readStream.format("text").load(str(src_dir))
            .withColumnRenamed("value", "value"))


def test_streaming_parses_and_writes_bronze(tmp_path, spark):
    src = tmp_path / "incoming"; _write_json_files(src, rows=5)
    cfg = _streaming_cfg(tmp_path/"bronze_stream", tmp_path/"chk")
    consumer = StreamingConsumer(_kafka_cfg(), cfg, spark)

    parsed = consumer.parse(_file_value_stream(spark, src))
    consumer.write_stream(parsed, await_termination=True)

    out = pd.read_parquet(tmp_path/"bronze_stream"/"transactions", engine="pyarrow")
    assert len(out) == 5
    assert "transaction_id" in out.columns
    assert "dt" in out.columns


def test_streaming_checkpoint_idempotent_on_replay(tmp_path, spark):
    # criterion: restart with same checkpoint + no new data -> no duplication
    src = tmp_path / "incoming"; _write_json_files(src, rows=5)
    cfg = _streaming_cfg(tmp_path/"bronze_stream", tmp_path/"chk")
    consumer = StreamingConsumer(_kafka_cfg(), cfg, spark)

    consumer.write_stream(consumer.parse(_file_value_stream(spark, src)), True)
    count1 = len(pd.read_parquet(tmp_path/"bronze_stream"/"transactions", engine="pyarrow"))

    # replay: same checkpoint, same files -> already-processed, nothing re-ingested
    consumer.write_stream(consumer.parse(_file_value_stream(spark, src)), True)
    count2 = len(pd.read_parquet(tmp_path/"bronze_stream"/"transactions", engine="pyarrow"))

    assert count1 == 5
    assert count2 == 5      # no duplicates from replay


def test_streaming_offset_recovery_processes_only_new(tmp_path, spark):
    # criterion: offset recovery -> a second batch ingests only the new rows
    src = tmp_path / "incoming"; _write_json_files(src, rows=5, start=0)
    cfg = _streaming_cfg(tmp_path/"bronze_stream", tmp_path/"chk")
    consumer = StreamingConsumer(_kafka_cfg(), cfg, spark)

    consumer.write_stream(consumer.parse(_file_value_stream(spark, src)), True)
    _write_json_files(src, rows=3, start=100)   # 3 brand-new records arrive
    consumer.write_stream(consumer.parse(_file_value_stream(spark, src)), True)

    out = pd.read_parquet(tmp_path/"bronze_stream"/"transactions", engine="pyarrow")
    assert len(out) == 8                          # 5 + 3, none reprocessed
    assert out["transaction_id"].is_unique


# ===================== CONFIG-DRIVEN =====================
def test_kafka_and_streaming_configs_are_config_driven():
    cm = ConfigurationManager()
    k = cm.get_kafka_config()
    st = cm.get_streaming_config()
    assert k.topic == "transactions"
    assert k.bootstrap_servers == "localhost:9092"
    assert st.schema["amount"] == "float64"
    assert st.output_path.as_posix() == "data/processed/bronze_stream"