variable "environment" { type = string }
variable "database_url" {
  type      = string
  sensitive = true
}
variable "redis_url" {
  type      = string
  sensitive = true
}

locals {
  prefix = "/momentum/${var.environment}"
}

# Free-tier SSM Parameter Store (standard tier). Secrets are injected into ECS
# task definitions via `valueFrom`, keeping the app cloud-agnostic (env vars).
resource "aws_ssm_parameter" "secret_key" {
  name  = "${local.prefix}/SECRET_KEY"
  type  = "SecureString"
  value = var.environment == "production" ? "CHANGE_ME_IN_SECRETS" : "dev-secret-key"
}

resource "aws_ssm_parameter" "database_url" {
  name  = "${local.prefix}/DATABASE_URL"
  type  = "SecureString"
  value = var.database_url
}

resource "aws_ssm_parameter" "redis_url" {
  name  = "${local.prefix}/CELERY_BROKER_URL"
  type  = "SecureString"
  value = var.redis_url
}

resource "aws_ssm_parameter" "redis_result" {
  name  = "${local.prefix}/CELERY_RESULT_BACKEND"
  type  = "SecureString"
  value = var.redis_url
}

resource "aws_ssm_parameter" "app_env" {
  name  = "${local.prefix}/APP_ENV"
  type  = "String"
  value = var.environment
}

output "parameter_arns" {
  value = [
    aws_ssm_parameter.secret_key.arn,
    aws_ssm_parameter.database_url.arn,
    aws_ssm_parameter.redis_url.arn,
    aws_ssm_parameter.redis_result.arn,
  ]
}
