from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_security import Security
from flask_mail import Mail
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
migrate = Migrate()
security = Security()
mail = Mail()
csrf = CSRFProtect()
login_manager = LoginManager()
bcrypt = Bcrypt()
