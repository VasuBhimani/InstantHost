import logging
import threading
from time import sleep
import time
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session
import os
import shutil
import stat
from extensions import mongo
from utils.flaskonly_v1 import cleanup_terraform_and_ecr

folder_bp = Blueprint("folder", __name__)


class NoStatusLogFilter(logging.Filter):
    def filter(self, record):
        return "/check_task_status" not in record.getMessage()

# Apply the filter to the werkzeug logger
log = logging.getLogger("werkzeug")
log.addFilter(NoStatusLogFilter())

task_done = False
task_lock = threading.Lock()



@folder_bp.route("/edit_folder/<folder_name>", methods=["GET"])
def edit_folder(folder_name):
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    print("edit folder------------", folder_name)
    return render_template("projectinfo.html", folder_name=folder_name)
    # session['project_name'] = folder_name
    # user_folder = os.path.join("download", session["user"], folder_name, f"{folder_name}_structure.txt")
    
    # try:
    #     with open(user_folder, 'r') as file:
    #         first_line = file.readline().strip()
    #         print(first_line)
    #     if first_line == "Project Type: PYTHON":
    #         return render_template("flask_input.html", folder_name=folder_name)
    #     elif first_line == "Project Type: MERN":
    #         return render_template("mern_input.html", folder_name=folder_name)
    #     else:
    #         return "Unknown Project Type", 400
    
    # except FileNotFoundError:
    #     return "File not found", 404
    # except Exception as e:
    #     return f"An error occurred: {e}", 500
    
    # return render_template("projectinfo.html", folder_name=folder_name)


@folder_bp.route("/folder_disply")
def folder_disply():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    global task_done  # Add this line
    with task_lock:
        task_done = False

    user_folder = os.path.join("download", session["user"])
    os.makedirs(user_folder, exist_ok=True)
    folders = [f for f in os.listdir(user_folder) if os.path.isdir(os.path.join(user_folder, f))]

    # Fetch user data from MongoDB
    user_data = mongo.db.users.find_one({"username": session["user"]})
    folder_info = []
    for folder in folders:
        project_details = user_data['projects'].get(folder, {})
        endpoint_url = project_details.get('endpoint_url')
        folder_info.append({
            'name': folder,
            'endpoint_url': endpoint_url
        })
    return render_template("folders.html", folders=folder_info)

@folder_bp.route("/destroy/<folder_name>", methods=["GET"])
def destroy(folder_name):
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    # print("destroy folder------------", folder_name)
    session_name = session.get("user")
    image_name = folder_name
    terraform_dir = os.path.join( "download" , session_name, image_name, "terraform")
    # print("destroy folder------------", terraform_dir)
    thread = threading.Thread(target=cleanup_terraform_and_ecr_def, args=(session_name, terraform_dir, image_name))
    thread.daemon = True
    thread.start()
    # cleanup_terraform_and_ecr(session_name, terraform_dir, image_name, aws_region="us-east-1")
    return render_template("loading2.html", folder_name=folder_name)

def cleanup_terraform_and_ecr_def(session_name, terraform_dir, image_name):
    print("cleanup_terraform_and_ecr_def start")
    # print("destroy folder------------", terraform_dir)
    result = cleanup_terraform_and_ecr(session_name, terraform_dir, image_name, aws_region="us-east-1")
    # time.sleep(5)
    print(result)
    with task_lock:
        global task_done 
        task_done = True
        print(task_done , "from cleanup_terraform_and_ecr route ")

@folder_bp.route('/check_task_status', methods=['GET'])
def check_task_status():
    with task_lock:
        done = task_done
    if done:
        return jsonify({'status': 'complete', 'redirect': url_for('folder.folder_disply')})
    else:
        return jsonify({'status': 'pending'})

@folder_bp.route("/delete/<folder_name>", methods=["POST"])
def delete_folder(folder_name):
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    user_folder = os.path.join("download", session["user"], folder_name)

    if os.path.exists(user_folder):
        try:
            # Change permissions recursively to ensure we can delete everything
            for root, dirs, files in os.walk(user_folder, topdown=False):
                for name in dirs + files:
                    filepath = os.path.join(root, name)
                    os.chmod(filepath, stat.S_IWRITE)  # Make sure we can write/modify
            shutil.rmtree(user_folder)  # Force delete the folder and its contents
            flash(f"Folder '{folder_name}' deleted successfully.", "success")
        except PermissionError:
            flash(f"Permission error deleting folder: {folder_name}", "danger")
        except Exception as e:
            flash(f"Error deleting folder: {e}", "danger")
    else:
        flash(f"Folder '{folder_name}' does not exist.", "warning")

    return redirect(url_for("folder.folder_disply")) 


