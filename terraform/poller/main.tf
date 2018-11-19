data "aws_ami" "amazon_linux" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  owners = ["amazon"]
}

resource "aws_eip" "lb" {
  instance = "${aws_instance.poller.id}"
  vpc      = true
}

resource "aws_instance" "poller" {
  ami           = "${data.aws_ami.amazon_linux.id}"
  instance_type = "t2.small"
  key_name = "crypto"
  network_interface {
     network_interface_id = "${element(aws_network_interface.interfaces.*.id, count.index * 2)}"
     device_index = 0
  } 
  user_data = "${data.template_file.init.rendered}"
  tags {
    Name = "Poller"
    Environment = "${var.environment}"
    ManagedBy = "Terraform"
  }
}