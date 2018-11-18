variable "proxies" {
  type = "string"
  description = "Number of proxy instances (adds 2 public IPs for each)"
}

variable "environment" {
  type = "string"
  description = "Environment"
  default = "Production"
}

variable "aws_profile" {
  type        = "string"
  description = "AWS profile"
  default     = "crypto"
}

variable "aws_region" {
  type        = "string"
  default     = "eu-west-1"
  description = "AWS region"
}