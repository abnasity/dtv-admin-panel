from flask_login import current_user
from app.models import User, Customer, Device
from flask import render_template, redirect, url_for, request
from app.routes.public import bp

@bp.route('/')
def home():
    if current_user.is_authenticated:
        # Redirect based on user role
        if isinstance(current_user, User):
            if current_user.is_admin():
                return redirect(url_for('reports.dashboard'))
            elif current_user.is_staff():
                return redirect(url_for('staff.dashboard'))
        elif isinstance(current_user, Customer):
            return redirect(url_for('customers.dashboard'))

 
    featured_devices = Device.get_featured()

    return render_template(
        'public/home.html',
        public_view=True,
        featured_devices=featured_devices
    )




@bp.route('/logged-out')
def logged_out():
    featured_devices = Device.get_featured()

    return render_template('public/home.html', public_view=True, featured_devices=featured_devices)


@bp.route('/device/<imei>')
def public_device_redirect(imei):
    return redirect(url_for('devices.view_device_by_imei', imei=imei))