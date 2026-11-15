# Sending email with SES. New accounts start in the SES sandbox (can only send to verified
# addresses); request production access in the SES console before go-live.

resource "aws_sesv2_configuration_set" "main" {
  configuration_set_name = var.name
  reputation_options {
    reputation_metrics_enabled = true
  }
  suppression_options {
    suppressed_reasons = ["BOUNCE", "COMPLAINT"]
  }
}

resource "aws_sesv2_email_identity" "domain" {
  email_identity         = var.email_domain
  configuration_set_name = aws_sesv2_configuration_set.main.configuration_set_name
}
