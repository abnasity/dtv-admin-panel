import os
from datetime import timedelta
import os
from datetime import timedelta
from warnings import warn
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

def get_database_uri():
    """Helper function to properly format the database URI"""
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # Convert postgres:// to postgresql://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        # Add SSL requirement for Render
        if 'render.com' in db_url and '?sslmode=' not in db_url:
            db_url += '?sslmode=require'
        
        return db_url
    
    # Fallback to SQLite
    return 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diamond.db')

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Database configuration (now a string, not a property)
# In your Flask app configuration (usually __init__.py or config.py)
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://user:password@dpg-d1o0ihripnbc73btv170-a.oregon-postgres.render.com:5432/database_name?sslmode=require'
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,  # Enable connection health checks
    'pool_recycle': 300,    # Recycle connections after 5 minutes
    'pool_timeout': 30,     # Connection timeout in seconds
    'max_overflow': 10      # Allow additional connections beyond pool size
        "connect_args": {
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        }
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        warn('Using default JWT_SECRET_KEY. Please set JWT_SECRET_KEY in production!', RuntimeWarning)
        JWT_SECRET_KEY = 'jwt-dev-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # CSRF configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Flask-Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    
    @classmethod
    def check_mail_config(cls):
        """Check if email configuration is valid"""
        if not cls.MAIL_USERNAME or not cls.MAIL_PASSWORD:
            warn('Email credentials not properly configured. Set MAIL_USERNAME and MAIL_PASSWORD environment variables.', RuntimeWarning)
            return False
        return True


class ProductionConfig(Config):
    # Override with production-specific settings
    DEBUG = False
    TESTING = False
    WTF_CSRF_ENABLED = True

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise ValueError("DATABASE_URL environment variable must be set in production")
        
        # Ensure proper PostgreSQL URI format for Render
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        if 'render.com' in db_url and '?sslmode=' not in db_url:
            db_url += '?sslmode=require'
        
        return db_url


class DevelopmentConfig(Config):
    DEBUG = True
    WTF_CSRF_ENABLED = False  # Often disabled in development for easier testing


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False