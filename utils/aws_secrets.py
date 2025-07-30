
import boto3
import json
from flask import session  # Import session to access stored variables
import subprocess
import os

def create_session(username,aws_access_key,aws_secret_key):
    region = "us-east-1"
    cloud_name = "aws"
    
    if cloud_name == "aws":
        save_file_aws(username,aws_access_key,aws_secret_key,region,cloud_name)
    elif cloud_name == "azure":
        save_file_azure(username,aws_access_key,aws_secret_key,region,cloud_name)
    elif cloud_name == "gcp":
        save_file_gcp(username,aws_access_key,aws_secret_key,region,cloud_name)
    else:
        print("no cloud in list")

    session_name = username  # Use the username as the tmux session name
    # Create a new tmux session in detached mode
    tmux_cmd = f"tmux new-session -d -s {session_name}"
    
    # Command to configure AWS CLI inside the tmux session
    aws_config_cmd = (
        f"aws configure set aws_access_key_id {aws_access_key} && "
        f"aws configure set aws_secret_access_key {aws_secret_key} && "
        f"aws configure set region us-east-1 && "  # Change region if needed
        f"aws configure list"
    )

    # Send the AWS configuration command to the tmux session
    tmux_send_cmd = f'tmux send-keys -t {session_name} "{aws_config_cmd}" Enter'

    try:
        # Step 1: Create a tmux session
        subprocess.run(tmux_cmd, shell=True, check=True)
        
        # Step 2: Run AWS CLI configure command inside the session
        subprocess.run(tmux_send_cmd, shell=True, check=True)

        return True
    
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"
    
    
def save_file_aws(username, aws_access_key, aws_secret_key, region, cloud_name):
    # Directory path for user
    file_dir = f"download/{username}/"
    os.makedirs(file_dir, exist_ok=True)

    # ✅ Final path = directory + cloud_name (keeps your filename)
    file_path = os.path.join(file_dir, cloud_name)

    content = f"""export AWS_ACCESS_KEY_ID="{aws_access_key}"
export AWS_SECRET_ACCESS_KEY="{aws_secret_key}"
export AWS_DEFAULT_REGION="{region}"
"""

    with open(file_path, "w") as f:
        f.write(content)

    return f"Credentials saved to {file_path}"

def save_file_azure(username, aws_access_key, aws_secret_key, region, cloud_name):
    # Directory path for user
    file_dir = f"download/{username}/"
    os.makedirs(file_dir, exist_ok=True)

    # ✅ Final path = directory + cloud_name (keeps your filename)
    file_path = os.path.join(file_dir, cloud_name)

    content = f"""export AZURE_CLIENT_ID="{your_client_id}"
export AZURE_SECRET="{your_client_secret}"
export AZURE_TENANT_ID="{your_tenant_id}"
export AZURE_SUBSCRIPTION_ID="{your_subscription_id}"
"""

    with open(file_path, "w") as f:
        f.write(content)

    return f"Credentials saved to {file_path}"

def save_file_gcp(username, aws_access_key, aws_secret_key, region, cloud_name):
    # Directory path for user
    file_dir = f"download/{username}/"
    os.makedirs(file_dir, exist_ok=True)

    # ✅ Final path = directory + cloud_name (keeps your filename)
    file_path = os.path.join(file_dir, cloud_name)

    content = f"""export AWS_ACCESS_KEY_ID="{aws_access_key}"
export AWS_SECRET_ACCESS_KEY="{aws_secret_key}"
export AWS_DEFAULT_REGION="{region}"
"""

    with open(file_path, "w") as f:
        f.write(content)

    return f"Credentials saved to {file_path}"