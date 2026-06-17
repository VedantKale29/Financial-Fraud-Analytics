variable "region" {
  description = "AWS region for the lake (Glue/Athena/S3)."
  type        = string
  default     = "us-east-1"
}

variable "bucket_prefix" {
  description = "Globally-unique prefix for the lake bucket. A random suffix is appended."
  type        = string
  default     = "ffa-lake"
}

variable "alert_email" {
  description = "Email to receive the billing alarm (you must confirm the SNS subscription email)."
  type        = string
}

variable "billing_threshold_usd" {
  description = "Email you when month-to-date estimated charges cross this many USD."
  type        = number
  default     = 2
}
