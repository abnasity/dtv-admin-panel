from flask import render_template, redirect, url_for, abort
from flask_login import login_required
from app.models import Device
from app.routes.main import bp


@bp.route('/')
# @login_required
def index():
    return redirect(url_for('reports.dashboard'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html')
