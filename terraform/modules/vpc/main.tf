variable "environment" { type = string }
variable "region" { type = string }
variable "nat_count" {
  type    = number
  default = 1
}

locals {
  name_prefix = "momentum-${var.environment}"
}

# VPC
resource "aws_vpc" "this" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${local.name_prefix}-vpc" }
}

# Subnets: 2 AZs for staging (lean), 3 for production.
locals {
  az_count = var.environment == "production" ? 3 : 2
  azs      = slice(data.aws_availability_zones.available.names, 0, local.az_count)
}

data "aws_availability_zones" "available" { state = "available" }

# Public subnets (ALB, NAT)
resource "aws_subnet" "public" {
  count                   = local.az_count
  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(aws_vpc.this.cidr_block, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${local.name_prefix}-public-${count.index}" }
}

# Private app subnets (ECS)
resource "aws_subnet" "private" {
  count             = local.az_count
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(aws_vpc.this.cidr_block, 8, 10 + count.index)
  availability_zone = local.azs[count.index]
  tags              = { Name = "${local.name_prefix}-private-${count.index}" }
}

# DB subnets (RDS, ElastiCache)
resource "aws_subnet" "db" {
  count             = local.az_count
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(aws_vpc.this.cidr_block, 8, 20 + count.index)
  availability_zone = local.azs[count.index]
  tags              = { Name = "${local.name_prefix}-db-${count.index}" }
}

# IGW
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = { Name = "${local.name_prefix}-igw" }
}

# NAT gateways — 1 for lean startup, one per AZ for HA.
resource "aws_eip" "nat" {
  count = var.nat_count
  tags  = { Name = "${local.name_prefix}-nat-eip-${count.index}" }
}

resource "aws_nat_gateway" "this" {
  count         = var.nat_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${local.name_prefix}-nat-${count.index}" }
}

# Route tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
  tags = { Name = "${local.name_prefix}-public-rt" }
}

resource "aws_route_table" "private" {
  count  = max(var.nat_count, 1)
  vpc_id = aws_vpc.this.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[count.index % var.nat_count].id
  }
  tags = { Name = "${local.name_prefix}-private-rt-${count.index}" }
}

# Associations
resource "aws_route_table_association" "public" {
  count          = local.az_count
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = local.az_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index % max(var.nat_count, 1)].id
}

# S3 gateway endpoint — media traffic stays inside the VPC (no NAT egress cost).
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.this.id
  service_name = "com.amazonaws.${var.region}.s3"
  route_table_ids = [
    aws_route_table.public.id,
    aws_route_table.private[0].id,
  ]
  tags = { Name = "${local.name_prefix}-s3-endpoint" }
}

output "vpc_id" { value = aws_vpc.this.id }
output "public_subnet_ids" { value = aws_subnet.public[*].id }
output "private_subnet_ids" { value = aws_subnet.private[*].id }
output "db_subnet_ids" { value = aws_subnet.db[*].id }
