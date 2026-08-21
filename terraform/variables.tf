variable "environment" {
  description = "Deployment environment (staging | production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "domain_name" {
  description = "Public domain for the ALB (production only; staging uses ALB DNS)."
  type        = string
  default     = ""
}

variable "nat_count" {
  description = "Number of NAT gateways (1 for lean startup, 2+ for HA)."
  type        = number
  default     = 1
}

variable "multi_az" {
  description = "Multi-AZ for RDS."
  type        = bool
  default     = false
}

variable "rds_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "image_backend" {
  description = "Backend ECR image tag (e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com/momentum-backend:abc123)"
  type        = string
}

variable "image_frontend" {
  description = "Frontend ECR image tag. Set by the frontend repo's CD; placeholder until first frontend deploy."
  type        = string
  default     = "momentum-frontend:unset"
}

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
