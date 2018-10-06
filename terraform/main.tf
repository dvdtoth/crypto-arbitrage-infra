variable "aws_profile" {
  type        = "string"
  description = "AWS profile"
}

variable "aws_region" {
  type        = "string"
  default     = "eu-west-1"
  description = "AWS region"
}

variable "shard" {
  type = "string"
}

variable "retention" {
  type = "string"
}

output "kinesis-arn" {
  value = "${aws_kinesis_stream.kinesis.arn}"
}
