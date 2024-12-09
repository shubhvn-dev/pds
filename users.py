from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from db import get_db
import hashlib
import secrets
import re
import mysql.connector

bp = Blueprint('users', __name__, url_prefix='/users')
PEPPER = "mypepper"
def generate_salt():
    """Generate a random salt"""
    return secrets.token_hex(16)  # Generates a random 16-byte salt

def hash_password(password, salt):
    """Hash password with salt and pepper"""
    salted_password = f"{salt}{password}{PEPPER}"  # Combine salt, password, and pepper
    return hashlib.sha256(salted_password.encode('utf-8')).hexdigest()


@bp.route('/staff_register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        db = get_db()
        cursor = db.cursor(dictionary=True)
        error = None
        # Validate username: max 50 chars, alphanumeric only
        if len(username) > 50:
            error = 'Username cannot be longer than 50 characters.'
        elif not re.match("^[A-Za-z0-9]+$", username):
            error = 'Username can only contain English alphabets and numbers.'
            
        # Validate password: max 1000 chars
        elif len(password) > 1000:
            error = 'Password cannot be longer than 1000 characters.'

            # Validate first and last name: max 50 chars, alphabets only
        elif len(first_name) > 50 or not re.match("^[A-Za-z]+$", first_name):
            error = 'First name can only contain English alphabets and cannot be longer than 50 characters.'
        elif len(last_name) > 50 or not re.match("^[A-Za-z]+$", last_name):
            error = 'Last name can only contain English alphabets and cannot be longer than 50 characters.'

            # Validate email: max 100 chars, simple email format
        elif len(email) > 100:
            error = 'Email cannot be longer than 100 characters.'
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            error = 'Invalid email format.'

            # Check if the username already exists in the database
        cursor.execute("SELECT 1 FROM Person WHERE userName = %s", (username,))
        existing_user = cursor.fetchone()
            
        if existing_user:
            error = f"User {username} is already registered."

        if error is None:
            try:
                salt = generate_salt()
                hashed_password = hash_password(password, salt)
                cursor.execute(
                    "INSERT INTO Person (userName, password, fname, lname, email, salt) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (username, hashed_password, first_name, last_name, email, salt)
                )
                #add the user to the act table as staff
                cursor.execute(
                    "INSERT INTO Act (userName, roleID) "
                    "VALUES (%s, %s)",
                    (username, "staff")
                );
                db.commit()
            except mysql.connector.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('users/new_staff.html')