# Define variables for secret key names (passed via CLI)
variable "access_key_name" {}
variable "secret_key_name" {}

# **Temporary AWS provider** to fetch secrets (Uses default AWS credentials)
provider "aws" {
  region = "ap-south-1"
  alias  = "secrets"
}

# Retrieve AWS credentials from Secrets Manager (Uses temporary provider)
data "aws_secretsmanager_secret" "aws_creds" {
  provider = aws.secrets
  name     = "InstantHost"  # Secret name remains constant
}

data "aws_secretsmanager_secret_version" "aws_creds_version" {
  provider  = aws.secrets
  secret_id = data.aws_secretsmanager_secret.aws_creds.id
}

# Decode secret JSON and fetch credentials dynamically
locals {
  secrets    = jsondecode(data.aws_secretsmanager_secret_version.aws_creds_version.secret_string)
  access_key = sensitive(lookup(local.secrets, var.access_key_name, "DEFAULT_ACCESS_KEY"))
  secret_key = sensitive(lookup(local.secrets, var.secret_key_name, "DEFAULT_SECRET_KEY"))
}

# **Main AWS Provider** (Uses credentials from Secrets Manager)
provider "aws" {
  region     = "ap-south-1"
  access_key = local.access_key
  secret_key = local.secret_key
}

# Create a random ID for ECR repository uniqueness
resource "random_id" "ecr_suffix" {
  byte_length = 3
}

# Define ECR repository variable
variable "ecr_repository_name" {
  description = "The base name for the ECR repository"
  type        = string
  default     = "my-ecr-repo"  # Default name (optional)
}

# Create an ECR repository with dynamic name
resource "aws_ecr_repository" "my_ecr_repo" {
  name = "${var.ecr_repository_name}-${random_id.ecr_suffix.hex}"

  image_scanning_configuration {
    scan_on_push = true
  }

  image_tag_mutability = "MUTABLE"
}

# Output ECR repository URL
output "ecr_repository_url" {
  value = aws_ecr_repository.my_ecr_repo.repository_url
}

# terraform init
# terraform apply -var="access_key_name=vasu-username" -var="secret_key_name=vasu-password" -var="ecr_repository_name=houseofit" -auto-approve -backup=/dev/null
# terraform destroy -var="access_key_name=vasu-username" -var="secret_key_name=vasu-password" -var="ecr_repository_name=houseofit" -auto-approve -backup=/dev/null

