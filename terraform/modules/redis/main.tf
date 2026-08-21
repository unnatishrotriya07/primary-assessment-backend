variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "cache_subnets" { type = list(string) }
variable "app_sgs" {
  type    = list(string)
  default = []
}

locals {
  name_prefix = "momentum-${var.environment}"
}

# Security group: Redis only from app SGs.
resource "aws_security_group" "redis" {
  name        = "${local.name_prefix}-redis"
  description = "Redis (Celery broker) access"
  vpc_id      = var.vpc_id
  tags        = { Name = "${local.name_prefix}-redis-sg" }
}

resource "aws_security_group_rule" "ingress" {
  count                    = length(var.app_sgs)
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = aws_security_group.redis.id
  source_security_group_id = var.app_sgs[count.index]
}

resource "aws_elasticache_subnet_group" "this" {
  name       = "${local.name_prefix}-redis-subnets"
  subnet_ids = var.cache_subnets
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.name_prefix}-redis"
  description                = "Momentum ${var.environment} Celery broker"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.environment == "production" ? "cache.t4g.small" : "cache.t3.micro"
  num_cache_clusters         = 1
  parameter_group_name       = "default.redis7"
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [aws_security_group.redis.id]
  port                       = 6379
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled           = var.environment == "production"
  tags                       = { Name = "${local.name_prefix}-redis" }
}

output "redis_url" {
  value     = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
  sensitive = true
}

output "security_group_id" { value = aws_security_group.redis.id }
