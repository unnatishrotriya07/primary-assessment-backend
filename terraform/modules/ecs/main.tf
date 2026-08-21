variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnets" { type = list(string) }
variable "image_backend" { type = string }
variable "image_frontend" { type = string }
variable "api_replicas" {
  type    = number
  default = 2
}
variable "next_replicas" {
  type    = number
  default = 2
}
variable "worker_replicas" {
  type    = number
  default = 1
}
variable "execution_role_arn" { type = string }
variable "task_role_arn" { type = string }
variable "rds_security_group" { type = string }
variable "redis_security_group" { type = string }

locals {
  name_prefix = "momentum-${var.environment}"
  ssm_prefix  = "/momentum/${var.environment}"
}

resource "aws_ecs_cluster" "this" {
  name = local.name_prefix
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Shared: security groups for the API + Next + worker services.
resource "aws_security_group" "api" {
  name        = "${local.name_prefix}-api"
  description = "FastAPI :5000"
  vpc_id      = var.vpc_id
  tags        = { Name = "${local.name_prefix}-api-sg" }
}
resource "aws_security_group" "next" {
  name        = "${local.name_prefix}-next"
  description = "Next.js :3000"
  vpc_id      = var.vpc_id
  tags        = { Name = "${local.name_prefix}-next-sg" }
}

# ── API service ──────────────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn
  container_definitions = jsonencode([
    {
      name         = "api"
      image        = var.image_backend
      essential    = true
      portMappings = [{ containerPort = 5000, protocol = "tcp" }]
      environment = [
        { name = "APP_ENV", value = var.environment },
        { name = "PORT", value = "5000" },
      ]
      secrets = [
        { name = "DATABASE_URL", valueFrom = "${local.ssm_prefix}/DATABASE_URL" },
        { name = "CELERY_BROKER_URL", valueFrom = "${local.ssm_prefix}/CELERY_BROKER_URL" },
        { name = "SECRET_KEY", valueFrom = "${local.ssm_prefix}/SECRET_KEY" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.environment == "production" ? "us-east-1" : "us-east-1"
          "awslogs-stream-prefix" = "api"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  name            = "${local.name_prefix}-api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_replicas
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 5000
  }
  # Rolling deploy (zero-downtime via min/max healthy). Blue/Green via CodeDeploy
  # can be layered on later without reworking the task definition.
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
}

# ── Next.js service ──────────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "next" {
  family                   = "${local.name_prefix}-next"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.execution_role_arn
  container_definitions = jsonencode([
    {
      name         = "next"
      image        = var.image_frontend
      essential    = true
      portMappings = [{ containerPort = 3000, protocol = "tcp" }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.next.name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "next"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "next" {
  name            = "${local.name_prefix}-next"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.next.arn
  desired_count   = var.next_replicas
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [aws_security_group.next.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.next.arn
    container_name   = "next"
    container_port   = 3000
  }
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
}

# ── Celery worker service ────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name_prefix}-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn
  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = var.image_backend
      essential = true
      command   = ["celery", "-A", "app.core.celery_app.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
      environment = [
        { name = "APP_ENV", value = var.environment },
      ]
      secrets = [
        { name = "DATABASE_URL", valueFrom = "${local.ssm_prefix}/DATABASE_URL" },
        { name = "CELERY_BROKER_URL", valueFrom = "${local.ssm_prefix}/CELERY_BROKER_URL" },
        { name = "SECRET_KEY", valueFrom = "${local.ssm_prefix}/SECRET_KEY" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.worker.name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "worker"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "worker" {
  name            = "${local.name_prefix}-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_replicas
  launch_type     = "FARGATE"
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 100
  }
  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }
}

# ── One-off DB migration task (run by CI/CD before deploy) ──────────────────
resource "aws_ecs_task_definition" "migrate" {
  family                   = "${local.name_prefix}-migrate"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn
  container_definitions = jsonencode([
    {
      name      = "migrate"
      image     = var.image_backend
      essential = true
      command   = ["alembic", "upgrade", "head"]
      environment = [
        { name = "APP_ENV", value = var.environment },
      ]
      secrets = [
        { name = "DATABASE_URL", valueFrom = "${local.ssm_prefix}/DATABASE_URL" },
        { name = "SECRET_KEY", valueFrom = "${local.ssm_prefix}/SECRET_KEY" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "migrate"
        }
      }
    }
  ])
}

# ── CloudWatch log groups ────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name_prefix}/api"
  retention_in_days = var.environment == "production" ? 90 : 14
}
resource "aws_cloudwatch_log_group" "next" {
  name              = "/ecs/${local.name_prefix}/next"
  retention_in_days = var.environment == "production" ? 90 : 14
}
resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${local.name_prefix}/worker"
  retention_in_days = var.environment == "production" ? 90 : 14
}

# ── Target groups (owned by ALB module via outputs) ─────────────────────────
resource "aws_lb_target_group" "api" {
  name        = "${local.name_prefix}-api-tg"
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check {
    path                = "/"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    interval            = 30
  }
  tags = { Name = "${local.name_prefix}-api-tg" }
}

resource "aws_lb_target_group" "next" {
  name        = "${local.name_prefix}-next-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check {
    path                = "/"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    interval            = 30
  }
  tags = { Name = "${local.name_prefix}-next-tg" }
}

# Wire RDS/Redis SGs to allow the API+worker SG.
resource "aws_security_group_rule" "api_to_rds" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = var.rds_security_group
  source_security_group_id = aws_security_group.api.id
}

resource "aws_security_group_rule" "api_to_redis" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = var.redis_security_group
  source_security_group_id = aws_security_group.api.id
}

output "api_security_group_id" { value = aws_security_group.api.id }
output "next_security_group_id" { value = aws_security_group.next.id }
output "app_security_group_ids" { value = [aws_security_group.api.id, aws_security_group.next.id] }
output "api_target_group_arn" { value = aws_lb_target_group.api.arn }
output "next_target_group_arn" { value = aws_lb_target_group.next.arn }
output "migrate_task_definition_arn" { value = aws_ecs_task_definition.migrate.arn }
