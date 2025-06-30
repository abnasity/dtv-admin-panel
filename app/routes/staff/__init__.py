from flask import Blueprint

bp = Blueprint('staff', __name__, url_prefix='/staff')

from app.routes.staff import routes
