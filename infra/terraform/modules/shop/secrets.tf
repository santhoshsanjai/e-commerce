# Secrets the API needs, generated here and kept in Secrets Manager. ECS injects them as environment
# variables at start-up; they never appear in task definitions or logs. (They are in the Terraform
# state too, which lives in the encrypted, private state bucket.)

resource "random_password" "jwt" {
  length  = 64
  special = false
}

# A Fernet key: 32 random bytes, URL-safe base64.
resource "random_bytes" "mfa_key" {
  length = 32
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.name}/app"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    JWT_SECRET         = random_password.jwt.result
    MFA_ENCRYPTION_KEY = replace(replace(random_bytes.mfa_key.base64, "+", "-"), "/", "_")
  })
}

locals {
  db_secret_arn = aws_db_instance.main.master_user_secret[0].secret_arn
}
