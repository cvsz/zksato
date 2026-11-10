variable "aws_region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  default     = "production"
}

variable "cloudflare_api_token" {
  description = "Cloudflare API Token with Tunnel and DNS edit permissions"
  type        = string
  sensitive   = true
  default     = null
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for DNS record management"
  type        = string
  default     = null
}

variable "cloudflare_account_id" {
  description = "Cloudflare Account ID"
  type        = string
  default     = null
}
