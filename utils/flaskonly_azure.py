import subprocess
import time
import os
import tempfile
import json
from extensions import mongo

def fun_flaskonly_v1_azure(username, dockerfile_path, image_name, terraform_dir, port_no, azure_region, cleanup_on_failure=True):
    
    # IMPORTANT: Make sure port_no is an integer
    port_no = int(port_no)
    
    print(f"Starting Azure deployment in tmux session: {username}")
    print(f"Container will expose port: {port_no}")
    
    # Create new tmux session with Azure environment
    if not _create_tmux_session_with_azure(username):
        return {"status": "error", "message": "Failed to create tmux session with Azure environment"}
    
    # Create temporary build script
    build_script = _create_build_script_azure(azure_region)
    
    try:
        # Step 1: Build Docker image and push to ACR
        if not _build_docker_image_azure(username, dockerfile_path, image_name, build_script, azure_region):
          if cleanup_on_failure:
                print("Build failed. Cleaning up any created resources...")
                # cleanup_terraform_and_acr(username, terraform_dir, image_name, azure_region)
          return {"status": "error", "message": "Docker build failed"}
        
        # Step 2: Deploy with Terraform
        print("Docker build successful. Deploying with Terraform...")
        endpoint_url = _deploy_terraform_azure(username, terraform_dir, image_name, port_no, azure_region)
        
        if not endpoint_url:
          if cleanup_on_failure:
              print("Deployment failed. Cleaning up created resources...")
              # cleanup_terraform_and_acr(username, terraform_dir, image_name, azure_region)
          return {"status": "error", "message": "Terraform deployment failed"}
        
        change_dir = '''cd ../../../../'''
        _run_in_tmux(username, change_dir)

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

def _create_tmux_session_with_azure(username):
    """Create a new tmux session with Azure environment sourced"""
    try:
        # Kill existing session if it exists
        kill_cmd = f"tmux kill-session -t {username} 2>/dev/null || true"
        subprocess.run(kill_cmd, shell=True)
        
        # Create new session with Azure environment
        create_cmd = f'tmux new -d -s "{username}" "source download/abc/azure && az login --service-principal -u \\$AZURE_CLIENT_ID -p \\$AZURE_SECRET --tenant \\$AZURE_TENANT_ID && az account set --subscription \\$AZURE_SUBSCRIPTION_ID && bash"'
        subprocess.run(create_cmd, shell=True, check=True)
        
        # Give it a moment to initialize
        time.sleep(5)  # Azure login might take a bit longer
        
        # Verify session was created
        check_cmd = f"tmux has-session -t {username} 2>/dev/null"
        session_exists = subprocess.run(check_cmd, shell=True).returncode == 0
        
        if session_exists:
            print(f"Successfully created tmux session '{username}' with Azure environment")
            return True
        else:
            print(f"Failed to verify tmux session '{username}'")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Error creating tmux session with Azure environment: {e}")
        return False

def _create_build_script_azure(azure_region):
    """Create temporary Docker build script for Azure"""
    script_content = """#!/bin/bash
set -e  # Exit on any error

DOCKER_FILE_PATH=$1
IMAGE_NAME=$2
AZURE_REGION=$3

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

def _run_in_tmux(username, command, wait_for_output=False, output_file=None):
    """Run a command in the tmux session and optionally wait for output"""
    try:
        # Clear any previous output if we're capturing
        if output_file and wait_for_output:
            if os.path.exists(output_file):
                os.remove(output_file)
                
        # Run command in session
        run_cmd = f'tmux send-keys -t {username} "{command}" C-m'
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

def _build_docker_image_azure(username, dockerfile_path, image_name, build_script, azure_region):
    """Build Docker image in tmux session and push to ACR"""
    print(f"Building Docker image '{image_name}' from {dockerfile_path}")
    
    # Create temp output file
    output_file = tempfile.mktemp()
    
    # Build Docker image
    build_cmd = f"{build_script} '{dockerfile_path}' '{image_name}' '{azure_region}' > {output_file} 2>&1"
    _run_in_tmux(username, build_cmd)
    
    # Wait for a moment to ensure build completes
    time.sleep(5)
    
    # Verify the image exists
    verify_cmd = f"docker image ls {image_name} --format '{{{{.Repository}}}}' | grep -q '{image_name}' && echo 'BUILD_SUCCESS' > {output_file}"
    _run_in_tmux(username, verify_cmd)
    
    # Wait for verification
    time.sleep(2)
    
    # Check if build succeeded
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            content = f.read()
            if 'BUILD_SUCCESS' in content:
                # Push to ACR - using a more reliable command structure
                push_script = tempfile.mktemp(suffix='.sh')
                with open(push_script, 'w') as f:
                    f.write(f"""#!/bin/bash
set -e

# Get resource group and subscription info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Subscription ID: $SUBSCRIPTION_ID"

# Set ACR name (must be globally unique, lowercase alphanumeric only)
ACR_NAME="{image_name}acr${{SUBSCRIPTION_ID:0:8}}"
ACR_NAME=$(echo "$ACR_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
echo "ACR Name: $ACR_NAME"

# Resource group name
RESOURCE_GROUP="{image_name}-rg"
echo "Resource Group: $RESOURCE_GROUP"

# Create resource group if it doesn't exist
echo "Creating resource group if it doesn't exist"
az group create --name $RESOURCE_GROUP --location {azure_region}

# Create ACR if it doesn't exist
echo "Creating ACR if it doesn't exist"
if ! az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP 2>/dev/null; then
    echo "Creating ACR: $ACR_NAME"
    az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --location {azure_region}
fi

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query loginServer -o tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"

# Tag the image
ACR_IMAGE="$ACR_LOGIN_SERVER/{image_name}:latest"
echo "Tagging image: docker tag {image_name} $ACR_IMAGE"
docker tag {image_name} $ACR_IMAGE

# Login to ACR
echo "Logging into ACR"
az acr login --name $ACR_NAME

# Push image to ACR
echo "Pushing image: $ACR_IMAGE"
docker push $ACR_IMAGE

echo "ACR_PUSH_SUCCESS"
echo "ACR_NAME=$ACR_NAME" >> {output_file}
echo "RESOURCE_GROUP=$RESOURCE_GROUP" >> {output_file}
""")
                os.chmod(push_script, 0o755)
                
                # Run the script
                push_cmd = f"{push_script} > {output_file} 2>&1"
                _run_in_tmux(username, push_cmd)
                
                time.sleep(2)
                # Wait for script to complete
                max_wait_time = 600  # 10 minutes
                start_time = time.time()
                while time.time() - start_time < max_wait_time:
                    if os.path.exists(output_file):
                        with open(output_file, 'r') as f:
                            content = f.read()
                            if 'ACR_PUSH_SUCCESS' in content:
                                print("Successfully built and pushed image to ACR")
                                # Clean up temp script
                                if os.path.exists(push_script):
                                    os.remove(push_script)
                                return True
                    time.sleep(2)
    
    print("Docker build or push failed or timed out")
    return False

def _deploy_terraform_azure(username, terraform_dir, image_name, port_no, azure_region):
    """Deploy with Terraform in tmux session for Azure"""
    print(f"Deploying infrastructure with Terraform from {terraform_dir} for port {port_no}")
    
    # Create temp output file for Terraform
    output_file = tempfile.mktemp()
    
    # Always recreate Terraform files to ensure correct format
    _create_terraform_files_azure(terraform_dir, azure_region, True)
    
    # Create terraform.tfvars file with the values
    tfvars_path = os.path.join(terraform_dir, 'terraform.tfvars')
    with open(tfvars_path, 'w') as f:
        f.write(f'''azure_region = "{azure_region}"
image_name = "{image_name}"
container_port = {port_no}
''')
    
    # Initialize and apply Terraform
    terraform_cmd = f"""cd {terraform_dir} && \
    terraform init && \
    terraform apply -auto-approve && \
    terraform output -raw load_balancer_url > {output_file}"""
    
    _run_in_tmux(username, terraform_cmd, wait_for_output=True, output_file=output_file)
    
    # Check for Terraform output
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            endpoint_url = f.read().strip()
        
        if endpoint_url and endpoint_url != "null":
            return endpoint_url
    
    print("Terraform deployment failed or didn't produce an endpoint URL")
    return None

def _create_terraform_files_azure(terraform_dir, azure_region, force_recreate=False):
    """Create Terraform files for Azure Container Instances with Load Balancer"""
    os.makedirs(terraform_dir, exist_ok=True)
    
    # Create variables.tf
    variables_tf_path = os.path.join(terraform_dir, 'variables.tf')
    if force_recreate or not os.path.exists(variables_tf_path):
        with open(variables_tf_path, 'w') as f:
            f.write('''variable "azure_region" {
  description = "The Azure region to deploy to"
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

variable "cpu_cores" {
  description = "CPU cores for the container"
  default     = 1
}

variable "memory_gb" {
  description = "Memory for the container in GB"
  default     = 1
}

variable "container_count" {
  description = "Number of container instances"
  default     = 2
}''')
    
    # Create main.tf for Azure
    main_tf_path = os.path.join(terraform_dir, 'main.tf')
    if force_recreate or not os.path.exists(main_tf_path):
        with open(main_tf_path, 'w') as f:
            f.write('''terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Get current subscription info
data "azurerm_client_config" "current" {}

# Create resource group
resource "azurerm_resource_group" "main" {
  name     = "${var.image_name}-rg"
  location = var.azure_region
}

# Create ACR name (must be globally unique)
locals {
  acr_name = "${var.image_name}acr${substr(data.azurerm_client_config.current.subscription_id, 0, 8)}"
  acr_name_clean = lower(replace(local.acr_name, "/[^a-z0-9]/", ""))
}

# Get existing ACR (created during image push)
data "azurerm_container_registry" "main" {
  name                = local.acr_name_clean
  resource_group_name = azurerm_resource_group.main.name
  depends_on         = [azurerm_resource_group.main]
}

# Create virtual network
resource "azurerm_virtual_network" "main" {
  name                = "${var.image_name}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# Create subnet
resource "azurerm_subnet" "main" {
  name                 = "${var.image_name}-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
  
  delegation {
    name = "aci-delegation"
    service_delegation {
      name    = "Microsoft.ContainerInstance/containerGroups"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# Create public IP for load balancer
resource "azurerm_public_ip" "main" {
  count               = var.container_count
  name                = "${var.image_name}-pip-${count.index}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

# Create container instances
resource "azurerm_container_group" "main" {
  count               = var.container_count
  name                = "${var.image_name}-aci-${count.index}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  ip_address_type     = "Public"
  dns_name_label      = "${var.image_name}-${count.index}-${random_string.dns_suffix.result}"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.main.id]

  container {
    name   = var.image_name
    image  = "${data.azurerm_container_registry.main.login_server}/${var.image_name}:latest"
    cpu    = var.cpu_cores
    memory = var.memory_gb

    ports {
      port     = var.container_port
      protocol = "TCP"
    }
  }

  image_registry_credential {
    server   = data.azurerm_container_registry.main.login_server
    username = data.azurerm_container_registry.main.admin_username
    password = data.azurerm_container_registry.main.admin_password
  }
}

# Random string for DNS names
resource "random_string" "dns_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Application Gateway for load balancing
resource "azurerm_subnet" "gateway" {
  name                 = "${var.image_name}-gateway-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_public_ip" "gateway" {
  name                = "${var.image_name}-gateway-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_application_gateway" "main" {
  name                = "${var.image_name}-appgw"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 2
  }

  gateway_ip_configuration {
    name      = "gateway-ip-config"
    subnet_id = azurerm_subnet.gateway.id
  }

  frontend_port {
    name = "frontend-port"
    port = 80
  }

  frontend_ip_configuration {
    name                 = "frontend-ip-config"
    public_ip_address_id = azurerm_public_ip.gateway.id
  }

  backend_address_pool {
    name = "backend-pool"
    fqdns = [for i in range(var.container_count) : azurerm_container_group.main[i].fqdn]
  }

  backend_http_settings {
    name                  = "backend-http-settings"
    cookie_based_affinity = "Disabled"
    path                  = ""
    port                  = var.container_port
    protocol              = "Http"
    request_timeout       = 60
  }

  http_listener {
    name                           = "http-listener"
    frontend_ip_configuration_name = "frontend-ip-config"
    frontend_port_name             = "frontend-port"
    protocol                       = "Http"
  }

  request_routing_rule {
    name                       = "routing-rule"
    rule_type                  = "Basic"
    http_listener_name         = "http-listener"
    backend_address_pool_name  = "backend-pool"
    backend_http_settings_name = "backend-http-settings"
    priority                   = 1
  }
}

# Output
output "load_balancer_url" {
  value = "http://${azurerm_public_ip.gateway.ip_address}"
}

output "container_urls" {
  value = [for cg in azurerm_container_group.main : "http://${cg.fqdn}:${var.container_port}"]
}''')

def cleanup_terraform_and_acr(username, terraform_dir, image_name, azure_region="eastus"):
    """Cleanup Azure resources"""
    print(f"Starting destruction of Azure deployment in tmux session: {username}")
    print("10 sec timer start")
    time.sleep(10)
    
    # Create new tmux session with Azure environment for cleanup
    if not _create_tmux_session_with_azure(username):
        return {"status": "error", "message": "Failed to create tmux session with Azure environment for cleanup"}
    
    # Create temp output file for tracking progress
    output_file = tempfile.mktemp()
    
    # Step 1: Ensure terraform.tfvars exists with correct values
    tfvars_path = os.path.join(terraform_dir, 'terraform.tfvars')
    if not os.path.exists(tfvars_path):
        # Create terraform.tfvars file if it doesn't exist
        with open(tfvars_path, 'w') as f:
            f.write(f'''azure_region = "{azure_region}"
image_name = "{image_name}"
container_port = 8080
''')
        print("Created terraform.tfvars file for destroy operation")
    
    # Step 2: Destroy Terraform resources
    print("Destroying Terraform resources...")
    print(terraform_dir)
    
    terraform_destroy_cmd = f"""cd {terraform_dir} && \
    echo "Starting Terraform destroy process..." && \
    terraform destroy -auto-approve && \
    echo "TERRAFORM_DESTROY_COMPLETE" > {output_file}
    """
    
    _run_in_tmux(username, terraform_destroy_cmd)
    
    max_wait_time = 1200  # 20 minutes for Azure
    start_time = time.time()
    terraform_destroyed = False
    
    while time.time() - start_time < max_wait_time:
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                content = f.read()
                if 'TERRAFORM_DESTROY_COMPLETE' in content:
                    terraform_destroyed = True
                    print("Terraform resources successfully destroyed.")
                    break
        time.sleep(5)
    
    if not terraform_destroyed:
        return {"status": "error", "message": "Terraform destroy timed out or failed"}
    
    # Step 3: Clean up remaining resources (resource group will contain any remaining resources)
    print(f"Cleaning up resource group: {image_name}-rg...")
    
    delete_rg_cmd = f"""
    echo "Deleting resource group: {image_name}-rg..." && \
    az group delete --name {image_name}-rg --yes --no-wait && \
    echo "RESOURCE_GROUP_DELETE_INITIATED" > {output_file}
    """
    
    _run_in_tmux(username, delete_rg_cmd)
    
    # Wait for resource group deletion to initiate
    rg_start_time = time.time()
    rg_deleted = False
    
    while time.time() - rg_start_time < 60:  # 1 minute timeout for initiation
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                content = f.read()
                if 'RESOURCE_GROUP_DELETE_INITIATED' in content:
                    rg_deleted = True
                    print("Resource group deletion initiated.")
                    break
        time.sleep(2)
    
    if rg_deleted:
        # Clean up terraform.tfvars file after successful destroy
        if os.path.exists(tfvars_path):
            os.remove(tfvars_path)
            
        mongo.db.users.update_one(
            { "username": username },  
            {
                "$set": {
                    f"projects.{image_name}.exposed_port": "",
                    f"projects.{image_name}.endpoint_url": ""
                }
            }
        )
        change_dir = '''cd ../../../../'''
        _run_in_tmux(username, change_dir)
        return {
            "status": "success",
            "message": "All resources successfully destroyed",
            "details": {
                "terraform_destroyed": True,
                "resource_group_deleted": True
            }
        }
    else:
        return {
            "status": "partial_success",
            "message": "Terraform resources destroyed, but resource group deletion failed or timed out",
            "details": {
                "terraform_destroyed": True,
                "resource_group_deleted": False
            }
        }