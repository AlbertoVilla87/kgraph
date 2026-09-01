resource "aws_iam_role" "wake" {
  name               = "${var.project}-wake"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role" "wake_scheduler" {
  name               = "${var.project}-wake-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "wake" {
  statement {
    effect = "Allow"
    actions = [
      "ec2:StartInstances",
      "ec2:StopInstances",
      "ec2:DescribeInstances",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "scheduler:CreateSchedule",
      "scheduler:DeleteSchedule",
      "scheduler:GetSchedule",
    ]
    resources = ["*"]
  }

  statement {
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      aws_iam_role.wake_scheduler.arn
    ]
  }
}

resource "aws_iam_policy" "wake" {
  name   = "${var.project}-wake"
  policy = data.aws_iam_policy_document.wake.json
}

resource "aws_iam_role_policy_attachment" "wake" {
  role       = aws_iam_role.wake.name
  policy_arn = aws_iam_policy.wake.arn
}

resource "aws_iam_role_policy_attachment" "wake_logs" {
  role       = aws_iam_role.wake.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "wake_scheduler" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [local.wake_function_arn]
  }
}

resource "aws_iam_policy" "wake_scheduler" {
  name   = "${var.project}-wake-scheduler"
  policy = data.aws_iam_policy_document.wake_scheduler.json
}

resource "aws_iam_role_policy_attachment" "wake_scheduler" {
  role       = aws_iam_role.wake_scheduler.name
  policy_arn = aws_iam_policy.wake_scheduler.arn
}