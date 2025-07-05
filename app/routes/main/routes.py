from flask import render_template, redirect, url_for, abort
from flask_login import login_required
from app.models import CustomerOrder, Customer, Device
from app.routes.main import bp

@bp.route('/dashboard')
def dashboard():
    
    stats = {
        'total_orders': CustomerOrder.query.count(),
        'pending_orders': CustomerOrder.query.filter_by(status='pending').count(),
        'approved_orders': CustomerOrder.query.filter_by(status='approved').count(),
        'failed_orders': CustomerOrder.query.filter_by(status='failed').count(),
        'registered_customers': Customer.query.count(),
        'assigned_orders': CustomerOrder.query.filter_by(status='assigned').count(),
        'total_devices': Device.query.filter_by(status='available').count()
    }

    return render_template('main/dashboard.html', stats=stats, show_nav=False)



@bp.route('/')
# @login_required
def index():
    return redirect(url_for('reports.dashboard'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html')
