from flask import render_template
from app.routes.public import bp

@bp.route('/public')
@bp.route('/')
def home():
    return render_template('public/home.html', public_view=True)
    