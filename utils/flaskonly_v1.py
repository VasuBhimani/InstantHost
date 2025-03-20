import subprocess
import time
import os
import tempfile
import json

def fun_flaskonly_v1(session_name, dockerfile_path, image_name, terraform_dir, port_no=8123, aws_region="us-east-1"):
    """
    Build a Docker image and deploy it to AWS ECS Fargate with load balancing.
    
    Args:
        session_name: Name of the tmux session to use
        dockerfile_path: Path to the Dockerfile
        image_name: Name for the Docker image
        terraform_dir: Directory containing Terraform scripts
        port_no: Port number the container exposes (default: 8123)
        aws_region: AWS region to deploy to (default: us-east-1)
        
    Returns:
        dict: Deployment status and endpoint URL if successful
    """
    # IMPORTANT: Make sure port_no is an integer
    port_no = int(port_no)
    
    print(f"Starting deployment in tmux session: {session_name}")
    print(f"Container will expose port: {port_no}")
    
    # Ensure tmux session exists
    if not _ensure_tmux_session(session_name):
        return {"status": "error", "message": "Failed to create tmux session"}
    
    # Create temporary build script
    build_script = _create_build_script(aws_region)
    
    try:
        # Step 1: Build Docker image and push to ECR
        if not _build_docker_image(session_name, dockerfile_path, image_name, build_script, aws_region):
            return {"status": "error", "message": "Docker build failed"}
        
        # Step 2: Deploy with Terraform
        print("Docker build successful. Deploying with Terraform...")
        endpoint_url = _deploy_terraform(session_name, terraform_dir, image_name, port_no, aws_region)
        
        if not endpoint_url:
            return {"status": "error", "message": "Terraform deployment failed"}
        
        print(f"Deployment successful! Endpoint URL: {endpoint_url}")
        return {
            "status": "success",
            "message": "Deployment completed successfully",
            "endpoint_url": endpoint_url,
            "port": port_no
        }
    finally:
        # Clean up temporary files
        if os.path.exists(build_script):
            os.remove(build_script)




def _ensure_tmux_session(session_name):
    """Ensure the tmux session exists, create if it doesn't"""
    try:
        # Check if session exists
        check_cmd = f"tmux has-session -t {session_name} 2>/dev/null"
        session_exists = subprocess.run(check_cmd, shell=True).returncode == 0
        
        if not session_exists:
            # Create new session
            create_cmd = f"tmux new-session -d -s {session_name}"
            subprocess.run(create_cmd, shell=True, check=True)
            time.sleep(1)  # Brief pause to ensure session is ready
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error with tmux session: {e}")
        return False

def _create_build_script(aws_region):
    """Create temporary Docker build script"""
    script_content = """#!/bin/bash
set -e  # Exit on any error

DOCKER_FILE_PATH=$1
IMAGE_NAME=$2
AWS_REGION=$3

echo "Building Docker image: $IMAGE_NAME from $DOCKER_FILE_PATH"
cd $(dirname $DOCKER_FILE_PATH)
docker build -t $IMAGE_NAME -f $(basename $DOCKER_FILE_PATH) .

echo "BUILD_COMPLETE"
"""
    
    # Write script to temporary file
    fd, script_path = tempfile.mkstemp(suffix='.sh')
    with os.fdopen(fd, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(script_path, 0o755)
    return script_path


def _run_in_tmux(session_name, command, wait_for_output=False, output_file=None):
    """Run a command in the tmux session and optionally wait for output"""
    try:
        # Clear any previous output if we're capturing
        if output_file and wait_for_output:
            if os.path.exists(output_file):
                os.remove(output_file)
                
        # Run command in session
        run_cmd = f'tmux send-keys -t {session_name} "{command}" C-m'
        subprocess.run(run_cmd, shell=True, check=True)
        
        # If we need to wait for output
        if wait_for_output and output_file:
            timeout = 1800  # 30 minutes timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        content = f.read().strip()
                    if content:
                        return content
                time.sleep(5)
            
            print("Timed out waiting for command output")
            return None
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command in tmux: {e}")
        return None

def _build_docker_image(session_name, dockerfile_path, image_name, build_script, aws_region):
    """Build Docker image in tmux session and push to ECR"""
    print(f"Building Docker image '{image_name}' from {dockerfile_path}")
    
    # Create temp output file
    output_file = tempfile.mktemp()
    
    # Build Docker image
    build_cmd = f"{build_script} '{dockerfile_path}' '{image_name}' '{aws_region}' > {output_file} 2>&1"
    _run_in_tmux(session_name, build_cmd)
    
    # Wait for a moment to ensure build completes
    time.sleep(5)
    
    # Verify the image exists
    verify_cmd = f"docker image ls {image_name} --format '{{{{.Repository}}}}' | grep -q '{image_name}' && echo 'BUILD_SUCCESS' > {output_file}"
    _run_in_tmux(session_name, verify_cmd)
    
    # Wait for verification
    time.sleep(2)
    
    # Check if build succeeded
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            content = f.read()
            if 'BUILD_SUCCESS' in content:
                # Push to ECR - using a more reliable command structure
                push_script = tempfile.mktemp(suffix='.sh')
                with open(push_script, 'w') as f:
                    f.write(f"""#!/bin/bash
set -e

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# Set ECR Repository URL
ECR_REPO_URL="$AWS_ACCOUNT_ID.dkr.ecr.{aws_region}.amazonaws.com"
echo "ECR Repository URL: $ECR_REPO_URL"

# Set full image name
ECR_IMAGE="$ECR_REPO_URL/{image_name}"
echo "ECR Image: $ECR_IMAGE"

# Tag the image
echo "Tagging image: docker tag {image_name} $ECR_IMAGE"
docker tag {image_name} $ECR_IMAGE

# Login to ECR
echo "Logging into ECR"
aws ecr get-login-password --region {aws_region} | docker login --username AWS --password-stdin $ECR_REPO_URL

# Create repository if it doesn't exist
echo "Checking if repository exists"
if ! aws ecr describe-repositories --repository-names {image_name} --region {aws_region} 2>/dev/null; then
    echo "Creating repository: {image_name}"
    aws ecr create-repository --repository-name {image_name} --region {aws_region}
fi

# Push image to ECR
echo "Pushing image: $ECR_IMAGE"
docker push $ECR_IMAGE

echo "ECR_PUSH_SUCCESS"
""")
                os.chmod(push_script, 0o755)
                
                # Run the script
                push_cmd = f"{push_script} > {output_file} 2>&1"
                _run_in_tmux(session_name, push_cmd)
                
                # Wait for script to complete
                max_wait_time = 300  # 5 minutes
                start_time = time.time()
                while time.time() - start_time < max_wait_time:
                    if os.path.exists(output_file):
                        with open(output_file, 'r') as f:
                            content = f.read()
                            if 'ECR_PUSH_SUCCESS' in content:
                                print("Successfully built and pushed image to ECR")
                                # Clean up temp script
                                if os.path.exists(push_script):
                                    os.remove(push_script)
                                return True
                    time.sleep(2)
    
    print("Docker build or push failed or timed out")
    return False


def _deploy_terraform(session_name, terraform_dir, image_name, port_no, aws_region):
    """Deploy with Terraform in tmux session"""
    print(f"Deploying infrastructure with Terraform from {terraform_dir} for port {port_no}")
    
    # Create temp output file for Terraform
    output_file = tempfile.mktemp()
    
    # Always recreate Terraform files to ensure correct format
    _create_terraform_files(terraform_dir, aws_region, True)
    
    # Initialize and apply Terraform - pass port as number
    terraform_cmd = f"""cd {terraform_dir} && \
    export TF_VAR_image_name='{image_name}' && \
    export TF_VAR_aws_region='{aws_region}' && \
    export TF_VAR_container_port={port_no} && \
    terraform init && \
    terraform apply -auto-approve && \
    terraform output -raw load_balancer_url > {output_file}"""
    
    _run_in_tmux(session_name, terraform_cmd, wait_for_output=True, output_file=output_file)
    
    # Check for Terraform output
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            endpoint_url = f.read().strip()
        
        if endpoint_url:
            return endpoint_url
    
    print("Terraform deployment failed or didn't produce an endpoint URL")
    return None




def _create_terraform_files(terraform_dir, aws_region, force_recreate=False):
    """Create Terraform files with explicit type handling for container port"""
    os.makedirs(terraform_dir, exist_ok=True)
    
    # Create variables.tf
    variables_tf_path = os.path.join(terraform_dir, 'variables.tf')
    if force_recreate or not os.path.exists(variables_tf_path):
        with open(variables_tf_path, 'w') as f:
            f.write('''variable "aws_region" {
  description = "The AWS region to deploy to"
  type        = string
}

variable "image_name" {
  description = "The name of the Docker image"
  type        = string
}

variable "container_port" {
  description = "The port the container exposes"
  type        = number
}

variable "task_cpu" {
  description = "CPU units for the task"
  default     = 256
}

variable "task_memory" {
  description = "Memory for the task in MiB"
  default     = 512
}

variable "desired_task_count" {
  description = "The desired number of tasks to run"
  default     = 2
}

variable "min_task_count" {
  description = "The minimum number of tasks to run"
  default     = 1
}

variable "max_task_count" {
  description = "The maximum number of tasks to run"
  default     = 10
}''')
    
    # Create main.tf that uses default VPC and handles port as a number
    main_tf_path = os.path.join(terraform_dir, 'main.tf')
    if force_recreate or not os.path.exists(main_tf_path):
        with open(main_tf_path, 'w') as f:
            f.write('''provider "aws" {
  region = var.aws_region
}

# Get ECR repository
data "aws_ecr_repository" "app" {
  name = var.image_name
}

# Reference the default VPC and subnets instead of creating new ones
data "aws_vpc" "default" {
  default = true
}

data "aws_subnet" "default_a" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = ["${var.aws_region}a"]
  }
  filter {
    name   = "default-for-az"
    values = [true]
  }
}

data "aws_subnet" "default_b" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = ["${var.aws_region}b"]
  }
  filter {
    name   = "default-for-az"
    values = [true]
  }
}

# Security Groups
resource "aws_security_group" "lb_sg" {
  name        = "${var.image_name}-lb-sg"
  description = "Allow HTTP inbound traffic"
  vpc_id      = data.aws_vpc.default.id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs_sg" {
  name        = "${var.image_name}-ecs-sg"
  description = "Allow traffic from ALB"
  vpc_id      = data.aws_vpc.default.id
  
  ingress {
    # Use numeric port directly
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.lb_sg.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Load Balancer
resource "aws_lb" "app_lb" {
  name               = "${var.image_name}-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb_sg.id]
  subnets            = [data.aws_subnet.default_a.id, data.aws_subnet.default_b.id]
}

resource "aws_lb_target_group" "app" {
  name        = "${var.image_name}-tg"
  # Use numeric port directly
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"
  
  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
    path                = "/"
    interval            = 30
  }
}

resource "aws_lb_listener" "app" {
  load_balancer_arn = aws_lb.app_lb.arn
  port              = 80
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# IAM Roles
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.image_name}-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Resources
resource "aws_ecs_cluster" "app_cluster" {
  name = "${var.image_name}-cluster"
}

resource "aws_ecs_task_definition" "app" {
  family                   = var.image_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  
  # IMPORTANT: Using direct numeric values in the JSON for container port
  container_definitions = jsonencode([
    {
      name      = var.image_name
      image     = "${data.aws_ecr_repository.app.repository_url}:latest"
      essential = true
      
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.image_name}"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/ecs/${var.image_name}"
  retention_in_days = 30
}

resource "aws_ecs_service" "app" {
  name            = "${var.image_name}-service"
  cluster         = aws_ecs_cluster.app_cluster.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_task_count
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = [data.aws_subnet.default_a.id, data.aws_subnet.default_b.id]
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = var.image_name
    container_port   = var.container_port
  }
  
  depends_on = [aws_lb_listener.app]
}

# Auto Scaling
resource "aws_appautoscaling_target" "app_target" {
  max_capacity       = var.max_task_count
  min_capacity       = var.min_task_count
  resource_id        = "service/${aws_ecs_cluster.app_cluster.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "app_cpu" {
  name               = "${var.image_name}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.app_target.resource_id
  scalable_dimension = aws_appautoscaling_target.app_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.app_target.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}

resource "aws_appautoscaling_policy" "app_memory" {
  name               = "${var.image_name}-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.app_target.resource_id
  scalable_dimension = aws_appautoscaling_target.app_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.app_target.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}

# Output
output "load_balancer_url" {
  value = "http://${aws_lb.app_lb.dns_name}"
}''')
