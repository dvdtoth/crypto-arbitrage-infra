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

resource "aws_network_interface" "interfaces" {
  count    = "${var.proxies * 2}"
# Same subnet for now. To be improved when full VPC is defined with 3-3 public-private subnets
  subnet_id     = "${element(data.aws_subnet_ids.subnet_ids.ids, 1)}"
  private_ips     = ["172.31.16.${count.index + 10}"]
  security_groups = ["sg-0ff5da62ece2a0983"]
  tags {
    Name = "ProxyNIC${count.index + 1}"
    Environment = "${var.environment}"
    ManagedBy = "Terraform"
  }
}

resource "aws_eip" "ips" {
  depends_on = ["aws_network_interface.interfaces", "aws_instance.proxy"]
  count    = "${var.proxies * 2}"
  network_interface = "${element(aws_network_interface.interfaces.*.id, count.index)}"
  tags {
    Name = "ProxyEIP${count.index + 1}"
    Environment = "${var.environment}"
    ManagedBy = "Terraform"
  }
}

resource "aws_instance" "proxy" {
  count         = "${var.proxies}"
  ami           = "${data.aws_ami.amazon_linux.id}"
  instance_type = "t2.micro"
  key_name = "crypto"
  network_interface {
     network_interface_id = "${element(aws_network_interface.interfaces.*.id, count.index * 2)}"
     device_index = 0
  } 
  network_interface {
     network_interface_id = "${element(aws_network_interface.interfaces.*.id, (count.index * 2) + 1)}"
     device_index = 1
  }
  user_data = "${element(data.template_file.init.*.rendered, count.index)}"
  tags {
    Name = "Proxy${count.index + 1}"
    Environment = "${var.environment}"
    ManagedBy = "Terraform"
  }
}

data "aws_vpc" "default_vpc" {
    default = true
}
data "aws_subnet_ids" "subnet_ids" {
  vpc_id = "${data.aws_vpc.default_vpc.id}"
}

data "template_file" "init" {
  count    = "${var.proxies}"
  template = "${file("init.tpl")}"

  vars {
    squid_addresses = "${element(data.template_file.squid.*.rendered, count.index)}"
    haproxy_servers = "${join("\n", data.template_file.haproxy.*.rendered)}"
  }
}

data "template_file" "squid" {
  template = "${file("${path.module}/squid.tpl")}"
  count    = "${var.proxies}"
  vars {
    private_ip1 = "172.31.16.${count.index * 2 + 10}"
    private_ip2 = "172.31.16.${count.index * 2 + 11}"
  }
}

data "template_file" "haproxy" {
  template = "${file("${path.module}/haproxy.tpl")}"
  count    = "${var.proxies}"
  vars {
    ip = "172.31.16.${count.index * 2 + 10}"
    count1 = "${count.index * 2}"
    count2 = "${count.index * 2 + 1}"
  }
}

resource "aws_route53_record" "proxy1" {
  zone_id = "ZV2NCER43JK3Y"
  name    = "proxy1"
  type    = "A"
  ttl     = "300"
  records = ["172.31.16.10", "172.31.16.12"]
}

output "ip" {
  description = "Connect on port 3000 to proxy load balancers"
  # TODO
  value = ["${aws_eip.ips.*.public_ip}"]
}

output "hostname" {
  description = "FQDN"
  value = "${aws_route53_record.proxy1.fqdn}"
}