variable "environment" { type = string }

locals {
  name_prefix = "momentum-${var.environment}"
}

data "aws_iam_policy_document" "assume_ecs" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Execution role: pull images, ship logs, read SSM params.
resource "aws_iam_role" "execution" {
  name               = "${local.name_prefix}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.assume_ecs.json
}

resource "aws_iam_role_policy_attachment" "execution_ecr" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "execution_logs" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

data "aws_iam_policy_document" "execution_ssm" {
  statement {
    actions   = ["ssm:GetParameter", "ssm:GetParameters"]
    resources = ["arn:aws:ssm:*:*:parameter/momentum/${var.environment}/*"]
  }
}

resource "aws_iam_policy" "execution_ssm" {
  name   = "${local.name_prefix}-ecs-execution-ssm"
  policy = data.aws_iam_policy_document.execution_ssm.json
}

resource "aws_iam_role_policy_attachment" "execution_ssm_attach" {
  role       = aws_iam_role.execution.name
  policy_arn = aws_iam_policy.execution_ssm.arn
}

# Task role: least-privilege S3 access to the media bucket.
resource "aws_iam_role" "task" {
  name               = "${local.name_prefix}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.assume_ecs.json
}

data "aws_iam_policy_document" "task_s3" {
  statement {
    actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
    resources = [
      "arn:aws:s3:::${var.environment == "production" ? "momentum-production-*" : "momentum-staging-*"}",
      "arn:aws:s3:::${var.environment == "production" ? "momentum-production-*" : "momentum-staging-*"}/*",
    ]
  }
}

resource "aws_iam_policy" "task_s3" {
  name   = "${local.name_prefix}-ecs-task-s3"
  policy = data.aws_iam_policy_document.task_s3.json
}

resource "aws_iam_role_policy_attachment" "task_s3_attach" {
  role       = aws_iam_role.task.name
  policy_arn = aws_iam_policy.task_s3.arn
}

output "execution_role_arn" { value = aws_iam_role.execution.arn }
output "task_role_arn" { value = aws_iam_role.task.arn }
