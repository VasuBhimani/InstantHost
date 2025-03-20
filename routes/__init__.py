from flask import Blueprint

# Import blueprints from different route files
from .auth_routes import auth_bp
from .repo_routes import repo_bp
from .folder_routes import folder_bp
from .docker_routes import docker_bp
from .flask_v1_route import flask_v1_bp
from .repo_routes_v1 import repo_bp_v1

