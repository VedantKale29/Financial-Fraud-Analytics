terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = "financial-fraud-analytics"
      ManagedBy = "terraform"
      Env       = "dev"
    }
  }
}

# Billing metrics (EstimatedCharges) are only published in us-east-1,
# so the billing alarm uses this aliased provider regardless of var.region.
provider "aws" {
  alias  = "useast1"
  region = "us-east-1"
}
