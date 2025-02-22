
import boto3
import json
from flask import session  # Import session to access stored variables

def aws_secrets_store(secret_name, username, password):
    client = boto3.client('secretsmanager', region_name='ap-south-1')
    
    try:
        # Get the session variable (Assuming it's already stored)
        # session_variable = session.get("user")  # Change "user_role" if needed
        session_variable = "vasu"

        if not session_variable:
            return "Error: Session variable not found!"

        # Try to get the existing secret
        try:
            existing_secret = client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(existing_secret['SecretString'])  
        except client.exceptions.ResourceNotFoundException:
            # If secret doesn't exist, create an empty dictionary
            secret_data = {}

        # Store credentials using session variable value
        secret_data[f"{session_variable}-username"] = username
        secret_data[f"{session_variable}-password"] = password

        # Store the updated secret (use update_secret instead of put_secret_value)
        client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(secret_data)
        )
        
        return f"Credentials stored successfully for session {session_variable}!"

    except client.exceptions.ResourceNotFoundException:
        # If secret doesn't exist, create it first
        client.create_secret(
            Name=secret_name,
            SecretString=json.dumps({
                f"{session_variable}-username": username,
                f"{session_variable}-password": password
            })
        )
        return f"New secret created and credentials stored for session {session_variable}!"

    except Exception as e:
        return f"Error: {e}"


# 
print(aws_secrets_store("InstantHost", "john_doerrrr", "myp@ssword123"))


def aws_secrets_get(secret_name, username):
    client = boto3.client('secretsmanager', region_name='ap-south-1')  
    
    try:
        # Retrieve the secret
        response = client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])  # Convert JSON string to dict
        
        # Get the password for the given username
        return secret_data.get(username, "User not found!")  # Return password or error message

    except client.exceptions.ResourceNotFoundException:
        return "Secret not found!"
    except Exception as e:
        return f"Error: {e}"

# print(aws_secrets_get("InstantHost", "john_doe"))  # Output: myp@ssword123