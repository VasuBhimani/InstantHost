from flask import Blueprint, render_template, session, redirect, url_for, flash

flask_v1_bp = Blueprint('flask_v1_bp', __name__)

task_done = False
task_lock = threading.Lock()

@flask_v1_bp.route('/flask_v1', methods=['GET'])
def flask_v1():
    """
    Simply display the loading.html page when accessed
    """
    # Security check - make sure user is logged in
    if 'user' not in session:
        flash('Please log in to access this page', 'danger')
        return redirect(url_for('auth.login'))
    
    project_name = session.get('project_name')
    username = session.get("user")
    
    print("Python project docker file creation started")
    thread = threading.Thread(target=testing_for_flask_v1, args=(project_name, username))
    thread.daemon = True
    thread.start()
    return render_template("loading.html")


def testing_for_flask_v1(project_name, username):
     """
    Main endpoint to build Docker image and deploy to AWS
    
    Expected JSON payload:
    {
        "session_name": "tmux-session-name",
        "dockerfile_path": "/path/to/Dockerfile",
        "image_name": "my-app-image",
        "terraform_dir": "/path/to/terraform",
        "aws_region": "us-east-1"
    }
    """
    data = request.json
    logger.info(f"Received request: {data}")
    
    # Extract parameters from request
    session_name = data.get('session_name')
    dockerfile_path = data.get('dockerfile_path')
    image_name = data.get('image_name')
    terraform_dir = data.get('terraform_dir')
    aws_region = data.get('aws_region', 'us-east-1')
    
    # Validate required parameters
    if not all([session_name, dockerfile_path, image_name, terraform_dir]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Create tmux session if it doesn't exist
    if not check_tmux_session(session_name):
        logger.info(f"Creating tmux session: {session_name}")
        create_tmux_session(session_name)
    
    # Build Docker image
    logger.info(f"Building Docker image in session: {session_name}")
    build_result = build_docker_image(session_name, dockerfile_path, image_name)
    
    if build_result['success']:
        # If build was successful, deploy to AWS
        logger.info("Docker build successful. Proceeding with deployment.")
        deploy_result = deploy_to_aws(
            session_name=session_name,
            terraform_dir=terraform_dir,
            image_name=image_name,
            aws_region=aws_region
        )
        
        return jsonify({
            "build": build_result,
            "deploy": deploy_result
        })
    else:
        logger.error(f"Docker build failed: {build_result.get('error')}")
        return jsonify({
            "build": build_result,
            "error": "Docker build failed, deployment aborted"
        }), 500

def deploy_to_aws(session_name, terraform_dir, image_name, aws_region):
    """
    Function to deploy the built Docker image to AWS using Terraform
    """
    logger.info(f"Starting AWS deployment with Terraform from {terraform_dir}")
    
    # Apply Terraform to create infrastructure
    terraform_vars = {
        'image_name': image_name,
        'aws_region': aws_region,
        'project_name': image_name.replace('/', '-').replace(':', '-')
    }
    
    terraform_result = apply_terraform(session_name, terraform_dir, terraform_vars)
    
    if terraform_result['success'] and terraform_result.get('outputs'):
        # Get ECR repository URL from Terraform outputs
        outputs = terraform_result['outputs']
        ecr_repo_url = outputs.get('ecr_repository_url')
        app_url = outputs.get('app_url')
        
        if ecr_repo_url:
            logger.info(f"Pushing Docker image to ECR: {ecr_repo_url}")
            
            # Run the push to ECR script
            script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'push_to_ecr.sh')
            run_in_tmux(session_name, f"bash {script_path} {ecr_repo_url} {image_name} {aws_region}", wait=True)
            
            return {
                "success": True,
                "ecr_repository_url": ecr_repo_url,
                "app_url": app_url,
                "message": "Application successfully deployed"
            }
        else:
            return {
                "success": False,
                "error": "ECR repository URL not found in Terraform outputs"
            }
    else:
        return terraform_result


@docker_bp.route("/status", methods=["GET"])
def status():
    global task_done
    if task_done:
        return redirect(url_for("docker_bp.test"))
    return "", 204

@docker_bp.route("/test")
def test():
    return render_template("home.html")