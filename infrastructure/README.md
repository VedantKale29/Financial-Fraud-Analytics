# Phase 7 (slice) — Serverless AWS Lake: S3 + KMS + Glue + Athena

Cheap, serverless portfolio slice. No always-on compute (no MSK/EMR/MWAA), so there is
nothing to "leave running" — you pay only for tiny S3 storage, per-crawler runs, and
per-query Athena scans. A $2 billing alarm is included as a tripwire.

## Prerequisites
- AWS CLI configured:  `aws configure`  then  `aws sts get-caller-identity`
- Terraform >= 1.5:    `terraform -version`

## 1. Configure
```
cd infrastructure
copy terraform.tfvars.example terraform.tfvars   # Windows
# edit terraform.tfvars: set alert_email to YOUR email
```

## 2. Provision
```
terraform init
terraform plan      # review what will be created (should be ~15 resources, all free/cheap)
terraform apply     # type yes
```
Then CONFIRM the SNS subscription email AWS sends you (click the link) or the billing
alarm can never notify you.

## 3. Load data into the lake
Produce gold locally first (run_gold_spark.py), then upload:
```
aws s3 cp ../data/processed/gold/ s3://<lake_bucket>/gold/ --recursive
```
(`<lake_bucket>` is printed by `terraform output lake_bucket`.)

## 4. Catalog it (Glue crawler — runs in seconds)
```
aws glue start-crawler --name ffa-gold-crawler
aws glue get-crawler   --name ffa-gold-crawler --query "Crawler.State"
```
Wait for state READY. Tables now exist in Glue DB `ffa_lake` (prefixed `gold_`).

## 5. Query in Athena
Console -> Athena -> Workgroup `ffa-workgroup` -> Database `ffa_lake`:
```
SELECT * FROM gold_fraud_rate_by_category ORDER BY fraud_rate DESC;
SELECT merchant_id, total_amount FROM gold_top_merchants ORDER BY total_amount DESC LIMIT 10;
```

## 6. TEAR DOWN when done (stops all charges)
```
terraform destroy   # type yes
```
This deletes the bucket, crawlers, catalog, workgroup, KMS key (7-day window), and alarm.
Your Terraform code stays; only the cloud resources are removed.

## Cost note
S3 storage for this dataset is a few cents/month; each crawler run and Athena query is
fractions of a cent. The expensive AWS services (MSK/EMR/MWAA/Snowflake) are intentionally
NOT built here — they are designed in PHASE7_AWS_DESIGN.md.
