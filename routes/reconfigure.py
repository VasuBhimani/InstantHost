import json
import subprocess
from flask import render_template, request
from flask import Blueprint
from utils.aws_secrets import save_file_aws
from utils.aws_secrets import save_file_azure

reconfigure_bp = Blueprint("reconfigure", __name__)

# Cloud Credentials route
@reconfigure_bp.route('/cloud-credentials',methods=["GET", "POST"])
def cloud_credentials():
    aws_info = check_aws()
    azure_info = check_azure()
    gcp_info = check_gcp()

    return render_template(
        "cloud_acc_info.html",
        aws_info=aws_info,
        azure_info=azure_info,
        gcp_info=gcp_info
    )

# Alternative info route (if you prefer /info URL)
@reconfigure_bp.route('/aws_save_data',methods=["GET","POST"])
def aws_save_data():
    if request.method == "POST":
        access_key = request.form.get("AWS_ACCESS_KEY_ID")
        secret_key = request.form.get("AWS_SECRET_ACCESS_KEY")
        region = request.form.get("AWS_DEFAULT_REGION")
        print(region , access_key , secret_key)
        
    username = "abc"
    save_file_aws(username, access_key, secret_key, region)
    aws_info = check_aws()
    azure_info = check_azure()
    gcp_info = check_gcp()

    return render_template(
        "cloud_acc_info.html",
        aws_info=aws_info,
        azure_info=azure_info,
        gcp_info=gcp_info
    )

@reconfigure_bp.route('/azure_save_data',methods=["GET","POST"])
def azure_save_data():
    if request.method == "POST":
        client_id = request.form.get("AZURE_CLIENT_ID")
        secret = request.form.get("AZURE_SECRET")
        tenant_id = request.form.get("AZURE_TENANT_ID")
        subscription_id = request.form.get("AZURE_SUBSCRIPTION_ID")
        print(client_id , secret , tenant_id, subscription_id)
        print("azure")
        
    username = "abc"
    save_file_azure(username, client_id, secret, tenant_id, subscription_id)
    aws_info = check_aws()
    azure_info = check_azure()
    gcp_info = check_gcp()

    return render_template(
        "cloud_acc_info.html",
        aws_info=aws_info,
        azure_info=azure_info,
        gcp_info=gcp_info
    )


def check_aws():
    try:
        # Get Caller Identity
        sts_cmd = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--output", "json"],
            capture_output=True, text=True
        )
        sts_output = json.loads(sts_cmd.stdout) if sts_cmd.returncode == 0 else {"Error": sts_cmd.stderr}

        # Get AWS Configure list
        conf_cmd = subprocess.run(
            ["aws", "configure", "list"],
            capture_output=True, text=True
        )
        conf_output = conf_cmd.stdout.strip() if conf_cmd.returncode == 0 else conf_cmd.stderr.strip()

        return {
            "sts_identity": sts_output,
            "configure_list": conf_output
        }
    except Exception as e:
        return {"Error": str(e)}

# ---------------- Azure ----------------
def check_azure():
    try:
        # Run az account show
        az_cmd = subprocess.run(
            ["az", "account", "show", "--output", "json"],
            capture_output=True, text=True
        )
        if az_cmd.returncode == 0:
            az_output = json.loads(az_cmd.stdout)
        else:
            az_output = {"Error": az_cmd.stderr}

        return az_output
    except Exception as e:
        return {"Error": str(e)}

# ---------------- GCP ----------------
def check_gcp():
    try:
        # gcloud auth list
        auth_cmd = subprocess.run(
            ["gcloud", "auth", "list", "--format=json"],
            capture_output=True, text=True
        )
        auth_output = json.loads(auth_cmd.stdout) if auth_cmd.returncode == 0 else {"Error": auth_cmd.stderr}

        # gcloud config list
        config_cmd = subprocess.run(
            ["gcloud", "config", "list", "--format=json"],
            capture_output=True, text=True
        )
        config_output = json.loads(config_cmd.stdout) if config_cmd.returncode == 0 else {"Error": config_cmd.stderr}

        return {
            "auth_list": auth_output,
            "config_list": config_output
        }
    except Exception as e:
        return {"Error": str(e)}

@reconfigure_bp.route("/aws")
def aws_page():
    return render_template("aws_configure.html")

@reconfigure_bp.route("/azure")
def azure_page():
    return render_template("azure_configure.html")

@reconfigure_bp.route("/gcp")
def gcp_page():
    return render_template("gcp_configure.html")
