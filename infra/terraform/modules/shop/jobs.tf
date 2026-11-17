# Every few minutes: send queued order emails, retry failed ones and delete old sent ones
# (`python -m app.cli send-emails`). Emails normally go out straight after the change; this is
# the safety net when SES was briefly unavailable.

resource "aws_scheduler_schedule" "send_emails" {
  name                         = "${var.name}-send-emails"
  schedule_expression          = "rate(5 minutes)"
  schedule_expression_timezone = "UTC"
  flexible_time_window {
    mode = "OFF"
  }
  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.scheduler.arn
    ecs_parameters {
      task_definition_arn = replace(aws_ecs_task_definition.jobs.arn, "/:\\d+$/", "")
      launch_type         = "FARGATE"
      task_count          = 1
      network_configuration {
        subnets          = aws_subnet.public[*].id
        security_groups  = [aws_security_group.tasks.id]
        assign_public_ip = true
      }
    }
    retry_policy {
      maximum_retry_attempts = 0
    }
  }
}
