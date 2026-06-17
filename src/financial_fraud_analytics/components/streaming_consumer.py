import sys

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()

# contract dtype -> Spark DDL type (for from_json)
_DDL = {"int64": "long", "float64": "double", "string": "string"}


class StreamingConsumer:
    """
    Spark Structured Streaming consumer: Kafka topic -> Bronze parquet.

    The Kafka-specific part is isolated in `kafka_source()`. `parse()` and
    `write_stream()` operate on a plain DataFrame with a string `value` column,
    so the same logic is testable against any streaming source.
    """

    def __init__(self, kafka_config, streaming_config, spark):
        self.kafka = kafka_config
        self.streaming = streaming_config
        self.spark = spark

    def _ddl(self):
        return ", ".join(f"{c} {_DDL.get(t, t)}" for c, t in self.streaming.schema.items())

    def kafka_source(self):
        return (
            self.spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", self.kafka.bootstrap_servers)
            .option("subscribe", self.kafka.topic)
            .option("startingOffsets", self.kafka.starting_offsets)
            .option("maxOffsetsPerTrigger", self.streaming.max_offsets_per_trigger)
            .load()
            .selectExpr("CAST(value AS STRING) AS value")
        )

    def parse(self, df):
        """df has a string `value` column of JSON -> typed columns."""
        from pyspark.sql import functions as F
        return (
            df.select(F.from_json(F.col("value"), self._ddl()).alias("d"))
              .select("d.*")
        )

    def write_stream(self, parsed_df, await_termination=True):
        from pyspark.sql import functions as F
        out = str(self.streaming.output_path / "transactions")
        chk = str(self.streaming.checkpoint_path)

        query = (
            parsed_df.withColumn("dt", F.date_format(F.current_timestamp(), "yyyy-MM-dd"))
            .writeStream.format("parquet")
            .option("path", out)
            .option("checkpointLocation", chk)
            .partitionBy(*self.streaming.partition_cols)
            .outputMode("append")
            .trigger(availableNow=True)   # process all available, then stop (bounded run)
            .start()
        )
        logger.info(f"STREAM: writing to {out} (checkpoint={chk})")
        if await_termination:
            query.awaitTermination()
        return query

    def run(self):
        try:
            logger.info("STREAM: starting Kafka -> Bronze consumer")
            source = self.kafka_source()
            parsed = self.parse(source)
            self.write_stream(parsed)
            logger.info("STREAM: micro-batch(es) committed; offsets checkpointed")
        except Exception:
            raise DataPlatformException("Streaming consume failed", "STREAM", sys)