import os
import sys
import logging
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, current_app
from flask_wtf.csrf import generate_csrf
from flask_login import current_user
from config import Config
from app.extensions import db, migrate, login_manager, bcrypt, csrf, mail
from app.models import User
from app.utils.cloudinary_utils import init_cloudinary
import cloudinary

load_dotenv()

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Flask-Login setup
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

    # Load config
    app.config.from_object(config_class)
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
    )

    # Logging setup for Vercel
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.exception("Unhandled Exception: %s", e)
        return "Internal Server Error", 500

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    init_cloudinary()

    # Context processors
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.utcnow()}

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf())

    @app.context_processor
    def utility_processor():
        def file_exists(filepath):
            absolute_path = os.path.join(current_app.root_path, filepath)
            return os.path.isfile(absolute_path)
        return dict(file_exists=file_exists)

    # Register web blueprints
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.devices import bp as devices_bp
    from app.routes.sales import bp as sales_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.staff import bp as staff_bp

    app.register_blueprint(main_bp, url_prefix='/main')
    app.register_blueprint(auth_bp)
    app.register_blueprint(devices_bp, url_prefix='/devices', name='devices')
    app.register_blueprint(sales_bp, url_prefix='/sales', name='sales')
    app.register_blueprint(reports_bp, url_prefix='/reports', name='reports')
    app.register_blueprint(staff_bp, url_prefix='/staff', name='staff')

    # Register API blueprints
    from app.api.auth import bp as auth_api_bp
    from app.api.devices import bp as devices_api_bp
    from app.api.sales import bp as sales_api_bp
    from app.api.reports import bp as reports_api_bp
    from app.api.users import bp as users_api_bp

    app.register_blueprint(auth_api_bp, url_prefix='/api/auth', name='api_auth')
    app.register_blueprint(devices_api_bp, url_prefix='/api/devices', name='api_devices')
    app.register_blueprint(sales_api_bp, url_prefix='/api/sales', name='api_sales')
    app.register_blueprint(reports_api_bp, url_prefix='/api/reports', name='api_reports')
    app.register_blueprint(users_api_bp, url_prefix='/api/users', name='api_users')

    # Exempt CSRF for APIs
    csrf.exempt(auth_api_bp)
    csrf.exempt(devices_api_bp)
    csrf.exempt(sales_api_bp)
    csrf.exempt(reports_api_bp)
    csrf.exempt(users_api_bp)

    return app
