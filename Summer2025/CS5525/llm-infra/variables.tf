variable "project" {
  description = "The project ID"
  default     = "thomasjones-llm-project-2025"
}

variable "region" {
  description = "The GCP region for resources."
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone for resources."
  default     = "us-central1-c"
}

variable "secondary_model_name" {
  description = "The HuggingFace model name for the secondary classifier."
  type        = string
  default     = "jackhhao/jailbreak-classifier"
}

variable "secondary_model_location" {
  description = "The path within the GCS bucket where the secondary model is stored."
  type        = string
  default     = "/storage/models/jailbreak-classifier"
}

variable "llm_stub_port" {
  description = "The container port for the LLM stub service"
  type        = number
  default     = 8081
}

variable "sfilter_port" {
  description = "The container port for the SFilter service"
  type        = number
  default     = 8083
}

variable "bfilter_port" {
  description = "The container port for the BFilter service"
  type        = number
  default     = 8082
}