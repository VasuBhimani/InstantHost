import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from git import Repo
import os
from flask import jsonify
from flask import request
from extensions import mongo

repo_bp_v1 = Blueprint("repo_v1", __name__)


@repo_bp_v1.route("/url_form", methods=["GET", "POST"])
def url_form():
    global repo_name
    username = session["user"] 
    if request.method == "POST":
        github_url = request.form.get("github_url")
        if github_url:
            try:
                repo_name = github_url.rstrip('/').split('/')[-1].replace('.git', '')
                folder_path = os.path.join("download", username, repo_name)
                os.makedirs(folder_path, exist_ok=True)
                repo_path = os.path.join(folder_path, repo_name)

                if not os.path.exists(repo_path):
                    # Clone the repository
                    Repo.clone_from(github_url, repo_path)
                    flash(f"Repository '{repo_name}' cloned successfully!", "success")
                    
                    # Scan for Dockerfile or dockerfile
                    dockerfile_path, exposed_port = find_dockerfile(repo_path)
                    if dockerfile_path:
                        if exposed_port:
                            flash(f"Dockerfile found at: {dockerfile_path} with port {exposed_port} exposed.", "success")
                            print(f"Dockerfile found at: {dockerfile_path} with port {exposed_port} exposed.")
                            mongo.db.users.update_one(
                                                    { "username": username },  # Find the user by username
                                                    { 
                                                        "$set": { 
                                                            f"projects.{repo_name}": {  
                                                                "dockerfile_path": dockerfile_path,
                                                                "exposed_port": exposed_port
                                                            }
                                                        }
                                                    }
                                                )
                            return redirect(url_for("flask_v1_bp.flask_v1") + f"?dockerfile_path={dockerfile_path}&repo_name={repo_name}&exposed_port={exposed_port}")
                        else:
                            flash(f"Dockerfile found at: {dockerfile_path}, but no port is exposed.", "warning")
                            print(f"Dockerfile found at: {dockerfile_path}, but no port is exposed.")
                    else:
                        flash("Dockerfile not found.", "danger")
                        print("Dockerfile not found.")
                else:
                    flash(f"Repository '{repo_name}' already exists in the download folder.", "warning")
            except Exception as e:
                flash(f"Error cloning repository: {e}", "danger")
        else:
            flash("Please provide a valid GitHub URL.", "warning")
        return redirect(url_for("repo_v1.url_form"))
    
    return render_template("index.html", user=session["user"])


def find_dockerfile(repo_path):
    """
    Scans the given repository path for Dockerfile or dockerfile.
    Reads the Dockerfile and extracts the port from the EXPOSE instruction.
    Returns the path of the Dockerfile and the exposed port if found, otherwise returns None.
    """
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.lower() == 'dockerfile':  # Check for 'Dockerfile' or 'dockerfile'
                dockerfile_path = os.path.join(root, file)
                
                # Read the Dockerfile and extract the port
                exposed_port = get_exposed_port(dockerfile_path)
                if exposed_port:
                    return dockerfile_path, exposed_port

    return None, None


def get_exposed_port(dockerfile_path):
    """
    Reads the Dockerfile and extracts the first port mentioned in the EXPOSE instruction.
    Ignores commented lines.
    Returns the port if found, otherwise returns None.
    """
    try:
        with open(dockerfile_path, 'r') as f:
            for line in f:
                line = line.strip()

                # Skip commented lines (lines starting with #)
                if line.startswith('#') or not line:
                    continue
                
                # Check if the line starts with 'EXPOSE' (case-insensitive)
                if line.lower().startswith('expose'):
                    # Extract the port number using regex
                    match = re.search(r'expose\s+(\d+)', line, re.IGNORECASE)
                    if match:
                        return int(match.group(1))  # Return the port as an integer
    except Exception as e:
        print(f"Error reading Dockerfile: {e}")
    
    return None


# def find_dockerfile(repo_path):
#     """
#     Scans the given repository path for Dockerfile or dockerfile.
#     Returns the path of the Dockerfile if found, otherwise returns None.
#     """
#     for root, dirs, files in os.walk(repo_path):
#         for file in files:
#             if file.lower() == 'dockerfile':  # Check for both 'Dockerfile' and 'dockerfile'
#                 return os.path.join(root, file)
#     return None
