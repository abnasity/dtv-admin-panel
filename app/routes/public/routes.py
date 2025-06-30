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

    # Unauthenticated users see public home page
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



