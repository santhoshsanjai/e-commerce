# PostgreSQL 18 on RDS: encrypted, automatic backups with point-in-time recovery, and a password
# that RDS keeps in Secrets Manager and can rotate (the API reads it at start-up).

resource "aws_db_subnet_group" "main" {
  name       = var.name
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_parameter_group" "main" {
  name   = "${var.name}-pg18"
  family = "postgres18"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
  # Log statements slower than one second, for the "API slow" alarm investigations.
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
}

resource "aws_db_instance" "main" {
  identifier     = var.name
  engine         = "postgres"
  engine_version = "18"
  instance_class = var.db_instance_class

  db_name                     = "ecommerce"
  username                    = "shop"
  manage_master_user_password = true

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  parameter_group_name   = aws_db_parameter_group.main.name
  publicly_accessible    = false
  multi_az               = var.db_multi_az

  backup_retention_period  = var.db_backup_retention_days
  backup_window            = "19:00-19:30" # 00:30-01:00 in India, before the nightly dump
  maintenance_window       = "sun:20:00-sun:21:00"
  copy_tags_to_snapshot    = true
  delete_automated_backups = false

  auto_minor_version_upgrade      = true
  performance_insights_enabled    = true
  enabled_cloudwatch_logs_exports = ["postgresql"]

  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.name}-final"
}
