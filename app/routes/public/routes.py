from flask_login import current_user
from app.models import User, Customer, Device
from flask import render_template, redirect, url_for, request
from app.routes.public import bp

@bp.route('/')
def home():
    if current_user.is_authenticated:
        # If the logged in user is a staff/admin
        if isinstance(current_user, User):
            if current_user.is_admin():
                return redirect(url_for('reports.dashboard'))
            elif current_user.is_staff():
                return redirect(url_for('staff.dashboard'))

        # If the logged in user is a customer
        elif isinstance(current_user, Customer):
            return redirect(url_for('customers.dashboard'))

    # Unauthenticated public user: show up to 8 most recent active devices
    featured_devices = (
        Device.query
        .filter_by(status='available')  # optional: only show available devices
        .order_by(Device.id.desc())
        .limit(8)
        .all()
    )
    
    return render_template(
        'public/home.html',
        public_view=True,
        featured_devices=featured_devices
    )
