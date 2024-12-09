import mysql.connector
import re
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app, session
)
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db
from flask_login import LoginManager, UserMixin
from flask_login import login_user, logout_user, current_user, login_required
import hashlib
import secrets

# Define your User class that extends UserMixin
class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username

def create_auth_blueprint(login_manager: LoginManager):
    bp = Blueprint('auth', __name__, url_prefix='/auth')
    PEPPER = "mypepper"
    
    def generate_salt():
        """Generate a random salt"""
        return secrets.token_hex(16)  # Generates a random 16-byte salt

    def hash_password(password, salt):
        """Hash password with salt and pepper"""
        salted_password = f"{salt}{password}{PEPPER}"  # Combine salt, password, and pepper
        return hashlib.sha256(salted_password.encode('utf-8')).hexdigest()

    @login_manager.user_loader
    def load_user(user_id):
        db = get_db()
        cursor = db.cursor(dictionary=True)  # ensure dictionary cursor
        cursor.execute('SELECT * FROM Person WHERE userName = %s', (user_id,))
        user = cursor.fetchone()
        if user is None:
            return None
        return User(user['userName'])

    @bp.route('/register', methods=('GET', 'POST'))
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
                    db.commit()
                except mysql.connector.IntegrityError:
                    error = f"User {username} is already registered."
                else:
                    return redirect(url_for("auth.login"))

            flash(error)

        return render_template('auth/register.html')

    @bp.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('auth.index'))

        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            db = get_db()
            cursor = db.cursor(dictionary=True)
            error = None

            # Validate username: alphanumeric and max 50 characters
            if len(username) > 50:
                error = 'Username cannot be longer than 50 characters.'
            elif not re.match("^[A-Za-z0-9]+$", username):
                error = 'Username can only contain English alphabets and numbers.'

            # Validate password: max 1000 characters
            elif len(password) > 1000:
                error = 'Password cannot be longer than 1000 characters.'
            
            if error is None:
                cursor.execute('SELECT * FROM Person WHERE userName = %s', (username,))
                user = cursor.fetchone()

                if user is None:
                    error = 'Non-existing username'
                else:
                    # Retrieve the stored salt and hashed password
                    stored_hash = user['password']
                    salt = user['salt']

                    # Hash the input password with the stored salt and the pepper
                    hashed_input_password = hash_password(password, salt)

                    if stored_hash != hashed_input_password:
                        error = 'Incorrect password.'

            if error is None:
                # Fetch role from Act table
                cursor.execute('SELECT roleID FROM Act WHERE userName = %s', (username,))
                role_result = cursor.fetchone()
                print(role_result)
                if role_result:
                    role = role_result['roleID']
                else:
                    role = 'No role assigned'

                # Store the role in session
                session['role'] = role
                session['username'] = username
                print(session['role'])
                # Create a User object and log the user in
                wrapped_user = User(user['userName'])
                login_user(wrapped_user)

                # Redirect to the index page, passing the role from session
                return redirect(url_for('auth.index'))
            
            flash(error)

        return render_template('auth/login.html')

    @bp.route('/logout')
    def logout():
        logout_user()
        session.pop('role', None)  # Clear the session role
        return redirect(url_for('auth.login'))

    @bp.route('/index', methods=('GET', 'POST'))
    def index():
        role = session.get('role', 'No role assigned')  # Get role from session
        return render_template('auth/index.html', role=role)

    return bp
