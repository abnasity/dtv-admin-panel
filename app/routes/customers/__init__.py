from flask import Blueprint

bp = Blueprint('customers', __name__)

from app.routes.customers import routes 