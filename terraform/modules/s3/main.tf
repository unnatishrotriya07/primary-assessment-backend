variable "environment" { type = string }

locals {
  name_prefix = "momentum-${var.environment}"
}

resource "aws_s3_bucket" "media" {
  bucket        = "${local.name_prefix}-media"
  force_destroy = false
}

resource "aws_s3_bucket" "reports" {
  bucket        = "${local.name_prefix}-reports"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# Lifecycle: Standard-IA after 30d; expire interview audio after 90d
# (replaces cleanup_expired_audio_task).
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    id     = "archive-audio"
    status = "Enabled"
    filter {
      prefix = "interviews/"
    }
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    expiration { days = 90 }
  }
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "media_bucket" { value = aws_s3_bucket.media.id }
output "reports_bucket" { value = aws_s3_bucket.reports.id }
