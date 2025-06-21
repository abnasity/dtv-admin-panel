from flask import render_template, request, session, url_for, flash, redirect, abort
from flask_login import login_required, current_user
from datetime import datetime
from app.routes.public import bp
from app.models import Device, CartItem, Customer, CustomerOrder, CustomerOrderItem
from app.forms import CheckoutForm
from app import db

# PUBLIC ROUTE
@bp.route('/public')
@bp.route('/')
def home():
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



