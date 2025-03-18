from flask import Flask
from flask_mysqldb import MySQL
from config import Config

mysql = MySQL()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mysql.init_app(app)

    # Register Blueprints (Routes)
    from routes.auth_routes import auth_bp
    from routes.repo_routes import repo_bp
    from routes.folder_routes import folder_bp
    from routes.docker_routes import docker_bp
    from routes.flask_v1_route import flask_v1_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(repo_bp)
    app.register_blueprint(folder_bp)
    app.register_blueprint(docker_bp)
    app.register_blueprint(flask_v1_bp)

    return app
