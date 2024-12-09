import os
from flask import Flask, g, render_template
from flask_mysqldb import MySQL
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',  # This should be a random secret key in production
    )
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'newpassword'
    app.config['MYSQL_DB'] = 'jcomp'

    # If test_config is provided, load that instead
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # # Initialize CSRF protection
    # csrf = CSRFProtect(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    import db
    db.init_app(app)

    # Initialize authentication blueprint
    from auth import create_auth_blueprint
    auth_bp = create_auth_blueprint(login_manager)
    app.register_blueprint(auth_bp)
    app.add_url_rule('/', endpoint='auth.login')

    # Register the items blueprint
    from items import bp as items_bp
    app.register_blueprint(items_bp)
    from reports import bp as reports_bp
    app.register_blueprint(reports_bp)
    from orders import bp as orders_bp
    app.register_blueprint(orders_bp)
    from donations import bp as donations_bp
    app.register_blueprint(donations_bp)
    from users import bp as users_bp
    app.register_blueprint(users_bp)
    # Simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    # Add CSP header to every response
    @app.after_request
    def apply_csp(response):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self'; "
            "object-src 'none'; "
            "frame-src 'none'; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "worker-src 'self'; "
        )
        return response

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
