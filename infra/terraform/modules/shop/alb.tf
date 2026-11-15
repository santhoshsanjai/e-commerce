# One HTTPS load balancer for both sites. /api/* goes straight to the API on either host name; other
# paths go to the shop or admin web container by host name. HTTP redirects to HTTPS.

resource "aws_acm_certificate" "sites" {
  domain_name               = var.buyer_domain
  subject_alternative_names = [var.admin_domain]
  validation_method         = "DNS"
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "sites" {
  certificate_arn         = aws_acm_certificate.sites.arn
  validation_record_fqdns = var.route53_zone_id == null ? null : [for r in aws_route53_record.cert_validation : r.fqdn]
}

resource "aws_lb" "main" {
  name                       = var.name
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = aws_subnet.public[*].id
  drop_invalid_header_fields = true
  idle_timeout               = 60
  enable_deletion_protection = var.environment == "production"
}

resource "aws_lb_target_group" "api" {
  name                 = "${var.name}-api"
  port                 = 8000
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.main.id
  deregistration_delay = 30
  health_check {
    path                = "/health/ready"
    matcher             = "200"
    interval            = 15
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_target_group" "web" {
  for_each             = toset(["buyer", "admin"])
  name                 = "${var.name}-${each.key}"
  port                 = 80
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.main.id
  deregistration_delay = 15
  health_check {
    path    = "/"
    matcher = "200"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.sites.certificate_arn
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not found"
      status_code  = "404"
    }
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
  condition {
    host_header {
      values = [var.buyer_domain, var.admin_domain]
    }
  }
}

resource "aws_lb_listener_rule" "web" {
  for_each     = { buyer = var.buyer_domain, admin = var.admin_domain }
  listener_arn = aws_lb_listener.https.arn
  priority     = each.key == "buyer" ? 20 : 30
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web[each.key].arn
  }
  condition {
    host_header {
      values = [each.value]
    }
  }
}
