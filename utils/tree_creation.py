from flask import Flask, render_template, request, redirect, url_for, flash
import os
from git import Repo
import requests
import json

repo_name = None
# Ensure the download directory exists
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'download')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Function to generate the file tree structure
def generate_tree(root_path, level=0):
    tree_str = ""
    items = sorted(os.listdir(root_path))
    for item in items:
        item_path = os.path.join(root_path, item)
        if item == '.git':
            continue
        indent = "    " * level
        if os.path.isdir(item_path):
            tree_str += f"{indent}{item}/\n"
            tree_str += generate_tree(item_path, level + 1)
        else:
            tree_str += f"{indent}{item}\n"
    return tree_str

# Function to check if the project is Python or MERN based on file tree
def check_project_type(repo_path):
    if os.path.exists(os.path.join(repo_path, 'requirements.txt')):
        return "Python"
    elif os.path.exists(os.path.join(repo_path, 'package.json')):
        return "Node"
    else:
        return "Python (Flask)"

# Function to save the file tree structure and project type
def save_file_tree(repo_name, repo_path, username):
    # Generate the tree structure
    tree_str = generate_tree(repo_path)
    # Check project type (Python or MERN)
    project_type = check_project_type(repo_path)

    # Save the file tree and project type to a file
    tree_file_path = os.path.join('download', username, repo_name, f"{repo_name}_structure.txt")
    with open(tree_file_path, 'w') as f:
        f.write(f"Project Type: {project_type}\n")
        f.write(tree_str)
        print(project_type)
    return project_type