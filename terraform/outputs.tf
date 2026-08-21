output "alb_dns_name" {
  description = "Load balancer DNS (point your domain / test against this)."
  value       = module.alb.alb_dns_name
}

output "media_bucket" {
  value = module.s3.media_bucket
}

output "reports_bucket" {
  value = module.s3.reports_bucket
}

output "database_url" {
  description = "RDS connection URL (sensitive)."
  value       = module.rds.database_url
  sensitive   = true
}

output "redis_url" {
  description = "ElastiCache Redis URL (sensitive)."
  value       = module.redis.redis_url
  sensitive   = true
}

output "migrate_task_definition_arn" {
  description = "One-off migration task definition for `alembic upgrade head`."
  value       = module.ecs.migrate_task_definition_arn
}
