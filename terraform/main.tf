provider "aws" {
  region = "us-east-1"  # Change as needed
}

# VPC and Security Group
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true

  tags = {
    Name = "kyc-vpc"
  }
}

resource "aws_security_group" "kyc" {
  name        = "kyc-sg"
  description = "Security group for KYC microservice"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "kyc-sg"
  }
}

# EC2 Instance
resource "aws_instance" "kyc" {
  ami           = "ami-0c55b159cbfafe1f0"  # Ubuntu 20.04 LTS
  instance_type = "t3.medium"
  key_name      = "your-key-name"  # Change this

  vpc_security_group_ids = [aws_security_group.kyc.id]
  subnet_id              = aws_subnet.main.id

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
    iops        = 3000
  }

  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y docker.io docker-compose
              systemctl enable docker
              systemctl start docker
              
              # Create app directory
              mkdir -p /opt/kyc
              cd /opt/kyc
              
              # Download docker-compose.yml and .env
              aws s3 cp s3://your-bucket/docker-compose.yml .
              aws s3 cp s3://your-bucket/.env .
              
              # Start the application
              docker-compose up -d
              EOF

  tags = {
    Name = "kyc-server"
  }
}

# Elastic IP
resource "aws_eip" "kyc" {
  instance = aws_instance.kyc.id
  vpc      = true
}

# S3 bucket for backups
resource "aws_s3_bucket" "backups" {
  bucket = "kyc-backups-${random_string.suffix.result}"

  tags = {
    Name = "KYC Backups"
  }
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# IAM role for EC2
resource "aws_iam_role" "kyc" {
  name = "kyc-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "kyc" {
  name = "kyc-policy"
  role = aws_iam_role.kyc.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.backups.arn,
          "${aws_s3_bucket.backups.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "kyc" {
  name = "kyc-profile"
  role = aws_iam_role.kyc.name
} 