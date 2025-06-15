from flask import Blueprint

bp = Blueprint('devices', __name__)

from app.routes.devices import routes  