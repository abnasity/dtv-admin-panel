import os
from datetime import timedelta
from warnings import warn
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        warn('Using default SECRET_KEY. Please set SECRET_KEY in production!', RuntimeWarning)
        SECRET_KEY = 'dev-key-please-change-in-production'
    
    # Database configuration
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        # For Render PostgreSQL
        if db_url and 'render.com' in db_url:
            if '?sslmode=' not in db_url:
                db_url += '?sslmode=require'
        
        return db_url or \
            'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diamond.db')

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,  # Reset connections regularly
        "pool_timeout": 30,   # 30 seconds timeout
        "max_overflow": 10,   # Max overflow connections
        "connect_args": {
            "connect_timeout": 10,  # 10 seconds connection timeout
            "keepalives": 1,        # Enable TCP keepalives
            "keepalives_idle": 30,   # 30 seconds before sending keepalives
            "keepalives_interval": 10,  # 10 seconds between keepalives
            "keepalives_count": 5    # 5 failed keepalives before closing
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