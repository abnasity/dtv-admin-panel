from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, bcrypt, csrf
    



@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Flask extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Add template context processor for current date
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.utcnow()}

    # Import web route blueprints
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.devices import bp as devices_bp
    from app.routes.sales import bp as sales_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.customers import bp as customers_bp
    from app.routes.public import bp as public_bp
    
     # Register web route blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(devices_bp, url_prefix='/devices', name='devices')
    app.register_blueprint(sales_bp, url_prefix='/sales', name='sales')
    app.register_blueprint(reports_bp, url_prefix='/reports', name='reports')
    app.register_blueprint(customers_bp, url_prefix='/customers', name='customers')
    app.register_blueprint(public_bp, url_prefix='/public', name='public')
    
    # Import API blueprints
    from app.api.auth import bp as auth_api_bp
    from app.api.devices import bp as devices_api_bp
    from app.api.sales import bp as sales_api_bp
    from app.api.reports import bp as reports_api_bp
    
    # Register API blueprints
    app.register_blueprint(auth_api_bp, url_prefix='/api/auth', name='api_auth')
    app.register_blueprint(devices_api_bp, url_prefix='/api/devices', name='api_devices')
    app.register_blueprint(sales_api_bp, url_prefix='/api/sales', name='api_sales')
    app.register_blueprint(reports_api_bp, url_prefix='/api/reports', name='api_reports')
     # Exempt blueprint or individual view
    csrf.exempt(devices_api_bp)
    

    return app