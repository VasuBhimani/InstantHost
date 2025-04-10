from flask import Flask
from extensions import mongo
from urllib.parse import quote_plus

# Encode password to handle special characters
username = "InstantHost"
password = "admin"  # Correct password
encoded_password = quote_plus(password)

# Correct MongoDB URI with target database
# uri = f"mongodb+srv://{username}:{encoded_password}@instanthost.oasev.mongodb.net/InstantHostDB?retryWrites=true&w=majority"
uri = "mongodb://10.255.255.254:27017/InstantHostDB"
def create_app():
    app = Flask(__name__)

    # Add a secret key for session management
    app.secret_key = "your-super-secret-key"  # Change this to something secure

    # MongoDB configuration
    app.config["MONGO_URI"] = uri
    mongo.init_app(app)  # Initialize MongoDB with the app

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


