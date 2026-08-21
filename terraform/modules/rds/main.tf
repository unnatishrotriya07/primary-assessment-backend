variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "db_subnets" { type = list(string) }
variable "app_sgs" {
  type    = list(string)
  default = []
}
variable "multi_az" {
  type    = bool
  default = false
}
variable "instance_class" {
  type    = string
  default = "db.t4g.micro"
}

locals {
  name_prefix = "momentum-${var.environment}"
}

# DB subnet group
resource "aws_db_subnet_group" "this" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = var.db_subnets
  tags       = { Name = "${local.name_prefix}-db-subnet-group" }
}

# Security group: Postgres only from app SGs.
resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-rds"
  description = "PostgreSQL access"
  vpc_id      = var.vpc_id
  tags        = { Name = "${local.name_prefix}-rds-sg" }
}

resource "aws_security_group_rule" "ingress" {
  count                    = length(var.app_sgs)
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = var.app_sgs[count.index]
}

# RDS instance
resource "aws_db_instance" "this" {
  identifier              = "${local.name_prefix}-postgres"
  engine                  = "postgres"
  engine_version          = "15"
  instance_class          = var.instance_class
  allocated_storage       = var.environment == "production" ? 50 : 20
  storage_type            = "gp3"
  max_allocated_storage   = 100
  multi_az                = var.multi_az
  db_name                 = "momentum"
  username                = "momentum"
  password                = random_password.this.result
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  deletion_protection     = true
  skip_final_snapshot     = false
  storage_encrypted       = true
  tags                    = { Name = "${local.name_prefix}-rds" }
}

resource "random_password" "this" {
  length  = 24
  special = false
}

output "database_url" {
  value     = "postgresql://momentum:${random_password.this.result}@${aws_db_instance.this.endpoint}/momentum"
  sensitive = true
}

output "security_group_id" { value = aws_security_group.rds.id }
