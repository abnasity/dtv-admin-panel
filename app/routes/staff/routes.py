from app.routes.staff import bp
from app.utils.decorators import staff_required
from flask_login import login_required
from flask import render_template




@bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    return render_template('staff/dashboard.html')