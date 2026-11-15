# Staging: the whole shop on AWS, sized small. Applied by the deploy workflow
# (.github/workflows/deploy-staging.yml); see infra/README.md for the first run.

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }
  # Bucket comes from -backend-config (the bootstrap output), so it isn't hard-coded here.
  backend "s3" {
    key          = "staging/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "shop", Environment = "staging", ManagedBy = "terraform" }
  }
}

variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "image_tag" {
  type        = string
  description = "Git commit to deploy; the workflow passes it."
}

variable "buyer_domain" {
  type = string
}

variable "admin_domain" {
  type = string
}

variable "email_domain" {
  type = string
}

variable "email_from" {
  type = string
}

variable "route53_zone_id" {
  type        = string
  default     = ""
  description = "Route 53 hosted zone id for the domains, or empty when DNS is managed elsewhere."
}

variable "alert_emails" {
  type = list(string)
}

module "shop" {
  source = "../../modules/shop"

  name            = "shop-staging"
  environment     = "staging"
  image_tag       = var.image_tag
  buyer_domain    = var.buyer_domain
  admin_domain    = var.admin_domain
  email_domain    = var.email_domain
  email_from      = var.email_from
  route53_zone_id = var.route53_zone_id == "" ? null : var.route53_zone_id
  alert_emails    = var.alert_emails

  db_instance_class = "db.t4g.micro"
  db_multi_az       = false
  api_desired_count = 1
  web_desired_count = 1
}

output "shop" {
  value = {
    buyer_url              = module.shop.buyer_url
    admin_url              = module.shop.admin_url
    load_balancer_dns_name = module.shop.load_balancer_dns_name
    media_url              = module.shop.media_url
  }
}

output "deploy" {
  description = "Read by the deploy workflow."
  value = {
    ecr_repositories = module.shop.ecr_repositories
    cluster_name     = module.shop.cluster_name
    api_task_family  = module.shop.api_task_family
    task_network     = module.shop.task_network
  }
}

output "dns_records_to_add" {
  value = module.shop.dns_records_to_add
}
