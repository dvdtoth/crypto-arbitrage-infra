variable "aws_profile" {
  type        = "string"
  description = "AWS profile"
}

variable "aws_region" {
  type        = "string"
  default     = "eu-west-1"
  description = "AWS region"
}

resource "aws_security_group" "proxy" {
  name        = "proxy"
  description = "Proxy security group"

  ingress {
    from_port   = 3000
    to_port     = 3002
    protocol    = "tcp"
    security_groups = ["${aws_security_group.poller.id}"]
    self        = true
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = -1
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "poller" {
  name        = "poller"
  description = "Poller security group"

  ingress {
    from_port   = 9092
    to_port     = 9092
    protocol    = "tcp"
    security_groups = ["${aws_security_group.analyser.id}"]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = -1
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "analyser" {
  name        = "analyser"
  description = "Analyser security group"
  egress {
    from_port = 0
    to_port = 0
    protocol = -1
    cidr_blocks = ["0.0.0.0/0"]
  }
}