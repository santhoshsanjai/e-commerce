# Alarms from docs/operations.md, all sent to one SNS topic that emails the people in alert_emails.

resource "aws_sns_topic" "alerts" {
  name = "${var.name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  for_each  = toset(var.alert_emails)
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

locals {
  alarm_actions = [aws_sns_topic.alerts.arn]
  lb_dims       = { LoadBalancer = aws_lb.main.arn_suffix }
}

resource "aws_cloudwatch_metric_alarm" "api_5xx_rate" {
  alarm_name          = "${var.name}-api-errors"
  alarm_description   = "More than 1% of requests failed with a server error for 5 minutes. See docs/operations.md."
  comparison_operator = "GreaterThanThreshold"
  threshold           = 1
  evaluation_periods  = 5
  datapoints_to_alarm = 5
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  metric_query {
    id          = "rate"
    expression  = "IF(requests > 20, 100 * (errors_target + errors_lb) / requests, 0)"
    label       = "5xx %"
    return_data = true
  }
  metric_query {
    id = "requests"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "RequestCount"
      dimensions  = local.lb_dims
      period      = 60
      stat        = "Sum"
    }
  }
  metric_query {
    id = "errors_target"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_5XX_Count"
      dimensions  = local.lb_dims
      period      = 60
      stat        = "Sum"
    }
  }
  metric_query {
    id = "errors_lb"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_ELB_5XX_Count"
      dimensions  = local.lb_dims
      period      = 60
      stat        = "Sum"
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "api_slow" {
  alarm_name          = "${var.name}-api-slow"
  alarm_description   = "p95 API response time above 2 s for 10 minutes."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "TargetResponseTime"
  dimensions          = { LoadBalancer = aws_lb.main.arn_suffix, TargetGroup = aws_lb_target_group.api.arn_suffix }
  extended_statistic  = "p95"
  period              = 300
  evaluation_periods  = 2
  threshold           = 2
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "unhealthy_targets" {
  for_each = {
    api   = aws_lb_target_group.api.arn_suffix
    buyer = aws_lb_target_group.web["buyer"].arn_suffix
    admin = aws_lb_target_group.web["admin"].arn_suffix
  }
  alarm_name          = "${var.name}-${each.key}-unhealthy"
  alarm_description   = "A ${each.key} instance has failed its health check for 5 minutes."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  dimensions          = { LoadBalancer = aws_lb.main.arn_suffix, TargetGroup = each.value }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 5
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "below_capacity" {
  for_each            = local.services
  alarm_name          = "${var.name}-${each.key}-below-capacity"
  alarm_description   = "Fewer ${each.key} tasks running than wanted for 5 minutes (crash loop or out of memory)."
  namespace           = "ECS/ContainerInsights"
  metric_name         = "RunningTaskCount"
  dimensions          = { ClusterName = aws_ecs_cluster.main.name, ServiceName = each.key }
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 5
  threshold           = each.value.count
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "${var.name}-api-error-lines"
  log_group_name = aws_cloudwatch_log_group.this["api"].name
  pattern        = "{ $.level = \"ERROR\" }"
  metric_transformation {
    name          = "ApiErrorLines"
    namespace     = var.name
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "api_error_lines" {
  alarm_name          = "${var.name}-api-error-logs"
  alarm_description   = "More than 10 ERROR log lines in 5 minutes."
  namespace           = var.name
  metric_name         = "ApiErrorLines"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "db" {
  for_each = {
    cpu         = { metric = "CPUUtilization", op = "GreaterThanThreshold", threshold = 80, periods = 3, desc = "Database CPU above 80% for 15 minutes." }
    storage     = { metric = "FreeStorageSpace", op = "LessThanThreshold", threshold = var.db_allocated_storage * 0.2 * 1073741824, periods = 1, desc = "Database has less than 20% of its starting storage free." }
    connections = { metric = "DatabaseConnections", op = "GreaterThanThreshold", threshold = 60, periods = 3, desc = "Database connections unusually high." }
    memory      = { metric = "FreeableMemory", op = "LessThanThreshold", threshold = 64 * 1048576, periods = 3, desc = "Database is nearly out of memory." }
  }
  alarm_name          = "${var.name}-db-${each.key}"
  alarm_description   = each.value.desc
  namespace           = "AWS/RDS"
  metric_name         = each.value.metric
  dimensions          = { DBInstanceIdentifier = aws_db_instance.main.identifier }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = each.value.periods
  threshold           = each.value.threshold
  comparison_operator = each.value.op
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

# The nightly backup must succeed at least once a day.
resource "aws_cloudwatch_log_metric_filter" "backup_done" {
  name           = "${var.name}-backup-done"
  log_group_name = aws_cloudwatch_log_group.this["backup"].name
  pattern        = "\"Backup done\""
  metric_transformation {
    name          = "BackupSucceeded"
    namespace     = var.name
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "backup_missing" {
  alarm_name          = "${var.name}-backup-missing"
  alarm_description   = "No successful nightly database backup in the last 24 hours."
  namespace           = var.name
  metric_name         = "BackupSucceeded"
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 24
  datapoints_to_alarm = 24
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "ses" {
  for_each = {
    bounce    = { metric = "Reputation.BounceRate", threshold = 0.05 }
    complaint = { metric = "Reputation.ComplaintRate", threshold = 0.001 }
  }
  alarm_name          = "${var.name}-email-${each.key}-rate"
  alarm_description   = "SES ${each.key} rate is high; sending could be paused by AWS."
  namespace           = "AWS/SES"
  metric_name         = each.value.metric
  statistic           = "Average"
  period              = 3600
  evaluation_periods  = 1
  threshold           = each.value.threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}
