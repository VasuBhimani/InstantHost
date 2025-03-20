from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from git import Repo
import os
from flask import jsonify
from flask import request




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
                    dockerfile_path = find_dockerfile(repo_path)
                    if dockerfile_path:
                        flash(f"Dockerfile found at: {dockerfile_path}", "success")
                        print(f"Dockerfile found at: {dockerfile_path}")
                        return redirect(url_for("flask_v1_bp.flask_v1") + f"?dockerfile_path={dockerfile_path}&repo_name={repo_name}")
                    else:
                        flash("No Dockerfile found in the repository.", "info")
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
    Returns the path of the Dockerfile if found, otherwise returns None.
    """
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.lower() == 'dockerfile':  # Check for both 'Dockerfile' and 'dockerfile'
                return os.path.join(root, file)
    return None
