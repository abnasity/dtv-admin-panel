import os
import sys
import logging
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, send_from_directory
from config import Config
from app.extensions import db, migrate, login_manager, bcrypt, csrf, mail
from flask_login import current_user
from werkzeug.exceptions import HTTPException
from app.models import User
import cloudinary

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Login manager hooks
@login_manager.unauthorized_handler
def custom_unauthorized():
    return redirect(url_for('auth.login', next=request.full_path))

@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith('user-'):
        user_id = user_id.replace('user-', '')
        return User.query.get(int(user_id))
    return None


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static')
    )

    app.config.from_object(config_class)
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
    )

    # Logging to stdout for Vercel
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    # Handle errors (keep HTTP errors like 404 unchanged)
    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return e
        app.logger.exception("Unhandled Exception: %s", e)
        return "Internal Server Error", 500

    # Serve favicon files from /static
    @app.route('/favicon.ico')
    @app.route('/favicon.png')
    def favicon():
        filename = 'favicon.ico' if request.path.endswith('.ico') else 'favicon.png'
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            filename
        )

    # Register blueprints
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.devices import bp as devices_bp
    from app.routes.sales import bp as sales_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.staff import bp as staff_bp
   
    # Register web blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(staff_bp)


    # Import API blueprints
    from app.api.auth import bp as auth_api_bp
    from app.api.devices import bp as devices_api_bp
    from app.api.sales import bp as sales_api_bp
    from app.api.reports import bp as reports_api_bp
    from app.api.users import bp as users_api_bp
        
    # Register API blueprints
    app.register_blueprint(auth_api_bp, url_prefix='/api/auth')
    app.register_blueprint(devices_api_bp, url_prefix='/api/devices')
    app.register_blueprint(sales_api_bp, url_prefix='/api/sales')
    app.register_blueprint(reports_api_bp, url_prefix='/api/reports')
    app.register_blueprint(users_api_bp, url_prefix='/api/users')

    

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    return app
