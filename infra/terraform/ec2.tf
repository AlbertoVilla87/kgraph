data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "backend" {
  name        = "${var.project}-backend"
  description = "HTTP/HTTPS públicos hacia el backend (nginx del compose)."
  vpc_id      = data.aws_vpc.default.id

  tags = { Name = "${var.project}-backend" }
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.backend.id
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
  description       = "HTTP (demo, sin TLS todavía)"
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.backend.id
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
  description       = "HTTPS (requiere dominio + certificado ACM)"
}

resource "aws_instance" "backend" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.backend.id]
  iam_instance_profile   = aws_iam_instance_profile.backend.name

  root_block_device {
    volume_type = var.root_volume_type
    volume_size = var.root_volume_size_gb
    encrypted   = true
  }

  user_data = <<-EOF
    #!/bin/bash
    logs=/var/log/astrolabe-userdata.log
    exec >>"$logs" 2>&1
    echo "[start] $(date)"
    dnf install -y docker git curl unzip
    systemctl enable --now docker
    usermod -aG docker ec2-user
    dnf install -y docker-compose-plugin || true
    mkdir -p /opt/astrolabe
    echo "[done] $(date)"
  EOF

  metadata_options {
    http_tokens = "required"
  }

  tags = { Name = "${var.project}-backend" }
}

resource "aws_eip" "backend" {
  domain   = "vpc"
  instance = aws_instance.backend.id

  tags = { Name = "${var.project}-backend-eip" }
}

resource "aws_iam_role" "backend" {
  name               = "${var.project}-backend"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "backend_ssm" {
  role       = aws_iam_role.backend.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "backend" {
  name = "${var.project}-backend"
  role = aws_iam_role.backend.name
}