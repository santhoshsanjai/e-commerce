variable "name" {
  type        = string
  description = "Prefix for every resource, e.g. shop-staging."
}

variable "environment" {
  type        = string
  description = "Value of the API's ENVIRONMENT setting: staging or production."
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "image_tag" {
  type        = string
  description = "Container image tag (the git commit) to run for the API and both web apps."
}

variable "buyer_domain" {
  type        = string
  description = "Host name of the shop, e.g. staging.shop.example.in."
}

variable "admin_domain" {
  type        = string
  description = "Host name of the admin portal, e.g. admin.staging.shop.example.in."
}

variable "email_domain" {
  type        = string
  description = "Domain emails are sent from (verified in SES), e.g. shop.example.in."
}

variable "email_from" {
  type        = string
  description = "From header for emails, e.g. \"Shop <no-reply@shop.example.in>\"."
}

variable "route53_zone_id" {
  type        = string
  default     = null
  description = "Route 53 hosted zone for the domains. Leave null if DNS is elsewhere: the DNS records to add are then outputs."
}

variable "alert_emails" {
  type        = list(string)
  description = "Addresses that receive alarm notifications (each must confirm the subscription email)."
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_max_allocated_storage" {
  type    = number
  default = 100
}

variable "db_multi_az" {
  type    = bool
  default = false
}

variable "db_backup_retention_days" {
  type    = number
  default = 14
}

variable "api_cpu" {
  type    = number
  default = 512
}

variable "api_memory" {
  type    = number
  default = 1024
}

variable "api_desired_count" {
  type    = number
  default = 1
}

variable "web_desired_count" {
  type    = number
  default = 1
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "backup_retention_days" {
  type        = number
  default     = 90
  description = "How long nightly database dumps are kept in S3."
}

variable "backup_schedule" {
  type        = string
  default     = "cron(30 20 * * ? *)"
  description = "When the nightly dump runs (UTC). The default is 02:00 in India."
}
