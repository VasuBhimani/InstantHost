from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import os
import shutil
import stat

folder_bp = Blueprint("folder", __name__)


@folder_bp.route("/edit/<folder_name>", methods=["GET"])
def edit_folder(folder_name):
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    session['project_name'] = folder_name
    # Render a new page for editing
    return render_template("projectinfo.html", folder_name=folder_name)

@folder_bp.route("/folder_disply")
def folder_disply():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    user_folder = os.path.join("download", session["user"])
    os.makedirs(user_folder, exist_ok=True)
    folders = [f for f in os.listdir(user_folder) if os.path.isdir(os.path.join(user_folder, f))]
    return render_template("folders.html", folders=folders)



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
