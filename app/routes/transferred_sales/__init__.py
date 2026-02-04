from flask import Blueprint

bp = Blueprint('transferred_sales', __name__, url_prefix='/transferred_sales')


from app.routes.transferred_sales import routes
