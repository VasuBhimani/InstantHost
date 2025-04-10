import time
from flask import Blueprint, jsonify, render_template, session, redirect, url_for, flash
from utils.flaskonly_v1 import fun_flaskonly_v1
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
    
    # image_name = session.get('project_name')
    session_name = session.get("user")
    terraform_dir = os.path.join( "download" , session_name, image_name, "terraform")
    if not os.path.exists(terraform_dir):
        os.makedirs(terraform_dir)
        print(f"Directory '{terraform_dir}' created.")
    else:
        print(f"Directory '{terraform_dir}' already exists.")
        
    aws_region = "us-east-1"
    port_no = exposed_port
    # port_no=8123
    
    print("Python project docker file creation started")
    thread = threading.Thread(target=testing_for_flask_v1, args=(session_name, dockerfile_path, image_name, terraform_dir, port_no, aws_region))
    thread.daemon = True
    thread.start()
    print("threate started")
    return render_template("loading.html")


def testing_for_flask_v1(session_name, dockerfile_path, image_name, terraform_dir,port_no, aws_region):
    global task_done
    result = fun_flaskonly_v1(session_name, dockerfile_path, image_name, terraform_dir, port_no, aws_region)
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

