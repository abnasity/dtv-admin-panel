from flask import render_template, redirect, url_for, flash, request, jsonify, abort, session, make_response, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db, bcrypt
from app.models import Customer, Device, CartItem, CustomerOrder, CustomerOrderItem, User, Notification
from app.forms import CustomerRegistrationForm, CustomerLoginForm, CustomerEditForm, CheckoutForm, CustomerRequestResetForm, CustomerResetPasswordForm
from datetime import datetime
from app.routes.customers import bp
from app.utils.helpers import assign_staff_to_order, get_device_debug_info
from app.utils.mixins import ResetTokenMixin
from app.utils.email import send_customer_reset_email
from sqlalchemy import and_, func
from sqlalchemy.orm import load_only , aliased
import os


@bp.route('/forgot-password', methods=['GET', 'POST'])
def customer_reset_request():
    form = CustomerRequestResetForm()
    if form.validate_on_submit():
        customer = Customer.query.filter_by(email=form.email.data).first()
        if customer:
            send_customer_reset_email(customer)
            flash('Reset instructions have been sent to your email.', 'info')
        else:
            flash('No customer with that email exists.', 'warning')
        return redirect(url_for('customers.login'))
    return render_template('customers/reset_request.html', form=form)


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def customer_reset_token(token):
    customer = ResetTokenMixin.verify_reset_token(token, model_class=Customer)
    if not customer:
        flash('That is an invalid or expired token.', 'warning')
        return redirect(url_for('customers.customer_reset_request'))

    form = CustomerResetPasswordForm()
    if form.validate_on_submit():
        customer.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('customers.login'))

    return render_template('customers/reset_token.html', form=form, token=token)



# CUSTOMER SEARCH SECTION
@bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()

    devices_query = Device.query.filter(Device.status == 'available')

    if query:
        devices_query = devices_query.filter(
    (Device.model.ilike(f"%{query}%")) | 
    (Device.brand.ilike(f"%{query}%"))
)


    results = devices_query.order_by(Device.arrival_date.desc()).all()

    return render_template('customers/search_results.html', results=results, query=query)



# REGISTER
@bp.route('/register', methods=['GET', 'POST'])
def register():
    # if current_user.is_authenticated:
    #     return redirect(url_for('main.index'))

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
        )
        customer.set_password(form.password.data)
        db.session.add(customer)
        db.session.commit()
        login_user(customer, remember=False)
        flash('Registration successful! Welcome!', 'success')
        return redirect(url_for('customers.dashboard'))

    return render_template('customers/register.html', form=form)


# LOGIN
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('customers.dashboard'))

    form = CustomerLoginForm()

    # Show flash message if redirected for device access
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
           
            # Merge session cart (after login)
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
    logout_user()                # Remove the user from session
    session.clear()              # Clear session data

    response = make_response(redirect(url_for('public.logged_out')))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    # Clear both session and remember_token cookies
    response.set_cookie('session', '', expires=0)
    response.set_cookie('remember_token', '', expires=0)

    return response




 
# CUSTOMER DASHBOARD (Primary dashboard with products)
@bp.route('/dashboard')
@login_required
def dashboard():
    if not isinstance(current_user, Customer):
        abort(403)

    # Subquery to get one device per unique model spec
    subq = (
        db.session.query(
            Device.brand,
            Device.model,
            Device.ram,
            Device.rom,
            Device.color,
            func.min(Device.id).label('min_id')
        )
        .filter(
            Device.status == 'available',
            Device.deleted == False,
            Device.featured == False
        )
        .group_by(Device.brand, Device.model, Device.ram, Device.rom, Device.color)
        .subquery()
    )

    DeviceAlias = aliased(Device)
    products = (
        db.session.query(DeviceAlias)
        .join(subq, DeviceAlias.id == subq.c.min_id)
        .all()
    )

    # Optional: attach file existence info
    for device in products:
        if device.image_url.startswith('/static/'):
            static_path = device.image_url[1:]
            device.file_exists = os.path.exists(os.path.join(current_app.root_path, static_path))
        else:
            device.file_exists = False

    notifications = Notification.query.filter(
        Notification.user_id == current_user.id,
        Notification.recipient_type == 'customer'
    ).order_by(Notification.created_at.desc()).limit(5).all()

    return render_template('customers/dashboard.html',
                           products=products,
                           notifications=notifications)

    

# CUSTOMER DASH (Order-focused dashboard)
@bp.route('/dash')
@login_required
def dash():
    if not isinstance(current_user, Customer):
        abort(403, description="Unauthorized access: Customers only.")

    # Search and filter functionality
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')

    # Base query for orders
    query = CustomerOrder.query.filter_by(
        customer_id=current_user.id, 
        is_deleted=False
    )

    # Apply search filters if provided
    if q:
        query = query.join(CustomerOrder.items).join(Device).filter(
            db.or_(
                Device.name.ilike(f"%{q}%"),
                Device.imei.ilike(f"%{q}%")
            )
        )

    if status:
        query = query.filter(CustomerOrder.status == status)

    orders = query.order_by(CustomerOrder.created_at.desc()).all()

    # Get all customer notifications
    notifications = Notification.query.filter(
        Notification.user_id == current_user.id,
        Notification.recipient_type == 'customer'
    ).order_by(Notification.created_at.desc()).all()

    return render_template('customers/dash.html', 
                         orders=orders, 
                         notifications=notifications)

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



# DEVICE DETAIL PAGE
@bp.route('/device/<int:device_id>')
@login_required
def device_detail(device_id):
    device = Device.query.get_or_404(device_id)

    if device.status != 'available':
        flash('This device is no longer available.', 'warning')
        return redirect(url_for('customers.dashboard'))

    return render_template('customers/device_detail.html', device=device)



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

    device = Device.query.filter_by(id=device_id, status='available').first()
    if not device:
        flash("This device is no longer available.", "warning")
        return redirect(request.referrer or url_for('customers.dashboard'))


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
@bp.route('/checkout')
@login_required
def checkout():
    if not isinstance(current_user, Customer):
        abort(403)

    form = CheckoutForm()

    # Get unique addresses from staff
    staff_addresses = db.session.query(User.address).filter(
        User.role == 'staff',
        User.address.isnot(None)
    ).distinct().all()

    form.delivery_address.choices = [(addr.address, addr.address) for addr in staff_addresses]

    # Optional: preselect customer's last used address
    if current_user.delivery_address:
        form.delivery_address.data = current_user.delivery_address


    if current_user.id_number:
      form.id_number.data = current_user.id_number

    # Cart setup
    cart_items = CartItem.query.filter_by(customer_id=current_user.id, status='active').all()
    cart_items = [item for item in cart_items if item.device and item.device.status == 'available']
    products = [item.device for item in cart_items]
    total_price = sum(device.purchase_price for device in products)

    return render_template('customers/checkout.html', form=form, products=products, cart_items=cart_items, total_price=total_price)


# PLACING AN ORDER
@bp.route('/place_order', methods=['POST'])
@login_required
def place_order():
    if not isinstance(current_user, Customer):
        abort(403)

    form = CheckoutForm()

    # Load delivery address choices again
    staff_addresses = db.session.query(User.address).filter(
        User.role == 'staff',
        User.address.isnot(None)
    ).distinct().all()
    form.delivery_address.choices = [(addr.address, addr.address) for addr in staff_addresses]

    if not form.validate_on_submit():
        flash("Please fill the form correctly.", "danger")
        return redirect(url_for('customers.checkout'))

    # properly fetch cart items
    cart_items = CartItem.query.filter_by(customer_id=current_user.id, status='active').all()

    if not cart_items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('customers.view_cart'))


    cart_item_ids = sorted([item.device_id for item in cart_items if item.device_id])

    # Prevent duplicate orders
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

    # Save delivery info
    selected_address = form.delivery_address.data.strip()
    id_number = form.id_number.data.strip() if form.id_number.data else None

    if current_user.delivery_address != selected_address:
        current_user.delivery_address = selected_address
    
    if form.payment_type.data == 'credit' and not id_number:
        flash("National ID number is required for credit payments.", "danger")
        return redirect(url_for('customers.checkout'))
    
    if id_number and current_user.id_number != id_number:
        current_user.id_number = id_number
        db.session.add(current_user)

    # Create order
    order = CustomerOrder(
        customer_id=current_user.id,
        delivery_address=selected_address,
        payment_option=form.payment_type.data,
        status='pending',
        created_at=datetime.utcnow()
    )
    db.session.add(order)
    db.session.flush()  # Get order.id

    # Assign staff
    assign_staff_to_order(order)

    # Add order items and delete cart items
    for item in cart_items:
        device = item.device
        if device.status != 'available':
            flash("Some items in your cart are no longer available.", "danger")
            return redirect(url_for('customers.view_cart'))

        db.session.add(CustomerOrderItem(
            order_id=order.id,
            device_id=device.id,
            unit_price=device.purchase_price
        ))

        db.session.delete(item)  # remove from cart

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

# MY ORDERS
@bp.route('/my_orders')
@login_required
def my_orders():
    orders = CustomerOrder.query.filter(
        CustomerOrder.customer_id == current_user.id,
        CustomerOrder.status.in_(['approved', 'completed'])
    ).order_by(CustomerOrder.created_at.desc()).all()

    return render_template('customers/my_orders.html', orders=orders)


# BOUGHT DEVICES 
@bp.route('/my_devices')
@login_required
def my_devices():
    if not isinstance(current_user, Customer):
        abort(403)

    completed_orders = CustomerOrder.query.filter_by(
        customer_id=current_user.id,
        status='completed'
    ).order_by(CustomerOrder.completed_at.desc()).all()

    # Flatten all purchased devices
    purchased_items = []
    for order in completed_orders:
        for item in order.items:
            if item.device and item.device.status == 'sold':
                purchased_items.append({
                    'device': item.device,
                    'order': order,
                    'completed_at': order.completed_at
                })
    purchased_items.sort(key=lambda x: x['completed_at'] or x['order'].created_at, reverse=True)


    return render_template('customers/my_devices.html', purchased_items=purchased_items)


# NOTIFICATIONS
@bp.route('/notifications')
@login_required
def notifications():
    if current_user.role != 'customer':
        abort(403)

    show = request.args.get('filter', 'all')

    query = Notification.query.filter(
        Notification.user_id == current_user.id,
        Notification.recipient_type == 'customer'
    )

    if show == 'unread':
        query = query.filter_by(is_read=False)

    notifications = query.order_by(Notification.created_at.desc()).all()

    return render_template('customers/dash.html', notifications=notifications, current_filter=show)


# MARK NOTIFICATION AS READ
@bp.route('/notifications/mark_all_read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    # Only allow customers to access this route
    if current_user.role != 'customer':
        abort(403)

    # Mark all unread notifications for the current customer as read
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({Notification.is_read: True})
    db.session.commit()

    flash("All notifications marked as read.", "info")
    return redirect(url_for('customers.dash'))



# REJECTED ORDERS
@bp.route('/orders/rejected')
@login_required
def rejected_orders():
    orders = CustomerOrder.query.filter_by(customer_id=current_user.id, status='rejected').order_by(CustomerOrder.created_at.desc()).all()
    return render_template('customers/rejected_orders.html', orders=orders)

