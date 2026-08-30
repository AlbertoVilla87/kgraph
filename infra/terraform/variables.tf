variable "region" {
  description = "Selected Region del proyecto AWS (los recursos regionales viven aquí)."
  type        = string
  default     = "eu-north-1"
}

variable "project" {
  description = "Prefijo de nombres (sin puntos; también va en nombres globales como el bucket)."
  type        = string
  default     = "kgraph-astrolabe"
}

variable "instance_type" {
  description = "t3.large (quick) o t3.xlarge (deep + Ollama)."
  type        = string
  default     = "t3.large"
}

variable "root_volume_size_gb" {
  type    = number
  default = 30
}

variable "root_volume_type" {
  type    = string
  default = "gp3"
}

variable "auto_stop_seconds" {
  description = "Anti-olvido: segundos de VM encendida antes de que el Scheduler la pare."
  type        = number
  default     = 10800
}

variable "state_timeout_seconds" {
  description = "Máx. segundos que la función wake espera a que el EC2 pase a running."
  type        = number
  default     = 300
}

variable "frontend_bucket" {
  description = "Nombre global del bucket S3 del frontend (ha de ser único en AWS)."
  type        = string
  default     = "kgraph-astrolabe-frontend"
}

variable "bucket_force_destroy" {
  description = "Borrar el bucket aunque tenga objetos (solo para pruebas)."
  type        = bool
  default     = false
}