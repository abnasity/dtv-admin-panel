import os
import sys
import logging
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, send_from_directory
from flask_wtf.csrf import generate_csrf
from config import Config
from app.extensions import db, migrate, login_manager, bcrypt, csrf, mail
from flask_login import current_user
from werkzeug.exceptions import HTTPException
from app.models import User,Device




load_dotenv()

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



 # CSRF token context processor
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf())
    
  # Recent devices context processor
    @app.context_processor
    def inject_recent_devices():
        # Get the 5 most recently added devices that are not deleted
        recent_devices = Device.query.filter_by(deleted=False)\
            .order_by(Device.arrival_date.desc())\
            .limit(5).all()
        return dict(recent_devices=recent_devices)
    

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
    from app.routes.transferred_sales import bp as transferred_sales_bp



   
    # Register web blueprints (only once)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(transferred_sales_bp)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # --- Automatic table creation and user seeding ---
    with app.app_context():
        db.create_all()

        def create_user(username, email, role, password):
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    email=email,
                    role=role,
                    is_active=True
                )
                user.set_password(password)
                db.session.add(user)
                print(f"✅ Created {role} user: {username}")

        # Seed only if users don't exist
        create_user("admin", "admin@example.com", "admin", "admin123")
        create_user("staff", "staff@example.com", "staff", "staff123")
        create_user("Diamond", "kiptokorir@gmail.com", "admin", "Dtv@2026")
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error seeding database: {e}")
    # --- End auto table creation and seeding ---

    # Import and register API blueprints
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

    return app
