variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "public_subnets" { type = list(string) }
variable "api_sg" { type = string }
variable "next_sg" { type = string }
variable "api_target_arn" { type = string }
variable "next_target_arn" { type = string }
variable "domain_name" {
  type    = string
  default = ""
}

locals {
  name_prefix = "momentum-${var.environment}"
}

# ALB security group: allow 443/80 from the internet.
resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb"
  description = "ALB ingress"
  vpc_id      = var.vpc_id
  tags        = { Name = "${local.name_prefix}-alb-sg" }
}

resource "aws_security_group_rule" "alb_https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "alb_http" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "alb_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 65535
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.alb.id
}

# Allow API + Next SGs to receive traffic from the ALB.
resource "aws_security_group_rule" "api_from_alb" {
  type                     = "ingress"
  from_port                = 5000
  to_port                  = 5000
  protocol                 = "tcp"
  security_group_id        = var.api_sg
  source_security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "next_from_alb" {
  type                     = "ingress"
  from_port                = 3000
  to_port                  = 3000
  protocol                 = "tcp"
  security_group_id        = var.next_sg
  source_security_group_id = aws_security_group.alb.id
}

resource "aws_lb" "this" {
  name                       = "${local.name_prefix}-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = var.public_subnets
  enable_deletion_protection = var.environment == "production"
  tags                       = { Name = "${local.name_prefix}-alb" }
}

# HTTPS listener (ACM cert provisioned out-of-band / validated via Route 53).
resource "aws_lb_listener" "https" {
  count             = var.domain_name != "" ? 1 : 0
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.domain_name != "" ? aws_acm_certificate_validation.this[0].certificate_arn : ""
  default_action {
    type             = "forward"
    target_group_arn = var.next_target_arn
  }
}

# HTTP listener: redirect to HTTPS, default to Next.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      protocol    = "HTTPS"
      port        = "443"
      status_code = "HTTP_301"
    }
  }
}

# Path-based rules: /api /voice /static → API target group.
resource "aws_lb_listener_rule" "api" {
  count        = var.domain_name != "" ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 100
  action {
    type             = "forward"
    target_group_arn = var.api_target_arn
  }
  condition {
    path_pattern { values = ["/api/*", "/voice/*", "/static/*"] }
  }
}

# ACM cert (request + validation records). Requires Route 53 hosted zone.
data "aws_route53_zone" "domain" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name
}

resource "aws_acm_certificate" "this" {
  count             = var.domain_name != "" ? 1 : 0
  domain_name       = var.domain_name
  validation_method = "DNS"
}

resource "aws_route53_record" "cert_validation" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = data.aws_route53_zone.domain[0].zone_id
  name    = tolist(aws_acm_certificate.this[0].domain_validation_options)[0].resource_record_name
  type    = tolist(aws_acm_certificate.this[0].domain_validation_options)[0].resource_record_type
  records = [tolist(aws_acm_certificate.this[0].domain_validation_options)[0].resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "this" {
  count                   = var.domain_name != "" ? 1 : 0
  certificate_arn         = aws_acm_certificate.this[0].arn
  validation_record_fqdns = [aws_route53_record.cert_validation[0].fqdn]
}

resource "aws_route53_record" "app" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = data.aws_route53_zone.domain[0].zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = aws_lb.this.dns_name
    zone_id                = aws_lb.this.zone_id
    evaluate_target_health = true
  }
}

output "alb_dns_name" { value = aws_lb.this.dns_name }
output "alb_zone_id" { value = aws_lb.this.zone_id }
