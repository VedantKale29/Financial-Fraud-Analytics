data "aws_iam_policy_document" "glue_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue_crawler" {
  name               = "ffa-glue-crawler-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

# AWS-managed baseline for Glue service operations
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_crawler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# scoped access to ONLY the lake bucket + its KMS key
data "aws_iam_policy_document" "glue_lake_access" {
  statement {
    sid       = "ListLakeBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.lake.arn]
  }
  statement {
    sid       = "ReadLakeObjects"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.lake.arn}/*"]
  }
  statement {
    sid       = "UseLakeKmsKey"
    actions   = ["kms:Decrypt", "kms:DescribeKey"]
    resources = [aws_kms_key.lake.arn]
  }
}

resource "aws_iam_role_policy" "glue_lake_access" {
  name   = "ffa-glue-lake-access"
  role   = aws_iam_role.glue_crawler.id
  policy = data.aws_iam_policy_document.glue_lake_access.json
}
