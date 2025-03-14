from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import mysql
import os
from utils.aws_secrets import create_session
import subprocess

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def home():
    if "user" in session:
        return redirect(url_for("folder.folder_disply"))
    return redirect(url_for("auth.login"))

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        aws_access_key = request.form["aws_secret_id"]
        aws_secret_key = request.form["aws_secret_key"]
        username = request.form["username"]
        password = request.form["password"]
        password_hash = generate_password_hash(password)

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cur.fetchone()

        if existing_user:
            flash("Username already exists!", "danger")
        else:
            # temp = create_session(username,aws_access_key,aws_secret_key)
            if create_session(username,aws_access_key,aws_secret_key):
                cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
                mysql.connection.commit()
                cur.close()
                flash("Signup successful! Please log in.", "success")
        
            return redirect(url_for("auth.login"))

    return render_template("signup.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session["user"] = username
            os.makedirs(os.path.join("download", username), exist_ok=True)
            flash("Login successful!", "success")
            return redirect(url_for("auth.home"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))
