import time
from flask import Blueprint, jsonify, render_template, session, redirect, url_for, flash
from utils.flaskonly_aws import flaskonly_aws
from utils.flaskonly_azure import flaskonly_azure

import threading
from flask import request
import os
import logging
from extensions import mongo

flask_v1_bp = Blueprint('flask_v1_bp', __name__)
# Disable logging for Werkzeug to suppress all logs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NoStatusLogFilter(logging.Filter):
    def filter(self, record):
        return "/check_task_status1" not in record.getMessage()

# Apply the filter to the werkzeug logger
log = logging.getLogger("werkzeug")
log.addFilter(NoStatusLogFilter())

task_done = False
task_lock = threading.Lock()

@flask_v1_bp.route('/flask_v1', methods=['GET'])
def flask_v1():
    print("flask_v1 funcition working------------------------")
    """
    Simply display the loading.html page when accessed
    """
    # Security check - make sure user is logged in
    if 'user' not in session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('auth.login'))
    
    dockerfile_path = request.args.get('dockerfile_path')
    image_name = request.args.get('repo_name')
    exposed_port = request.args.get('exposed_port')
    cloud = request.args.get('cloud')
    
    if cloud == "aws":
        image_name = image_name + "-aws"
    elif cloud == "azure":
        image_name = image_name + "-azure"
    elif cloud == "gcp":
        image_name = image_name + "-gcp"
        
    # image_name = session.get('project_name')
    session_name = session.get("user")
    terraform_dir = os.path.join( "download" , session_name, image_name, "terraform")
    if not os.path.exists(terraform_dir):
        os.makedirs(terraform_dir)
        print(f"Directory '{terraform_dir}' created.")
    else:
        print(f"Directory '{terraform_dir}' already exists.")
    port_no = exposed_port
    
    if cloud == "aws":
        aws_region = "us-east-1"
        print("Python project docker file creation started")

        thread = threading.Thread(target=aws_flask, args=(session_name, dockerfile_path, image_name, terraform_dir, port_no, aws_region))
        thread.daemon = True
        thread.start()
        print("threate started")
        print("last------------------------------------------------------aws")
        return render_template("loading.html")
    elif cloud == "azure":
        azure_region = "eastus"
        print("Python project docker file creation started")
        thread = threading.Thread(target=azure_flask, args=(session_name, dockerfile_path, image_name, terraform_dir, port_no, azure_region))
        thread.daemon = True
        thread.start()
        print("threate started")
        print("last------------------------------------------------------azure")
        return render_template("loading.html")


def aws_flask(session_name, dockerfile_path, image_name, terraform_dir,port_no, aws_region):
    global task_done
    result = flaskonly_aws(session_name, dockerfile_path, image_name, terraform_dir, port_no, aws_region)
    print("Python project docker file creation started-----------------------------------------------")
    print(result)
    print("Python project docker file creation completed-----------------------------------------------")
    endpoint_url = result.get("endpoint_url")
    print(endpoint_url)
    username = session_name
    repo_name = image_name
    mongo.db.users.update_one(
        { "username": username },  # Find the user by username
        {
            "$set": {
                f"projects.{repo_name}.endpoint_url": endpoint_url
            }
        }
    )
    with task_lock:
        task_done = True
        print(task_done)
        
def azure_flask(session_name, dockerfile_path, image_name, terraform_dir,port_no, azure_region):
    global task_done
    # image_name = image_name + "_" + session_name + "_" + azure_region
    print(image_name + "-----------------------------------------")
    result = flaskonly_azure(session_name, dockerfile_path, image_name, terraform_dir, port_no, azure_region)
    print("Python project docker file creation started-----------------------------------------------")
    print(result)
    print("Python project docker file creation completed-----------------------------------------------")
    endpoint_url = result.get("endpoint_url")
    print(endpoint_url)
    username = session_name
    repo_name = image_name
    mongo.db.users.update_one(
        { "username": username },  # Find the user by username
        {
            "$set": {
                f"projects.{repo_name}.endpoint_url": endpoint_url
            }
        }
    )
    with task_lock:
        task_done = True
        print(task_done)
        
        


@flask_v1_bp.route('/check_task_status1', methods=['GET'])
def check_task_status1():
    with task_lock:
        done = task_done
    if done:
        return jsonify({'status': 'complete', 'redirect': url_for('folder.folder_disply')})
    else:
        return jsonify({'status': 'pending'})

