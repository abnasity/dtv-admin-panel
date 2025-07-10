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

    # For public users: show featured devices or fallback to recent
    featured_devices = (
        Device.query
        .filter(Device.featured.is_(True))
        .order_by(Device.arrival_date.desc())
        .all()
    )

    if not featured_devices:
        featured_devices = (
            Device.query
            .filter_by(status='available')
            .order_by(Device.id.desc())
            .all()
        )
    
    return render_template(
        'public/home.html',
        public_view=True,
        featured_devices=featured_devices
    )
