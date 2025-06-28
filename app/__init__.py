from flask import Flask, request, jsonify
from config import Config
from app.extensions import db, migrate, login_manager, bcrypt, csrf
from flask_wtf.csrf import generate_csrf
from flask_login import current_user
from app.models import CartItem, User, Customer, CustomerOrder, Notification

login_manager.session_protection = "strong"
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    
    if user_id.startswith('user-'):
        user_id = user_id.replace('user-', '')
        return User.query.get(int(user_id))
    elif user_id.startswith('customer-'):
        user_id = user_id.replace('customer-', '')
        return Customer.query.get(int(user_id))
    return None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config.update(
    SESSION_COOKIE_SECURE=True,  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript cookie access
    SESSION_COOKIE_SAMESITE='Lax'  # CSRF protection
)
    
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

    #CONTEXT PROCESSORS 
    # Add template context processor for current date   
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.utcnow()}
    
    # This makes {{ csrf_token() }} available in all templates.
    @app.context_processor
    def inject_csrf_token():
     return dict(csrf_token=generate_csrf())
 
    @app.context_processor
    def inject_cart_count():
     cart_count = 0
     confirmed_orders_count = 0

     if hasattr(current_user, 'is_customer') and current_user.is_authenticated and current_user.is_customer():
        cart_count = CartItem.query.filter_by(customer_id=current_user.id).count()
        confirmed_orders_count = CustomerOrder.query.filter_by(customer_id=current_user.id, status='approved').count()

     return dict(cart_count=cart_count, confirmed_orders_count=confirmed_orders_count)
 
 
    @app.context_processor
    def inject_notifications():
     unread_count = 0  # Set a default

     if current_user.is_authenticated and getattr(current_user, 'role', None) == 'staff':
        unread_count = Notification.query.filter_by(
            staff_id=current_user.id, is_read=False
        ).count()

     return dict(unread_notifications_count=unread_count)

    




    # Import web route blueprints
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.devices import bp as devices_bp
    from app.routes.sales import bp as sales_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.customers import bp as customers_bp
    from app.routes.public import bp as public_bp
    
     # Register web route blueprints
    app.register_blueprint(main_bp, url_prefix='/main')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(devices_bp, url_prefix='/devices', name='devices')
    app.register_blueprint(sales_bp, url_prefix='/sales', name='sales')
    app.register_blueprint(reports_bp, url_prefix='/reports', name='reports')
    app.register_blueprint(customers_bp, url_prefix='/customers', name='customers')
    app.register_blueprint(public_bp)
    
    
    # Import API blueprints
    from app.api.auth import bp as auth_api_bp
    from app.api.devices import bp as devices_api_bp
    from app.api.sales import bp as sales_api_bp
    from app.api.reports import bp as reports_api_bp
    from app.api.users import bp as users_api_bp
    from app.api.customers import bp as customers_api_bp
    from app.api.orders import bp as orders_api_bp
    
    
    # Register API blueprints
    app.register_blueprint(auth_api_bp, url_prefix='/api/auth', name='api_auth')
    app.register_blueprint(devices_api_bp, url_prefix='/api/devices', name='api_devices')
    app.register_blueprint(sales_api_bp, url_prefix='/api/sales', name='api_sales')
    app.register_blueprint(reports_api_bp, url_prefix='/api/reports', name='api_reports')
    app.register_blueprint(users_api_bp, url_prefix='/api/users', name='api_users')
    app.register_blueprint(customers_api_bp, url_prefix='/api/customers', name='api_customers')
    app.register_blueprint(orders_api_bp, url_prefix='/api/orders', name='api_orders')
    
    # Exempt CSRF protection for API routes
    csrf.exempt(devices_api_bp)
    csrf.exempt(users_api_bp)
    csrf.exempt(auth_api_bp)
    csrf.exempt(customers_api_bp)
    csrf.exempt(orders_api_bp)
      

    

    return app