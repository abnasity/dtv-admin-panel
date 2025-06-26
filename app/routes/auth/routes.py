from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models import User, CustomerOrder, Customer, CartItem
from app.forms import LoginForm, ProfileForm, RegisterForm
from app.decorators  import admin_required
from app.utils.helpers import assign_staff_to_order
from app.routes.auth import bp
from datetime import datetime

# LOGIN
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('reports.dashboard'))
            
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(
            username=form.username.data,
            email=form.email.data
        ).first()
        
        if user and user.check_password(form.password.data):
            # Update last seen timestamp
            user.last_seen = db.func.now()
            db.session.commit()
            
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('reports.dashboard'))
        else:
            flash('Invalid login credentials. Please check your username, email, and password.', 'danger')
            
    return render_template('auth/login.html', form=form)

# PROFILE MANAGEMENT   
@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    
       
    form = ProfileForm(current_user.username, current_user.email)
    
    if not isinstance(current_user, User):
        abort(403, message="Access denied: only authenticated users can access this page.")
        redirect(url_for('customers.login'))
    
    if form.validate_on_submit():
        if form.current_password.data and not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return render_template('auth/profile.html', form=form)
        
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        if form.new_password.data:
            if form.new_password.data != form.confirm_password.data:
                flash('New passwords do not match', 'danger')
                return render_template('auth/profile.html', form=form)
            current_user.set_password(form.new_password.data)
        
        db.session.commit()
        flash('Your profile has been updated', 'success')
        return redirect(url_for('auth.profile'))
    
    # Pre-populate form with current data
    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    return render_template('auth/profile.html', form=form)


# LOGOUT
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ADMIN DASHBOARD
# USER MANAGEMENT
@bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    
    query = User.query
    
    
    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    # Apply role filter
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    # Apply status filter
    if status_filter:
        is_active = status_filter == 'active'
        query = query.filter(User.is_active == is_active)
    
    # Apply pagination
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    form = RegisterForm()  # Form for the add user modal
    customers = Customer.query.order_by(Customer.full_name).all()
    form.address.choices = [(c.delivery_address, f"{c.full_name} - {c.delivery_address}") for c in customers]
    form.address.choices.append(('__new__', 'Other (Add new address)'))
    return render_template('auth/users.html',
                         users=pagination.items,
                         pagination=pagination,
                         search=search,
                         role_filter=role_filter,
                         status_filter=status_filter,
                         form=form,
                         customers=customers
                         )
    
  


# CREATE USER
@bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    form = RegisterForm()
     # Dynamically populate address choices
    customers = Customer.query.all()
    form.address.choices = [(customer.delivery_address, f"{customer.full_name} - {customer.delivery_address}") for customer in customers]
    form.address.choices.append(('__new__', 'Other (Add new address)'))
    
    if form.validate_on_submit():
        
        address = form.address.data
        if address == '__new__':
            address = form.new_address.data
            
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            address=address
        )
        user.set_password(form.password.data)
        db.session.add(user)
    
    try:
        db.session.commit()
        flash(f'User {user.username} has been created successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error creating user', 'danger')
    
    return redirect(url_for('auth.users'))

# TOGGLE USER STATUS
@bp.route('/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent self-deactivation
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot modify your own status'})
    
    user.is_active = not user.is_active
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'User {user.username} has been {"activated" if user.is_active else "deactivated"}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Database error occurred'})

# GET USER DATA FOR EDITING
@bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user(user_id):
    """Get user data for editing"""
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role
    })

# BULK USER STATUS UPDATE
@bp.route('/users/bulk_status', methods=['POST'])
@login_required
@admin_required
def bulk_update_status():
    """Handle bulk user status updates"""
    data = request.get_json()
    
    if not data or 'user_ids' not in data or 'activate' not in data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400
        
    user_ids = data['user_ids']
    activate = data['activate']
    
    try:
        # Don't allow modifying current user's status
        users = User.query.filter(
            User.id.in_(user_ids),
            User.id != current_user.id
        ).all()
        
        for user in users:
            user.is_active = activate
            
        db.session.commit()
        action = 'activated' if activate else 'deactivated'
        return jsonify({
            'success': True,
            'message': f'{len(users)} users have been {action}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Database error: {str(e)}'
        }), 500

# EDIT USER
@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Handle user edit form submission"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'address': user.address
        })

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    try:
        # Check if it's an attempt to modify the current admin's role
        if user.id == current_user.id and data.get('role') != 'admin' and user.role == 'admin':
            return jsonify({'success': False, 'error': 'Cannot remove admin role from yourself'}), 400
        
        # Validate required fields
        if not data.get('username') or not data.get('email') or not data.get('role'):
            return jsonify({'success': False, 'error': 'Please fill in all required fields'}), 400
        
        if data.get('role') not in ['admin', 'staff']:
            return jsonify({'success': False, 'error': 'Invalid role selected'}), 400
        
        # Check if username/email are taken by other users
        username_exists = User.query.filter(User.username == data['username'], User.id != user_id).first()
        email_exists = User.query.filter(User.email == data['email'], User.id != user_id).first()
        
        if username_exists:
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        if email_exists:
            return jsonify({'success': False, 'error': 'Email already registered'}), 400

        # Update user
        user.username = data['username']
        user.email = data['email']
        user.role = data['role']
        user.address = data.get('address', user.address)

        
        if data.get('password'):
            user.set_password(data['password'])
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    

# CUSTOMER MANAGEMENT (ADMIN DASHBOARD)
# # ADMIN ORDER APPROVAL  
# # ADMIN ORDER APPROVAL  
@bp.route('/admin/approve-order/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def approve_order(order_id):
    if not current_user.is_admin():
        abort(403)

    order = CustomerOrder.query.get_or_404(order_id)

    # Mark devices as sold
    for item in order.items:
        if item.device.status != 'available':
            flash(f"Device {item.device.imei} is already sold.", "danger")
            return redirect(url_for('auth.view_order', order_id=order.id))
        item.device.mark_as_sold()

    order.status = 'approved'
    order.approved_by_id = current_user.id
    order.approved_at = datetime.utcnow()

    # Assign staff if not already assigned
    if not order.assigned_staff:       
        assign_staff_to_order(order)

    # Notify assigned staff
    if order.assigned_staff:
        print(f"Notify {order.assigned_staff.username}: Order #{order.id} for {order.customer.full_name} approved.")

    # Delete cart items after approval
    for item in order.items:
        cart_item = CartItem.query.filter_by(
            customer_id=order.customer_id,
            device_id=item.device_id
        ).first()
        if cart_item:
            db.session.delete(cart_item)

    db.session.commit()

    flash("Order approved and devices marked as sold.", "success")
    return redirect(url_for('auth.view_orders'))



# CUSTOMER ORDERS 
@bp.route('/admin/orders')
@login_required
@admin_required
def view_orders():
    orders = CustomerOrder.query.order_by(CustomerOrder.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

# SINGLE ORDER VIEW
@bp.route('/admin/order/<int:order_id>')
@login_required
@admin_required
def view_order(order_id):
    order = CustomerOrder.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)

# ADMIN CANCEL ORDER
@bp.route('/admin/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_order(order_id):
    order = CustomerOrder.query.get_or_404(order_id)

    if order.status != 'pending':
        flash("Only pending orders can be cancelled.", "warning")
        return redirect(url_for('auth.view_order', order_id=order.id))

    # Set status to 'cancelled'
    order.status = 'cancelled'
    order.approved_by_id = current_user.id
    order.approved_at = datetime.utcnow()
    order.notes = "Cancelled by admin"

    db.session.commit()

    flash("Order has been cancelled successfully.", "success")
    return redirect(url_for('auth.view_orders'))

# ADMIN DELETE ORDER
@bp.route('/admin/orders/<int:order_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_order(order_id):
    order = CustomerOrder.query.get_or_404(order_id)

    if order.status != 'cancelled':
        flash("Only cancelled orders can be deleted.", "warning")
        return redirect(url_for('auth.view_order', order_id=order.id))

    db.session.delete(order)
    db.session.commit()
    flash("Cancelled order deleted successfully.", "success")
    return redirect(url_for('auth.view_orders'))

# PENDING ORDERS
@bp.route('/orders/pending')
@login_required
@admin_required
def pending_orders():
    orders = CustomerOrder.query.filter_by(status='pending').order_by(CustomerOrder.created_at.desc()).all()
    return render_template('admin/orders_pending.html', orders=orders)

# APPROVED ORDERS
@bp.route('/orders/approved')
@login_required
@admin_required
def approved_orders():
    orders = CustomerOrder.query.filter_by(status='approved').order_by(CustomerOrder.created_at.desc()).all()
    return render_template('admin/orders_approved.html', orders=orders)

# ASSIGN STAFF TO CUSTOMER
def assign_staff_to_order(order):
    if not order.delivery_address:
        return None  # Can't match without delivery address

    matching_staff = User.query.filter_by(role='staff', address=order.delivery_address).first()

    if matching_staff:
        order.assigned_staff = matching_staff  # Make sure this relationship exists
        db.session.commit()
        return matching_staff

    return None

# ASSIGNMENTS
@bp.route('/assignments')
@login_required
@admin_required
def view_assignments():
    orders = CustomerOrder.query.filter(CustomerOrder.assigned_staff_id != None).order_by(CustomerOrder.created_at.desc()).all()
    return render_template('admin/view_assignments.html', orders=orders)

# DELETE CUSTOMER
@bp.route('/<int:id>', methods=['DELETE'])
def delete_customer(id):
    """Delete a customer by ID"""
    customer = Customer.query.get_or_404(id)

    try:
        db.session.delete(customer)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        print(f"❌ Delete failed for customer {id}: {e}")
        return jsonify({'error': 'Delete failed'}), 500
