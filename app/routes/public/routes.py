from flask import render_template, request, session, url_for, flash, redirect, abort
from flask_login import login_required, current_user
from datetime import datetime
from app.routes.public import bp
from app.models import Device, CartItem, Customer, CustomerOrder, CustomerOrderItem
from app.forms import CheckoutForm
from app import db

# PUBLIC ROUTE
# PUBLIC ROUTE
@bp.route('/public')
@bp.route('/')
def home():
    # Check if user is authenticated
    if current_user.is_authenticated:
        # Redirect based on user role
        if current_user.is_admin():
            return redirect(url_for('reports.dashboard'))
        elif current_user.is_staff():
            return redirect(url_for('staff.dashboard'))
        elif current_user.is_customer():
            return redirect(url_for('customers.dashboard'))
    
    # Show public view for unauthenticated users
    return render_template('public/home.html', public_view=True)


# PUBLIC SEARCH ROUTE 
@bp.route('/search')
def search():
    query = request.args.get('query', '')
    products = Device.query.filter(
        Device.model.ilike(f"%{query}%") |
        Device.brand.ilike(f"%{query}%")
    ).all()
    return render_template('customers/dashboard.html', products=products)



