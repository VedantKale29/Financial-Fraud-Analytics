output "lake_bucket" {
  description = "Name of the S3 lake bucket."
  value       = aws_s3_bucket.lake.id
}

output "kms_key_arn" {
  value = aws_kms_key.lake.arn
}

output "glue_database" {
  value = aws_glue_catalog_database.lake.name
}

output "glue_crawlers" {
  value = [for c in aws_glue_crawler.layer : c.name]
}

output "athena_workgroup" {
  value = aws_athena_workgroup.ffa.name
}

output "upload_hint" {
  description = "Copy your local gold marts to S3 like this."
  value       = "aws s3 cp data/processed/gold/ s3://${aws_s3_bucket.lake.id}/gold/ --recursive"
}
