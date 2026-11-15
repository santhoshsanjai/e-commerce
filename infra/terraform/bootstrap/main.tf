# One-time setup per AWS account, run by a person with admin rights:
#
#   cd infra/terraform/bootstrap
#   terraform init
#   terraform apply -var github_repository=santhoshsanjai/e-commerce
#
# It creates the bucket that holds Terraform state for every environment, and an IAM role that the
# GitHub deploy workflow assumes through OpenID Connect, so no AWS access keys exist anywhere.
# This configuration's own state stays on the machine that ran it (it is small and rarely changes).

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, ManagedBy = "terraform-bootstrap" }
  }
}

variable "region" {
  type        = string
  default     = "ap-south-1"
  description = "Home region for the state bucket (Mumbai by default)."
}

variable "project" {
  type    = string
  default = "shop"
}

variable "github_repository" {
  type        = string
  description = "owner/name of the GitHub repository allowed to deploy."
}

variable "github_environments" {
  type        = list(string)
  default     = ["staging", "production"]
  description = "GitHub environments whose workflow runs may assume the deploy role."
}

data "aws_caller_identity" "current" {}

# --- Terraform state -------------------------------------------------------------------------

resource "aws_s3_bucket" "state" {
  bucket = "${var.project}-terraform-state-${data.aws_caller_identity.current.account_id}"
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- GitHub deploy role (OIDC) ---------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "github_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # Only workflow jobs that run in one of the named GitHub environments of this repository.
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [for env in var.github_environments : "repo:${var.github_repository}:environment:${env}"]
    }
  }
}

resource "aws_iam_role" "deploy" {
  name                 = "${var.project}-github-deploy"
  assume_role_policy   = data.aws_iam_policy_document.github_trust.json
  max_session_duration = 3600
}

# Terraform manages most of the stack (VPC, ECS, RDS, IAM roles for tasks), so the deploy role
# needs broad rights in this account. Keep this account for the shop only.
resource "aws_iam_role_policy_attachment" "deploy_admin" {
  role       = aws_iam_role.deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "state_bucket" {
  value       = aws_s3_bucket.state.bucket
  description = "Put this in envs/*/backend.tf (bucket)."
}

output "deploy_role_arn" {
  value       = aws_iam_role.deploy.arn
  description = "Set as the AWS_DEPLOY_ROLE_ARN variable on the GitHub environments."
}
