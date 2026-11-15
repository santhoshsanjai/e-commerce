output "buyer_url" {
  value = "https://${var.buyer_domain}"
}

output "admin_url" {
  value = "https://${var.admin_domain}"
}

output "load_balancer_dns_name" {
  value = aws_lb.main.dns_name
}

output "media_url" {
  value = "https://${aws_cloudfront_distribution.media.domain_name}"
}

output "ecr_repositories" {
  value = { for k, r in aws_ecr_repository.this : k => r.repository_url }
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "api_task_family" {
  value = aws_ecs_task_definition.api.family
}

output "task_network" {
  description = "For one-off tasks (migrations, CLI commands): subnets and security group."
  value = {
    subnets         = aws_subnet.public[*].id
    security_groups = [aws_security_group.tasks.id]
  }
}

output "backup_bucket" {
  value = aws_s3_bucket.this["backups"].bucket
}

output "dns_records_to_add" {
  description = "Only when route53_zone_id is null: add these at your DNS provider."
  value = var.route53_zone_id != null ? [] : concat(
    [for v in local.cert_validation : { name = v.name, type = v.type, value = v.value }],
    [for d in [var.buyer_domain, var.admin_domain] : { name = d, type = "CNAME", value = aws_lb.main.dns_name }],
    [for t in aws_sesv2_email_identity.domain.dkim_signing_attributes[0].tokens : {
      name = "${t}._domainkey.${var.email_domain}", type = "CNAME", value = "${t}.dkim.amazonses.com"
    }],
  )
}
