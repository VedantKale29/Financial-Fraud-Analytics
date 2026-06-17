resource "aws_sns_topic" "billing" {
  provider = aws.useast1
  name     = "ffa-billing-alerts"
}

resource "aws_sns_topic_subscription" "billing_email" {
  provider  = aws.useast1
  topic_arn = aws_sns_topic.billing.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "billing" {
  provider            = aws.useast1
  alarm_name          = "ffa-estimated-charges-over-${var.billing_threshold_usd}usd"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600 # 6h (billing metric updates a few times/day)
  statistic           = "Maximum"
  threshold           = var.billing_threshold_usd
  alarm_description   = "Month-to-date estimated AWS charges exceeded threshold."
  dimensions = {
    Currency = "USD"
  }
  alarm_actions = [aws_sns_topic.billing.arn]
}
