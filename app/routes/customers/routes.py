from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db, bcrypt
from app.models import Customer
from app.forms import CustomerRegistrationForm, CustomerLoginForm, CustomerEditForm
from datetime import datetime
from app.routes.customers import bp

# REGISTER
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = CustomerRegistrationForm()
    if form.validate_on_submit():
        customer = Customer(
            email=form.email.data,
            full_name=form.full_name.data,
            phone_number=form.phone_number.data,
            address=form.address.data
        )
        customer.set_password(form.password.data)
        db.session.add(customer)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('customers.login'))

    return render_template('customers/register.html', form=form)

# LOGIN
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = CustomerLoginForm()
    if form.validate_on_submit():
        customer = Customer.query.filter_by(email=form.email.data).first()
        if customer and customer.check_password(form.password.data):
            customer.last_seen = datetime.utcnow()
            db.session.commit()
            remember = getattr(form, 'remember_me', False)
            login_user(customer, remember=remember.data if remember else False)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        flash('Invalid email or password.', 'danger')

    return render_template('customers/login.html', form=form)

# LOGOUT
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('customers.login'))

# ACCOUNT STATUS TOGGLE
# This route allows toggling the account status (active/inactive)
@bp.route('/account/status', methods=['POST'])
@login_required
def toggle_status():
    current_user.is_active = not current_user.is_active
    db.session.commit()
    return jsonify({
        'success': True,
        'is_active': current_user.is_active
    })
    
# PROFILE MANAGEMENT
# This route allows customers to view and edit their profile information
# It includes password change functionality and ensures only authenticated customers can access it.
@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Ensure only customers can access this route
    if not isinstance(current_user, Customer):
        abort(403)

    form = CustomerEditForm(obj=current_user)

    if form.validate_on_submit():
        # Password change
        if form.new_password.data:
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('customers/profile.html', form=form)
            if form.new_password.data != form.confirm_password.data:
                flash('New passwords do not match.', 'danger')
                return render_template('customers/profile.html', form=form)
            current_user.set_password(form.new_password.data)

        # Profile fields
        current_user.full_name = form.full_name.data
        current_user.phone_number = form.phone_number.data
        current_user.address = form.address.data
        current_user.email = form.email.data

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('customers.profile'))

    return render_template('customers/profile.html', form=form)


# RETURN LOGGED-IN CUSTOMER INFO
# This route returns the logged-in customer's information in JSON format.
# It requires the user to be logged in and returns a 404 error if the customer is not found.
@bp.route('/me')
@login_required
def get_my_info():
    return jsonify(current_user.to_dict())

# GET CUSTOMER BY ID
@bp.route('/customers/<int:customer_id>')
@login_required
def get_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    return jsonify(customer.to_dict())
