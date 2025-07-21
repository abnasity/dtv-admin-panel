from flask import render_template, redirect, url_for, abort
from flask_login import login_required
from app.models import CustomerOrder, Customer, Device
from app.routes.main import bp


@bp.route('/')
# @login_required
def index():
    return redirect(url_for('reports.dashboard'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html')


@main_bp.route('/device/<imei>')
def redirect_to_device(imei):
    return redirect(url_for('devices.view_device_by_imei', imei=imei))
