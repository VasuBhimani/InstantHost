import boto3
import os


def download_tf_files(user_name,project_name):
    # AWS S3 Configurations
    BUCKET_NAME = "instanhost-tffile"
    FOLDER_NAME = "scripts"  # The folder to download (keeps the same name locally)
    LOCAL_DOWNLOAD_PATH = os.path.join("download", user_name,project_name )  # Save in the current directory with the same name
    # LOCAL_DOWNLOAD_PATH = "./testfolder"  # Save in the current directory with the same name

    # Initialize S3 client
    s3 = boto3.client("s3")

    # Ensure the main folder exists (same as S3)
    local_script_path = os.path.join(LOCAL_DOWNLOAD_PATH, FOLDER_NAME)
    os.makedirs(local_script_path, exist_ok=True)

    # List all objects inside the 'script' folder
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=FOLDER_NAME + "/")

    if "Contents" in response:
        for obj in response["Contents"]:
            file_key = obj["Key"]

            if file_key.endswith("/"):  # Ignore folder paths
                continue

            # Keep the same folder structure from S3
            local_file_path = os.path.join(LOCAL_DOWNLOAD_PATH, file_key)

            # Create necessary directories
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            # Download the file
            s3.download_file(BUCKET_NAME, file_key, local_file_path)
            print(f"Downloaded: {file_key} -> {local_file_path}")

    else:
        print("No files found in the specified folder.")