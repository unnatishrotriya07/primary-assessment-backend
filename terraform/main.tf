# Momentum — Terraform root configuration.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state is configured per-environment via envs/<env>/backend.tf
  # using the `-backend-config` flag (state bucket is bootstrapped first).
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "momentum"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── VPC + network ────────────────────────────────────────────────────────────
module "vpc" {
  source      = "./modules/vpc"
  environment = var.environment
  region      = var.aws_region
  nat_count   = var.nat_count
}

# ── Data stores ──────────────────────────────────────────────────────────────
module "rds" {
  source         = "./modules/rds"
  environment    = var.environment
  vpc_id         = module.vpc.vpc_id
  db_subnets     = module.vpc.db_subnet_ids
  app_sgs        = module.ecs.app_security_group_ids
  multi_az       = var.multi_az
  instance_class = var.rds_instance_class
}

module "redis" {
  source        = "./modules/redis"
  environment   = var.environment
  vpc_id        = module.vpc.vpc_id
  cache_subnets = module.vpc.db_subnet_ids
  app_sgs       = module.ecs.app_security_group_ids
}

module "s3" {
  source      = "./modules/s3"
  environment = var.environment
}

module "params" {
  source       = "./modules/params"
  environment  = var.environment
  database_url = module.rds.database_url
  redis_url    = module.redis.redis_url
}

# ── IAM + compute ────────────────────────────────────────────────────────────
module "iam" {
  source      = "./modules/iam"
  environment = var.environment
}

module "ecs" {
  source               = "./modules/ecs"
  environment          = var.environment
  vpc_id               = module.vpc.vpc_id
  private_subnets      = module.vpc.private_subnet_ids
  image_backend        = var.image_backend
  image_frontend       = var.image_frontend
  api_replicas         = var.api_replicas
  next_replicas        = var.next_replicas
  worker_replicas      = var.worker_replicas
  execution_role_arn   = module.iam.execution_role_arn
  task_role_arn        = module.iam.task_role_arn
  rds_security_group   = module.rds.security_group_id
  redis_security_group = module.redis.security_group_id
}

# ── ALB / ingress ────────────────────────────────────────────────────────────
module "alb" {
  source          = "./modules/alb"
  environment     = var.environment
  vpc_id          = module.vpc.vpc_id
  public_subnets  = module.vpc.public_subnet_ids
  api_sg          = module.ecs.api_security_group_id
  next_sg         = module.ecs.next_security_group_id
  api_target_arn  = module.ecs.api_target_group_arn
  next_target_arn = module.ecs.next_target_group_arn
  domain_name     = var.domain_name
}
