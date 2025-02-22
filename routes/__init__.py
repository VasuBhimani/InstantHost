from flask import Blueprint

# Import blueprints from different route files
from .auth_routes import auth_bp
from .repo_routes import repo_bp
from .folder_routes import folder_bp
from .docker_routes import docker_bp


