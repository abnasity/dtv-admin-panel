from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate



# Initialize flask extensions
db = SQLAlchemy()
migrate = Migrate()



def  create_app():
    app = Flask(__name__)
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    
    return app
    