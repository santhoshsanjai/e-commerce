# DNS records, when the domains are in Route 53. Otherwise the same records are outputs
# (dns_records_to_add) for whoever manages the DNS.

locals {
  manage_dns = var.route53_zone_id != null
  cert_validation = {
    for o in aws_acm_certificate.sites.domain_validation_options : o.domain_name => {
      name  = o.resource_record_name
      type  = o.resource_record_type
      value = o.resource_record_value
    }
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each        = local.manage_dns ? local.cert_validation : {}
  zone_id         = var.route53_zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.value]
  ttl             = 300
  allow_overwrite = true
}

resource "aws_route53_record" "sites" {
  for_each = local.manage_dns ? toset([var.buyer_domain, var.admin_domain]) : toset([])
  zone_id  = var.route53_zone_id
  name     = each.value
  type     = "A"
  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "dkim" {
  count   = local.manage_dns ? 3 : 0
  zone_id = var.route53_zone_id
  name    = "${aws_sesv2_email_identity.domain.dkim_signing_attributes[0].tokens[count.index]}._domainkey.${var.email_domain}"
  type    = "CNAME"
  records = ["${aws_sesv2_email_identity.domain.dkim_signing_attributes[0].tokens[count.index]}.dkim.amazonses.com"]
  ttl     = 1800
}
