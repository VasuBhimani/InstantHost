from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from git import Repo
import os
from utils.tree_creation import save_file_tree

repo_bp = Blueprint("repo", __name__)


@repo_bp.route("/url_form", methods=["GET", "POST"])
def url_form():
    # if "user" in session:
    #     user = session["user"]
    global repo_name
    username = session["user"] 
    if request.method == "POST":
        github_url = request.form.get("github_url")
        if github_url:
            try:
                repo_name = github_url.rstrip('/').split('/')[-1].replace('.git', '')
                # repo_path = os.path.join(DOWNLOAD_FOLDER, repo_name)

                folder_path = os.path.join("download",username, repo_name)
                os.makedirs(folder_path, exist_ok=True)
                repo_path = os.path.join(folder_path, repo_name)

                if not os.path.exists(repo_path):
                    # Clone the repository
                    Repo.clone_from(github_url, repo_path)
                    flash(f"Repository '{repo_name}' cloned successfully!", "success")
                    
                    # Save file structure
                    project_type = save_file_tree(repo_name, repo_path, username)
                    print("project_type",project_type)
                    session["project_type"] = project_type
                    
                    flash(f"File structure of '{repo_name}' saved successfully!", "success")
                    
                    return render_template("projectinfo.html", project_name=project_name)
                else:
                    flash(f"Repository '{repo_name}' already exists in the download folder.", "warning")
            except Exception as e:
                flash(f"Error cloning repository: {e}", "danger")
        else:
            flash("Please provide a valid GitHub URL.", "warning")
        return redirect(url_for("repo.url_form"))
    
    return render_template("index.html", user=session["user"])