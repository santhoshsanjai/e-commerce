# ECS on Fargate: the API, the two web containers, and the nightly backup task.

resource "aws_ecs_cluster" "main" {
  name = var.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "this" {
  for_each          = toset(["api", "buyer", "admin", "backup"])
  name              = "/${var.name}/${each.key}"
  retention_in_days = var.log_retention_days
}

locals {
  region    = data.aws_region.current.region
  image     = { for k, r in aws_ecr_repository.this : k => "${r.repository_url}:${var.image_tag}" }
  media_url = "https://${aws_cloudfront_distribution.media.domain_name}"

  log_config = { for k, g in aws_cloudwatch_log_group.this : k => {
    logDriver = "awslogs"
    options = {
      awslogs-group         = g.name
      awslogs-region        = local.region
      awslogs-stream-prefix = k
    }
  } }

  db_secrets = [
    { name = "DB_USER", valueFrom = "${local.db_secret_arn}:username::" },
    { name = "DB_PASSWORD", valueFrom = "${local.db_secret_arn}:password::" },
  ]

  api_secrets = concat(local.db_secrets, [
    { name = "JWT_SECRET", valueFrom = "${aws_secretsmanager_secret.app.arn}:JWT_SECRET::" },
    { name = "MFA_ENCRYPTION_KEY", valueFrom = "${aws_secretsmanager_secret.app.arn}:MFA_ENCRYPTION_KEY::" },
  ])

  api_environment = [for k, v in {
    ENVIRONMENT           = var.environment
    DB_HOST               = aws_db_instance.main.address
    DB_PORT               = tostring(aws_db_instance.main.port)
    DB_NAME               = aws_db_instance.main.db_name
    CORS_ORIGINS          = jsonencode(["https://${var.buyer_domain}", "https://${var.admin_domain}"])
    COOKIE_SECURE         = "true"
    S3_ENDPOINT_URL       = ""
    S3_ACCESS_KEY         = ""
    S3_SECRET_KEY         = ""
    S3_REGION             = local.region
    MEDIA_BUCKET          = aws_s3_bucket.this["media"].bucket
    PRIVATE_BUCKET        = aws_s3_bucket.this["private"].bucket
    MEDIA_PUBLIC_BASE_URL = local.media_url
    EMAIL_BACKEND         = "ses"
    EMAIL_FROM            = var.email_from
    SES_REGION            = local.region
    BUYER_SITE_URL        = "https://${var.buyer_domain}"
    ADMIN_SITE_URL        = "https://${var.admin_domain}"
    STAFF_MFA_REQUIRED    = "true"
    FORWARDED_ALLOW_IPS   = var.vpc_cidr
  } : { name = k, value = v }]
}

# --- IAM -------------------------------------------------------------------------------------

data "aws_iam_policy_document" "ecs_tasks_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Used by ECS itself to pull images, write logs and read the secrets it injects.
resource "aws_iam_role" "execution" {
  name               = "${var.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_trust.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.app.arn, local.db_secret_arn]
    }]
  })
}

# What the API code may do: read and write its two buckets, and send email.
resource "aws_iam_role" "api" {
  name               = "${var.name}-api"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_trust.json
}

resource "aws_iam_role_policy" "api" {
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [
          "${aws_s3_bucket.this["media"].arn}/*",
          "${aws_s3_bucket.this["private"].arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = [
          aws_s3_bucket.this["media"].arn,
          aws_s3_bucket.this["private"].arn,
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["ses:SendEmail"]
        Resource = "*"
        Condition = {
          StringEquals = { "ses:FromAddress" = regex("[^<\\s]+@[^>\\s]+", var.email_from) }
        }
      },
    ]
  })
}

# The nightly backup may only add dumps to the backup bucket.
resource "aws_iam_role" "backup" {
  name               = "${var.name}-backup"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_trust.json
}

resource "aws_iam_role_policy" "backup" {
  role = aws_iam_role.backup.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject"]
      Resource = "${aws_s3_bucket.this["backups"].arn}/db/*"
    }]
  })
}

# --- task definitions ------------------------------------------------------------------------

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.api.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  # Every API task first runs the database migrations in a short-lived "migrate" container (they
  # take turns on a lock and are no-ops once applied); the API starts only if they succeed. So a
  # deploy migrates before new code takes traffic, and a failed migration rolls the deploy back.
  container_definitions = jsonencode([
    {
      name             = "migrate"
      image            = local.image["api"]
      essential        = false
      command          = ["alembic", "upgrade", "head"]
      environment      = local.api_environment
      secrets          = local.api_secrets
      logConfiguration = local.log_config["api"]
    },
    {
      name             = "api"
      image            = local.image["api"]
      essential        = true
      portMappings     = [{ containerPort = 8000, protocol = "tcp" }]
      environment      = local.api_environment
      secrets          = local.api_secrets
      dependsOn        = [{ containerName = "migrate", condition = "SUCCESS" }]
      logConfiguration = local.log_config["api"]
    },
  ])
}

resource "aws_ecs_task_definition" "web" {
  for_each                 = toset(["buyer", "admin"])
  family                   = "${var.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name         = "web"
    image        = local.image[each.key]
    essential    = true
    portMappings = [{ containerPort = 80, protocol = "tcp" }]
    environment = [
      # The load balancer sends /api/* to the API directly; nginx's own /api proxy is unused here
      # but needs an address that resolves.
      { name = "API_UPSTREAM", value = "http://127.0.0.1:8000" },
      { name = "MEDIA_ORIGIN", value = local.media_url },
    ]
    logConfiguration = local.log_config[each.key]
  }])
}

resource "aws_ecs_task_definition" "backup" {
  family                   = "${var.name}-backup"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.backup.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name      = "backup"
    image     = local.image["backup"]
    essential = true
    environment = [
      { name = "BACKUP_BUCKET", value = aws_s3_bucket.this["backups"].bucket },
      { name = "PGHOST", value = aws_db_instance.main.address },
      { name = "PGPORT", value = tostring(aws_db_instance.main.port) },
      { name = "PGDATABASE", value = aws_db_instance.main.db_name },
      { name = "PGSSLMODE", value = "require" },
      { name = "AWS_REGION", value = local.region },
    ]
    secrets = [
      { name = "PGUSER", valueFrom = "${local.db_secret_arn}:username::" },
      { name = "PGPASSWORD", valueFrom = "${local.db_secret_arn}:password::" },
    ]
    logConfiguration = local.log_config["backup"]
  }])
}

# Scheduled API jobs (see jobs.tf): the API image and settings, without the web server.
resource "aws_ecs_task_definition" "jobs" {
  family                   = "${var.name}-jobs"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.api.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name             = "job"
    image            = local.image["api"]
    essential        = true
    command          = ["python", "-m", "app.cli", "send-emails"]
    environment      = local.api_environment
    secrets          = local.api_secrets
    logConfiguration = local.log_config["api"]
  }])
}

# --- services --------------------------------------------------------------------------------

locals {
  services = {
    api   = { task = aws_ecs_task_definition.api.arn, tg = aws_lb_target_group.api.arn, container = "api", port = 8000, count = var.api_desired_count }
    buyer = { task = aws_ecs_task_definition.web["buyer"].arn, tg = aws_lb_target_group.web["buyer"].arn, container = "web", port = 80, count = var.web_desired_count }
    admin = { task = aws_ecs_task_definition.web["admin"].arn, tg = aws_lb_target_group.web["admin"].arn, container = "web", port = 80, count = var.web_desired_count }
  }
}

resource "aws_ecs_service" "this" {
  for_each               = local.services
  name                   = each.key
  cluster                = aws_ecs_cluster.main.id
  task_definition        = each.value.task
  desired_count          = each.value.count
  launch_type            = "FARGATE"
  enable_execute_command = false
  propagate_tags         = "SERVICE"

  # Start new tasks before stopping old ones, and roll back on its own if they never get healthy
  # (for the API: never ready, e.g. the migration didn't run).
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  health_check_grace_period_seconds = 30

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = each.value.tg
    container_name   = each.value.container
    container_port   = each.value.port
  }

  depends_on = [aws_lb_listener.https]
}
