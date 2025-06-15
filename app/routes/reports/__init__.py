from flask import Blueprint

bp = Blueprint('reports', __name__)

from app.routes.reports import routes
