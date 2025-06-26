from flask import render_template, redirect, url_for, flash, request, jsonify, abort, session, make_response
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db, bcrypt
from app.models import Customer, Device, CartItem, CustomerOrder, CustomerOrderItem
from app.forms import CustomerRegistrationForm, CustomerLoginForm, CustomerEditForm, CheckoutForm
from datetime import datetime
from app.routes.customers import bp
from app.utils.helpers import assign_staff_to_order

# REGISTER
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = CustomerRegistrationForm()

    if form.validate_on_submit():
        # Check for existing email
        existing_customer = Customer.query.filter_by(email=form.email.data).first()
        if existing_customer:
            flash('Email already registered.', 'danger')
            return redirect(url_for('customers.login'))

        # Create and save new customer
        customer = Customer(
            email=form.email.data.lower(),
            full_name=form.full_name.data,
            phone_number=form.phone_number.data,
            address=form.address.data
        )
        customer.set_password(form.password.data)
        db.session.add(customer)
        db.session.commit()
        login_user(customer, remember=True)
        flash('Registration successful! Welcome!', 'success')
        return redirect(url_for('customers.dashboard'))

    return render_template('customers/register.html', form=form)


# LOGIN
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('customers.dashboard'))

    form = CustomerLoginForm()

    # ✅ Show flash message if redirected for device access
    reason = request.args.get('reason')
    if reason == 'access_devices':
        flash("Please login to access available devices.", "warning")

    if form.validate_on_submit():
        customer = Customer.query.filter_by(email=form.email.data.lower()).first()
        if customer and customer.check_password(form.password.data):
            customer.last_seen = datetime.utcnow()
            db.session.commit()
            remember = getattr(form, 'remember_me', False)
            login_user(customer, remember=remember.data if remember else False)
           
            # ✅ Merge session cart (after login)
            cart = session.pop('cart', [])
            for device_id in cart:
                existing = CartItem.query.filter_by(customer_id=customer.id, device_id=device_id).first()
                if not existing:
                    db.session.add(CartItem(customer_id=customer.id, device_id=device_id))
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page or url_for('customers.dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('customers/login.html', form=form)


# LOGOUT
@bp.route('/logout')
@login_required
def logout():
    # 1. First logout the user
    logout_user()
    
    # 2. Clear all session data (recommended for security)
    session.clear()
    
    # 3. Create response before flashing to ensure headers are set
    response = make_response(redirect(url_for('public.home')))
    
    # 4. Add cache-control headers to prevent back-button access
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    
    # 5. Flash message after response is created
    flash('You have been successfully logged out.', 'success')
    
    return response
   

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
        return redirect(url_for('customers.dashboard'))

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



# CUSTOMER DASHBOARD
@bp.route('/dashboard')
@login_required
def dashboard():
    # Ensure only customers access this route
    if not isinstance(current_user, Customer):
        abort(403, description="Unauthorized access: Customers only.")
    products = Device.query.all()

    return render_template('customers/dashboard.html', products=products)


# CUSTOMER CARTS
@bp.route('/cart')
@login_required
def view_cart():
    if not isinstance(current_user, Customer):
        abort(403)

    cart_items = CartItem.query.filter_by(customer_id=current_user.id, status='active').all()
    return render_template('customers/cart.html', cart_items=cart_items)

# CUSTOMERS CART ROUTES
# The user is a customer
# ADD TO CART
@bp.route('/add-to-cart/<int:device_id>', methods=['POST'])
@login_required
def add_to_cart(device_id):
    if not isinstance(current_user, Customer):
        abort(403)

    device = Device.query.get_or_404(device_id)

    # Check if item already exists in cart
    cart_item = CartItem.query.filter_by(customer_id=current_user.id, device_id=device.id).first()
    if cart_item:
        flash("Item already in cart.", "info")
    else:
        new_item = CartItem(customer_id=current_user.id, device_id=device.id)
        db.session.add(new_item)
        flash(f"{device.brand} {device.model} added to cart!", "success")

    db.session.commit()
    return redirect(request.referrer or url_for('customers.dashboard'))






# REMOVE FROM CART
@bp.route('/remove-from-cart/<int:device_id>', methods=['POST'])
@login_required
def remove_from_cart(device_id):
    if isinstance(current_user, Customer):
        CartItem.query.filter_by(customer_id=current_user.id, device_id=device_id).delete()
        db.session.commit()
        flash("Item removed from cart.", "info")
    else:
        flash("Unauthorized access.", "danger")

    return redirect(url_for('customers.view_cart'))



# PROCEED TO CHECKOUT
@bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if not isinstance(current_user, Customer):
        flash("Only customers can checkout.", "danger")
        return redirect(url_for('customers.view_cart'))

    cart_items = CartItem.query.filter_by(customer_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty.", "info")
        return redirect(url_for('customers.view_cart'))

    devices = [Device.query.get(item.device_id) for item in cart_items]
    total_price = sum(float(d.purchase_price) for d in devices if d)
    form = CheckoutForm()

    return render_template('customers/checkout.html', products=devices, total_price=total_price, form=form)

# PLACING AN ORDER
@bp.route('/place_order', methods=['POST'])
@login_required
def place_order():
    if not isinstance(current_user, Customer):
        abort(403)

    form = CheckoutForm()
    if not form.validate_on_submit():
        flash("Please fill the form correctly.", "danger")
        return redirect(url_for('customers.checkout'))

    # Fetch active cart items
    cart_items = CartItem.query.filter_by(customer_id=current_user.id, status='active').all()
    if not cart_items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('customers.view_cart'))

    # Build a list of device IDs from the cart
    cart_item_ids = sorted([item.device_id for item in cart_items if item.device_id])

    # Get all previous non-cancelled orders (pending or approved)
    existing_orders = CustomerOrder.query.filter(
        CustomerOrder.customer_id == current_user.id,
        CustomerOrder.status.in_(['pending', 'approved'])
    ).all()

    for order in existing_orders:
        order_items = CustomerOrderItem.query.filter_by(order_id=order.id).all()
        order_item_ids = sorted([item.device_id for item in order_items if item.device_id])

        if cart_item_ids == order_item_ids:
            flash("You already have an identical order that is pending or confirmed.", "danger")
            return redirect(url_for('customers.view_cart'))

    # Debug: print cart items
    print(f"Cart items for customer {current_user.id}:")
    for item in cart_items:
        print(f"- {item.device.brand} {item.device.model} (IMEI: {item.device.imei})")

    # Create new order
    order = CustomerOrder(
        customer_id=current_user.id,
        delivery_address=form.delivery_address.data,
        status='pending',
        created_at=datetime.utcnow()
    )
    db.session.add(order)
    db.session.flush()

    # Assign staff to the order
    assigned = assign_staff_to_order(order)
    if assigned:
        print(f"[SUCCESS] Assigned staff: {assigned.username}")
    else:
        print("[WARNING] No matching staff found.")

    db.session.add(order)  # Ensure any changes are tracked

    # Add order items from cart
    for item in cart_items:
        device = item.device
        if not device or device.status != 'available':
            continue

        order_item = CustomerOrderItem(
            order_id=order.id,
            device_id=device.id,
            unit_price=device.purchase_price
        )
        db.session.add(order_item)

    db.session.commit()

    flash("Your order has been placed successfully!", "success")
    return redirect(url_for('customers.order_detail', order_id=order.id))




# ORDER DETAIL ROUTE
@bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = CustomerOrder.query.get_or_404(order_id)

    if order.customer_id != current_user.id:
        abort(403)

    return render_template('customers/order_detail.html', order=order)



# SUCCESSFUL ORDER
@bp.route('/order-success')
@login_required
def order_success():
    if not isinstance(current_user, Customer):
        abort(403)
    return render_template('customers/order_success.html')