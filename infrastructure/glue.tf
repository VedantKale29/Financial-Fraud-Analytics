resource "aws_glue_catalog_database" "lake" {
  name = "ffa_lake"
}

locals {
  layers = ["bronze", "silver", "gold"]
}

resource "aws_glue_crawler" "layer" {
  for_each = toset(local.layers)

  name          = "ffa-${each.value}-crawler"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.lake.name
  # table names prefixed by layer so bronze/silver/gold don't collide
  table_prefix  = "${each.value}_"

  s3_target {
    path = "s3://${aws_s3_bucket.lake.id}/${each.value}/"
  }

  # treat each top-level folder under the layer as one table
  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableLevelConfiguration = 2
    }
  })

  # run on demand only (no schedule) -> no surprise costs
  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
}
