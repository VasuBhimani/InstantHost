from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from git import Repo
import os
from utils.tree_creation import save_file_tree
from flask import jsonify


repo_bp = Blueprint("repo", __name__)


@repo_bp.route("/url_form", methods=["GET", "POST"])
def url_form():
    # if "user" in session:
    #     user = session["user"]
    global repo_name
    username = session["user"] 
    if request.method == "POST":
        github_url = request.form.get("github_url")
        # project_language = request.form.get("project_language")
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
                    
                    if project_type == "PYTHON":
                        return render_template("mern_input.html", project_type=project_type)
                    if project_type == "MERN":
                        return render_template("mern_input.html", project_type=project_type)
                    else :
                        return render_template("projectinfo.html", project_type=project_type)
                    
                else:
                    flash(f"Repository '{repo_name}' already exists in the download folder.", "warning")
            except Exception as e:
                flash(f"Error cloning repository: {e}", "danger")
        else:
            flash("Please provide a valid GitHub URL.", "warning")
        return redirect(url_for("repo.url_form"))
    
    return render_template("index.html", user=session["user"])


BASE_DIR = r"C:\Users\vasu\OneDrive\Desktop\New folder (4)"  # Change this to your directory
ROOT_NAME = os.path.basename(os.path.normpath(BASE_DIR))  # Get folder name from path



def get_directory_structure(rootdir):
    """Recursively get directory structure with relative file paths starting with the root folder name."""
    file_tree = {"name": ROOT_NAME, "base_path": rootdir, "files": [], "folders": {}}

    for root, dirs, files in os.walk(rootdir):
        path = root.replace(rootdir, "").strip(os.sep).split(os.sep)
        current_level = file_tree

        for part in path:
            if part:
                current_level = current_level["folders"].setdefault(part, {
                    "name": part,
                    "files": [],
                    "folders": {}
                })

        # Instead of storing full absolute paths, compute the relative path from BASE_DIR and prepend ROOT_NAME
        current_level["files"] = [
            os.path.join(ROOT_NAME, os.path.relpath(os.path.join(root, file), BASE_DIR)).replace("\\", "/")
            for file in files
        ]

    return file_tree

# Example Flask route
@repo_bp.route('/files')
def list_files():
    """API to send file structure as JSON with relative file paths"""
    return jsonify(get_directory_structure(BASE_DIR))