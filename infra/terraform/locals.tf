locals {
  wake_function_name = "${var.project}-wake"
  wake_function_arn  = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.wake_function_name}"
}