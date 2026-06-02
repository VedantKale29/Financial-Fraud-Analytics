# Financial Fraud Analytics — Project Roadmap & Handoff (v2)

> Paste this whole file at the start of a new chat to bring any assistant fully up to speed.
> It separates **what exists today** from **what we are evolving toward**, defines a **success gate per phase** to prevent scope creep, and is scoped to a **tier-1 bank** standard (Morgan Stanley / Barclays / JPMorgan / Goldman).

---

## 1. Project Identity & Goal

A **production-grade, finance-domain streaming lakehouse** that demonstrates the full data-engineering lifecycle under the constraints real banks operate within: **auditability, immutability of source, PII protection, layer-to-layer reconciliation, and regulatory-grade data quality (AML / KYC mindset).**

- Focus: **Data Engineering**, not ML training.
- Purpose: portfolio project targeting data-engineering roles at large financial institutions.
- Dataset: Kaggle Credit Card Fraud (`Time, V1..V28, Amount, Class`) standardized into a transaction schema.

ML boundary statement (for interviews):
> "Data Science owns model training; my responsibility is the feature pipeline and serving infrastructure for real-time inference."

What it must showcase: streaming, medallion lakehouse, **data contracts & schema enforcement**, **data quality + reconciliation**, **slowly-changing dimensions**, **idempotent / exactly-once processing**, partitioning & compaction, governance & lineage, **security (least-privilege IAM, KMS encryption, secrets management, PII masking)**, orchestration with SLAs & backfills, warehousing + dbt modeling, Infrastructure as Code, **CI/CD**, and observability.

---

## 2. Two States (read this first)

### Current Repository State (verified by running it)

```
CSV (data/raw/transactions.csv)
  -> extraction.py        (read CSV -> write raw CSV)
  -> transformation.py    (rename Time/Amount/Class -> date_key/amount/is_fraud,
                           add transaction_id/customer_id/account_id, reorder)
  -> Bronze CSV (data/processed/bronze/transactions_clean.csv)
  -> loading.py           (pandas.to_sql -> Postgres "fact_transactions")
```

A **pandas batch ETL**. NO Kafka, NO Spark, NO streaming, NO parquet lake yet.

### Target Architecture (the goal)

```
Producers -> Amazon MSK (Kafka) -> Spark Structured Streaming
                                      |-> DynamoDB (online serving)
                                      |-> S3 Lake (Bronze/Silver/Gold parquet)
                                              -> Snowflake + dbt -> BI

Orchestration: Airflow (MWAA)   Monitoring: CloudWatch + SNS
Governance: Glue Catalog + Lake Formation   IaC: Terraform   CI/CD: GitHub Actions
```

---

## 3. Phased Roadmap (resequenced: contracts first, engine swap later)

| Phase | Name | Engine | Status |
|-------|------|--------|--------|
| 1 | Clean Batch ETL baseline | pandas | DONE |
| 2 | Bronze Parquet (lake contract) | pandas | NEXT |
| 3 | Silver Parquet (clean + quality) | pandas | Planned |
| 4 | Introduce Spark (swap engine, same logic) | PySpark | Planned |
| 5 | Introduce Kafka (streaming ingestion) | PySpark + Kafka | Planned |
| 6 | Gold (business marts) | PySpark | Planned |
| 7 | AWS (S3, MSK, EMR, Glue, MWAA, Snowflake/dbt, Terraform) | Cloud | Planned |

Principle: establish **Bronze / Silver / Gold** data contracts + folder structures locally, then swap `pandas -> PySpark` without changing business logic. (Gold's business logic may be prototyped earlier in pandas if convenient, but it is *finalized* on Spark in Phase 6 so aggregations run on the production engine.)

### Cross-cutting tracks (run alongside every phase, not separate milestones)
- **A. Data Quality & Reconciliation** — completeness, uniqueness, validity, freshness; row-count reconciliation between layers.
- **B. Security & Governance** — PII masking/tokenization, encryption at rest, secrets out of code, immutable raw, audit trail.
- **C. Observability & Alerting** — structured logs, metrics, freshness SLAs, (cloud) consumer lag + failure alerts.
- **D. CI/CD & Testing** — modular tests after every component; GitHub Actions for lint + test (later: terraform plan/apply).
- **E. Documentation & Data Contracts** — `schema.yaml` is the contract; each layer documents its inputs/outputs.

---

## 4. Success Criteria Per Phase (the anti-scope-creep gates)

A phase is "done" only when **all** its criteria pass.

### Phase 1 — Clean Batch ETL  (DONE)
- Single standardized bronze location (`data/processed/bronze`) across config + tests
- All configs are `@dataclass(frozen=True)`, built by `ConfigurationManager`
- No component reads the raw config dict; table name + write mode come from config
- Tests derive paths from config (no hardcoding)
- 14 modular tests passing

### Phase 2 — Bronze Parquet
- Bronze written as **Parquet** (snappy), config-driven format + path
- **Partitioned by `dt=YYYY-MM-DD`** (derived from event time)
- **Row counts preserved** vs source (reconciliation check logged + asserted)
- Raw stays **immutable** (Bronze never mutates raw)
- Schema (columns + types) captured and asserted by a read-back test
- Tests passing: parquet reads back, partition dirs exist, count matches

### Phase 3 — Silver Parquet
- Silver parquet created from Bronze, partitioned
- **Schema enforcement** against `schema.yaml` (types validated)
- **Null / malformed handling** with documented, config-driven rules
- **Deduplication on `transaction_id`** (dedup ratio logged)
- **Late-arrival / watermark rule defined** (simple in pandas, ready for Spark)
- Data-quality gate passes: completeness, uniqueness, validity
- Reconciliation: `silver_rows <= bronze_rows`, drop counts explained
- Quality tests passing

### Phase 4 — Introduce Spark
- PySpark replaces pandas for Bronze + Silver
- **Parity test**: Spark output equals pandas output on a sample (same business logic)
- Partition pruning verified; small-files handled (coalesce/repartition)
- SparkSession is config-driven
- All existing tests pass on the Spark path

### Phase 5 — Introduce Kafka
- Local Kafka (Docker); producer streams CSV -> topic (config-driven, delivery callbacks)
- Spark Structured Streaming consumes -> Bronze parquet
- **Checkpointing + offset recovery** (replay capability proven)
- **Idempotent writes** — replay produces no duplicates
- Test: produce N messages, consume, assert N distinct rows in Bronze

### Phase 6 — Gold
- Marts built: `merchant_hourly_metrics`, `daily_customer_spend`, `fraud_rate_by_category`, `fraud_rate_by_state`, `top_merchants`, `high_risk_customers`
- Star-schema aligned (fact + dims; dims use SCD where relevant)
- Aggregations validated against a known sample
- Partitioned / optimized for BI; AML-style queries runnable
- Tests passing

### Phase 7 — AWS
- S3 medallion buckets with lifecycle + **KMS encryption**
- MSK replaces local Kafka (only bootstrap servers change)
- EMR runs the same Spark code
- Glue Catalog + crawlers; Lake Formation permissions
- Snowpipe (S3 Gold -> Snowflake); dbt models: `fct_transactions`, `dim_customer`, `dim_merchant`, `dim_time`, `dim_region`
- Airflow (MWAA) DAGs (ingestion, silver, gold, quality, dbt) with **retries, SLAs, backfills**
- CloudWatch metrics + SNS alerts (consumer lag, job failures, freshness, SLA breaches)
- **Secrets Manager** for credentials; **least-privilege IAM**
- **Terraform** provisions everything; S3 backend + DynamoDB state lock
- **GitHub Actions** CI/CD (lint, test, terraform plan/apply)

---

## 5. Development Workflow (mandatory order)

```
1. config.yaml        2. schema.yaml (if contract changes)   3. params.yaml (if tunables)
4. entity/ dataclass  5. ConfigurationManager builder         6. components/ (one job)
7. scripts/ entry     8. tests/ (run, verify output, check files, validate logs)
```
Next component only after the current one passes its test. No "test later."

## 6. Coding Style Rules
- Config-driven (no hardcoded values), dataclass-driven (`@dataclass(frozen=True)`), component isolation (one job per file), pipelines orchestrate only, scripts are entry points only, test after every component.
- For each component, explain: **why it exists, the problem it solves, how it works internally, the AWS equivalent, the interview answer.**
- Response style: explain -> file changes -> code -> test command -> expected output -> wait. No 1000-line dumps.

## 7. Project Structure
```
src/financial_fraud_analytics/{config,constants,entity,logger,exception,utils,components,pipelines}/
scripts/   tests/   config/(config.yaml, schema.yaml, params.yaml)   sql/   infrastructure/(later: terraform)   dags/(later)   dbt_project/(later)
```

## 8. Local -> AWS Mapping (interview shorthand)
```
filesystem -> S3   local Kafka -> MSK   local Spark -> EMR   Postgres -> Snowflake
manual runs -> Airflow(MWAA)   logs -> CloudWatch+SNS   manual setup -> Terraform
secrets in file -> Secrets Manager   none -> Glue Catalog + Lake Formation (governance)
```

## 9. Resume Bullet (evolves as phases land)
> Built a finance-domain streaming lakehouse (Kafka/MSK -> Spark Structured Streaming -> S3 Bronze/Silver/Gold -> Snowflake/dbt) with schema-enforced data contracts, a data-quality + reconciliation framework, idempotent processing, Airflow orchestration with SLAs/backfills, Terraform IaC, GitHub Actions CI/CD, and least-privilege IAM + KMS + Secrets Manager security.

## 10. How to Resume in a New Chat
Paste this file, then say:
> "Financial Fraud Analytics data-engineering project. Repo is at the Phase 1 baseline (clean pandas batch ETL, 14 tests passing). Continue with **Phase 2: Bronze CSV -> Bronze Parquet (pandas, partitioned by dt=YYYY-MM-DD)** per the Phase 2 Success Criteria. Follow my workflow (config -> entity -> ConfigurationManager -> component -> script -> test), one component at a time, with explanation and a test after each step. No large code dumps."

---
*Baseline: Phase 1 complete & verified. Next: Phase 2 — Bronze Parquet.*