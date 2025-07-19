import os
from datetime import timedelta
from warnings import warn

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        warn('Using default SECRET_KEY. Please set SECRET_KEY in production!', RuntimeWarning)
        SECRET_KEY = 'dev-key-please-change-in-production'
    
    # Database configuration
   # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diamond.db')

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


class DevelopmentConfig(Config):
    DEBUG = True
    WTF_CSRF_ENABLED = False  # Often disabled in development for easier testing


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False