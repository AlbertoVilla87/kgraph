output "backend_instance_id" {
  value = aws_instance.backend.id
}

output "backend_public_ip" {
  value = aws_eip.backend.public_ip
}

output "backend_console" {
  description = "Enlace a la consola con la instancia seleccionada."
  value       = "https://${var.region}.console.aws.amazon.com/ec2/home?region=${var.region}#InstanceDetails:instanceId=${aws_instance.backend.id}"
}

output "wake_url" {
  description = "URL pública de la función 'encender VM'. pública de verdad (auth_type NONE)."
  value       = aws_lambda_function_url.wake.function_url
}

output "wake_command" {
  value = "curl '${aws_lambda_function_url.wake.function_url}'"
}

output "stop_command" {
  value = "curl '${aws_lambda_function_url.wake.function_url}'?action=stop"
}

output "frontend_url" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}