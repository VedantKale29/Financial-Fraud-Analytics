# random suffix so the bucket name is globally unique
resource "random_id" "suffix" {
  byte_length = 3
}

locals {
  bucket_name = "${var.bucket_prefix}-${random_id.suffix.hex}"
}

# ---- KMS key for encryption at rest ----
resource "aws_kms_key" "lake" {
  description             = "KMS key for the FFA S3 lake"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "lake" {
  name          = "alias/ffa-lake"
  target_key_id = aws_kms_key.lake.key_id
}

# ---- the lake bucket ----
resource "aws_s3_bucket" "lake" {
  bucket = local.bucket_name
}

# block all public access
resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# versioning -> immutability/auditability of raw + bronze
resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

# default SSE-KMS encryption on every object
resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.lake.arn
    }
    bucket_key_enabled = true
  }
}

# lifecycle: expire old noncurrent versions to control cost
resource "aws_s3_bucket_lifecycle_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# the medallion "folders" (S3 has no real dirs; these are zero-byte prefixes)
resource "aws_s3_object" "prefixes" {
  for_each = toset(["bronze/", "silver/", "gold/", "athena-results/"])
  bucket   = aws_s3_bucket.lake.id
  key      = each.value
}
