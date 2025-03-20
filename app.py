from flask import Flask
import mysql.connector  # Using mysql-connector-python
from config import Config  # For MySQL config

# No need to initialize MySQL like before
# mysql = MySQL()    # REMOVE THIS LINE

# Create a connection function for MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Load config

    # Register Blueprints (Routes)
    from routes.auth_routes import auth_bp
    from routes.folder_routes import folder_bp
    from routes.docker_routes import docker_bp
    from routes.flask_v1_route import flask_v1_bp
    from routes.repo_routes_v1 import repo_bp_v1

    app.register_blueprint(auth_bp)
    app.register_blueprint(folder_bp)
    app.register_blueprint(docker_bp)
    app.register_blueprint(flask_v1_bp)
    app.register_blueprint(repo_bp_v1)

    return app
