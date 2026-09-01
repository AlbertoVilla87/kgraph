data "archive_file" "wake" {
  type        = "zip"
  source_file = "${path.module}/lambda/start_instance.py"
  output_path = "${path.module}/lambda/_wake.zip"
}

resource "aws_lambda_function" "wake" {
  function_name    = local.wake_function_name
  role             = aws_iam_role.wake.arn
  handler          = "start_instance.handler"
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  timeout          = 420
  memory_size      = 256
  filename         = data.archive_file.wake.output_path
  source_code_hash = filebase64sha256("${path.module}/lambda/start_instance.py")

  environment {
    variables = {
      EC2_INSTANCE_ID     = aws_instance.backend.id
      WAKE_LAMBDA_ARN     = local.wake_function_arn
      WAKE_SCHEDULER_ROLE = aws_iam_role.wake_scheduler.arn
      AUTO_STOP_SECONDS   = var.auto_stop_seconds
      STATE_TIMEOUT       = var.state_timeout_seconds
      STOP_SCHEDULE_NAME  = "${var.project}-auto-stop"
    }
  }
}

resource "aws_cloudwatch_log_group" "wake" {
  name              = "/aws/lambda/${local.wake_function_name}"
  retention_in_days = 7
}

resource "aws_lambda_function_url" "wake" {
  function_name      = local.wake_function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["*"]
  }
}

resource "aws_lambda_permission" "wake_scheduler" {
  action         = "lambda:InvokeFunction"
  function_name  = local.wake_function_name
  principal      = "scheduler.amazonaws.com"
  source_account = data.aws_caller_identity.current.account_id
}