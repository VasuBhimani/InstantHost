from flask import jsonify
from flask import Blueprint, render_template, request, session, flash, redirect, url_for
import os
import threading
from utils.docker_utils import docker_file_creation, build_docker_image, docker_file_recreation
import time

docker_bp = Blueprint('docker_bp', __name__)

task_done = False
task_lock = threading.Lock()

@docker_bp.route("/mern_submit", methods=["GET", "POST"])
def mern_submit():
    project_name = session.get('project_name')
    username = session.get("user")
    
    if not project_name or not username:
        flash("Project or user not found!", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        frontend_port = request.form.get("frontend_port")
        frontend_command = request.form.get("frontend_command")
        backend_port = request.form.get("backend_port")
        backend_command = request.form.get("backend_command")
        selected_file_url_1 = request.form.get("selected_file_url_1")
        selected_file_url_2 = request.form.get("selected_file_url_2")

        folder_path = os.path.join("download", username, project_name)
        file_path = os.path.join(folder_path, "dockerfile_info.txt")

        with open(file_path, "w") as file:
            file.write(f"Frontend Entry File: {selected_file_url_1}\n")
            file.write(f"Frontend Port: {frontend_port}\n")
            file.write(f"Frontend Command: {frontend_command}\n")
            file.write(f"Backend Entry File: {selected_file_url_2}\n")
            file.write(f"Backend Port: {backend_port}\n")
            file.write(f"Backend Command: {backend_command}\n")
            
            
        print("MERN project docker file creation started")
        thread = threading.Thread(target=testing_for_node, args=(project_name, username))
        thread.start()
        return render_template("loading.html")


@docker_bp.route("/flask_submit", methods=["GET", "POST"])
def flask_submit():
    project_name = session.get('project_name')
    username = session.get("user")
    
    if not project_name or not username:
        flash("Project or user not found!", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        flask_port = request.form.get("flask_port")
        flask_command = request.form.get("flask_command")
        selected_file_url_1 = request.form.get("selected_file_url_1")
        env_var_keys = request.form.getlist("env_var_key[]")
        env_var_values = request.form.getlist("env_var_value[]")
        env_vars = dict(zip(env_var_keys, env_var_values)) 


        folder_path = os.path.join("download", username, project_name)
        file_path = os.path.join(folder_path, "dockerfile_info.txt")

        with open(file_path, "w") as file:
            file.write(f"Flask Entry File: {selected_file_url_1}\n")
            file.write(f"Flask Port: {flask_port}\n")
            file.write(f"Flask run Command: {flask_command}\n")
            file.write(f"Environment Variables: {env_vars}\n")


        print("Python project docker file creation started")
        thread = threading.Thread(target=testing_for_python, args=(project_name, username))
        thread.start()
        return render_template("loading.html")
        
        
        



extra_text = "Create a production-ready Dockerfile for this project structure using best practices. Do not add markdown formatting, backticks, or explanations—just return the Dockerfile content as plain text."

def testing_for_python(project_name, username):
    global task_done
    folder_path = os.path.join("download", username, project_name, project_name)
    dockerfile_path = os.path.join(folder_path, "Dockerfile")
    
    with open(dockerfile_path, 'w', encoding="utf-8") as dockerfile:
        dockerfile.write("# Your Dockerfile content goes here")
    
    print("docker file creation started")
    docker_file_creation(username, project_name, extra_text) 

    while True:
        print("while loop performing---------------------")
        success = build_docker_image(username, project_name)
        if success:
            break
        else:
            print("Retrying in 5 seconds....................")
            docker_file_recreation(username, project_name)
            # time.sleep(1) 
    
    print("Testing function completed!")
    
    
    download_tf_files(username,project_name)
    script_dir = os.path.join("script", "ECR")
    
    if not os.path.isdir(script_dir):
        raise FileNotFoundError(f"Script directory not found: {script_dir}")
    
    # Create a new tmux session and detach
    subprocess.run(f"tmux new-session -d -s {username} -c {script_dir}", shell=True)

    commands = [
        "terraform init ",
        "terraform plan",
        "terraform apply -var=\"ecr_repository_name=my-new-repo\" -auto-approve"
    ]

    # Send each command to the tmux session
    for cmd in commands:
        subprocess.run(f"tmux send-keys -t {username} '{cmd}' C-m", shell=True)

    print(f"Terraform commands are running in tmux session: {username}")
    print("Attach using: tmux attach-session -t terraform_session")
    
    with task_lock:
        task_done = True
        
@docker_bp.route("/status", methods=["GET"])
def status():
    global task_done
    if task_done:
        return redirect(url_for("docker_bp.test"))
    return "", 204

@docker_bp.route("/test")
def test():
    return render_template("home.html")


#--------------------------------------------------unnecessary code--------------------------------------------

# @docker_bp.route("/submit", methods=["GET", "POST"])
# def submit():
#     print("hellllllll")
#     project_name = session.get('project_name')
#     username = session.get("user")
    
#     if not project_name or not username:
#         flash("Project or user not found!", "danger")
#         return redirect(url_for("auth.login"))

#     if request.method == "POST":
#         build_commands = request.form["build_commands"]
#         ports = request.form["ports"]
#         env_var_keys = request.form.getlist("env_var_key[]")
#         env_var_values = request.form.getlist("env_var_value[]")
#         env_vars = dict(zip(env_var_keys, env_var_values)) 

#         folder_path = os.path.join("download", username, project_name)
#         file_path = os.path.join(folder_path, "dockerfile_info.txt")

#         with open(file_path, "w") as file:
#             file.write(f"Build Commands: {build_commands}\n")
#             file.write(f"Ports: {ports}\n")
#             file.write(f"Environment Variables: {env_vars}\n")
        
        
#         if(session.get("project_type") == "Python"):
#             # Start the Dockerfile creation and image build process in a separate thread
#             print("Python project docker file creation started")
#             thread = threading.Thread(target=testing_for_python, args=(project_name, username))
#             thread.start()
            
#             return render_template("loading.html")
        
        
#         if(session.get("project_type") == "Node"):
#             # Start the Dockerfile creation and image build process in a separate thread
#             print("Node project docker file creation started")
#             thread = threading.Thread(target=testing_for_node, args=(project_name, username))
#             thread.start()
            
#             return render_template("loading.html")
        
#         # thread = threading.Thread(target=testing_for_mern, args=(project_name, username), daemon=True)
#         # thread.start()
        
#         return render_template("loading.html")

#     return render_template("projectinfo.html")