from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models import User, CustomerOrder, Customer, Notification, Device
from app.forms import LoginForm, ProfileForm, RegisterForm
from app.decorators  import admin_required
from app.utils.decorators import staff_required
from app.utils.helpers import assign_staff_to_order
from app.routes.auth import bp
from datetime import datetime
from sqlalchemy import or_


# LOGIN
@bp.route('/login', methods=['GET', 'POST'])
def login():         
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            or_(
                User.username == form.username.data,
                User.email == form.email.data
            )
        ).first()
        
        if user and user.check_password(form.password.data):
            # Update last seen timestamp
            user.last_seen = db.func.now()
            db.session.commit()
            
            login_user(user, remember=form.remember_me.data)
            
            # Role-based redirection
            if user.role == 'admin':
                return redirect(url_for('auth.dashboard'))
            elif user.role == 'staff':
                return redirect(url_for('staff.dashboard'))
            elif user.role == 'customer':
                return redirect(url_for('customers.dashboard'))

            # Default fallback
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid login credentials. Please try again.', 'danger')

    return render_template('auth/login.html', form=form)


# PROFILE MANAGEMENT   
@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
          
    form = ProfileForm(current_user.username, current_user.email)
    
    if not isinstance(current_user, User):
        abort(403)
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
    user_role = current_user.role 
    logout_user()
    flash('You have been logged out.', 'info')

    # Redirect based on role
    if user_role in ['admin', 'staff']:
        return redirect(url_for('main.dashboard')) 
    elif user_role == 'customer':
        return redirect(url_for('customers.login'))
    else:
        return redirect(url_for('auth.login'))

    

# STAFF DASHBOARD
@bp.route('/notifications')
@login_required
def notifications():
    if current_user.role != 'staff':
        abort(403)
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('staff/notifications.html', notifications=notes)

# MARK AWAITING APPROVAL
@bp.route('/orders/<int:order_id>/awaiting-approval', methods=['POST'])
@login_required
@staff_required
def mark_awaiting_approval(order_id):
    order = CustomerOrder.query.get_or_404(order_id)
    order.status = 'awaiting_approval'
    db.session.commit()

    # notify admin again that it's ready for approval
    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        note = Notification(
            user_id=admin.id,
            message=f"Order #{order.id} by {order.customer.full_name} is ready for approval",
            recipient_type='admin',
            link=url_for('auth.view_order', order_id=order.id)
        )
        db.session.add(note)
    db.session.commit()

    flash("Order marked as awaiting approval.", "info")
    return redirect(url_for('auth.notifications'))


# VIEW ORDER FOR STAFF
@bp.route('/orders/<int:order_id>')
@login_required
@staff_required
def view_order_staff(order_id):
    order = CustomerOrder.query.get_or_404(order_id)

    # Ensure staff is only seeing orders assigned to them
    if order.assigned_staff_id != current_user.id:
        flash("You are not assigned to this order.", "danger")
        return redirect(url_for('auth.notifications'))

    # Mark related notification as read (if exists)
    notif_link = url_for('auth.view_order_staff', order_id=order.id)
    notification = Notification.query.filter_by(
        user_id=current_user.id,
        link=notif_link,
        is_read=False
    ).first()

    if notification:
        notification.is_read = True
        db.session.commit()

    return render_template('staff/order_detail.html', order=order)


# ASSIGNED ORDERS
@bp.route('/orders/assigned')
@login_required
@staff_required
def assigned_orders():
    orders = CustomerOrder.query.filter_by(assigned_staff_id=current_user.id).order_by(CustomerOrder.created_at.desc()).all()
    return render_template('staff/assigned_orders.html', orders=orders)



# ADMIN DASHBOARD
@bp.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_devices = Device.query.filter_by(status='available').count()
    pending_orders = CustomerOrder.query.filter_by(status='pending').count()

    recent_orders = CustomerOrder.query.order_by(CustomerOrder.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_devices=total_devices,
                           pending_orders=pending_orders,
                           recent_orders=recent_orders)


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
@bp.route('/orders/<int:order_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_order(order_id):
    order = CustomerOrder.query.get_or_404(order_id)

    if order.status not in ['pending', 'awaiting_approval']:
        flash("This order cannot be approved.", "warning")
        return redirect(url_for('auth.view_orders', order_id=order.id))

    # Step 1: Conflict check - ensure no device is already sold
    sold_devices = [
        item.device for item in order.items
        if item.device and item.device.status == 'sold'
    ]

    if sold_devices:
        sold_names = [f"{d.brand} {d.model}" for d in sold_devices]
        sold_names_str = ', '.join(sold_names)

        # Mark order as rejected
        order.status = 'rejected'
        order.notes = f"The following device(s) are no longer available: {sold_names_str}"
        order.approved_by_id = current_user.id
        order.approved_at = datetime.utcnow()

        notif_link_staff = url_for('auth.view_order_staff', order_id=order.id)
        notif_link_customer = url_for('customers.order_detail', order_id=order.id)

        # Notify assigned staff
        if order.assigned_staff_id:
            Notification.query.filter_by(user_id=order.assigned_staff_id, link=notif_link_staff).delete()
            db.session.add(Notification(
                user_id=order.assigned_staff_id,
                message=f"Order #{order.id} was rejected. Sold device(s): {sold_names_str}",
                recipient_type='staff',
                link=notif_link_staff
            ))

        # Notify the customer about rejection
        if order.customer:
            db.session.add(Notification(
                user_id=order.customer.id,
                message=f"Your order #{order.id} was rejected. Device(s) unavailable: {sold_names_str}",
                recipient_type='customer',
                link=notif_link_customer
            ))

        db.session.commit()
        flash(f"Order #{order.id} rejected. Device(s) already sold: {sold_names_str}", "danger")
        return redirect(url_for('auth.view_order', order_id=order.id))

    # Step 2: Approve the order
    order.status = 'approved'
    order.approved_by_id = current_user.id
    order.approved_at = datetime.utcnow()

    for item in order.items:
        if item.device:
            item.device.status = 'sold'

    # Step 3: Notify assigned staff
    notif_link_staff = url_for('auth.view_order_staff', order_id=order.id)
    if order.assigned_staff_id:
        Notification.query.filter_by(user_id=order.assigned_staff_id, link=notif_link_staff).delete()
        db.session.add(Notification(
            user_id=order.assigned_staff_id,
            message=f"Order #{order.id} has been approved and marked as sold.",
            recipient_type='staff',
            link=notif_link_staff
        ))

    # ✅ Step 4: Notify the customer about approval
    notif_link_customer = url_for('customers.order_detail', order_id=order.id)
    if order.customer:
        db.session.add(Notification(
            user_id=order.customer.id,
            message=f"Your order #{order.id} has been approved! You will be contacted shortly.",
            recipient_type='customer',
            link=notif_link_customer
        ))

    db.session.commit()
    flash(f"Order #{order.id} approved. Devices marked as sold.", "success")
    return redirect(url_for('auth.view_orders', order_id=order.id))



# CUSTOMER ORDERS 
@bp.route('/admin/orders')
@login_required
@admin_required
def view_orders():
    orders = CustomerOrder.query.filter_by(is_deleted=False).order_by(CustomerOrder.created_at.desc()).all()

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

    if order.status not in ['pending', 'awaiting_approval']:
        flash("Only pending or awaiting approval orders can be cancelled.", "warning")
        return redirect(url_for('auth.view_order', order_id=order.id))

    reason = request.form.get('cancel_reason', '').strip()
    if not reason:
        flash("Cancellation reason is required.", "danger")
        return redirect(url_for('auth.view_order', order_id=order.id))

    order.status = 'cancelled'
    order.approved_by_id = current_user.id
    order.approved_at = datetime.utcnow()
    order.notes = f"Cancelled by admin: {reason}"

    # Notify staff if assigned
    if order.assigned_staff_id:
        notif_link_staff = url_for('auth.view_order_staff', order_id=order.id)
        Notification.query.filter_by(user_id=order.assigned_staff_id, link=notif_link_staff).delete()
        db.session.add(Notification(
            user_id=order.assigned_staff_id,
            message=f"Order #{order.id} was cancelled by admin. Reason: {reason}",
            recipient_type='staff',
            link=notif_link_staff
        ))

    # Notify customer
    if order.customer:
        notif_link_customer = url_for('customers.order_detail', order_id=order.id)
        db.session.add(Notification(
            user_id=order.customer.id,
            message=f"Your order #{order.id} was cancelled. Reason: {reason}",
            recipient_type='customer',
            link=notif_link_customer
        ))

    db.session.commit()
    flash("Order has been cancelled and notifications sent.", "success")
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

    order.is_deleted = True
    db.session.commit()
    flash("Cancelled order deleted successfully.", "success")
    return redirect(url_for('auth.view_orders'))

# PENDING ORDERS
@bp.route('/orders/pending')
@login_required
@admin_required
def pending_orders():
    orders = CustomerOrder.query.filter_by(status='pending', is_deleted=False).order_by(CustomerOrder.created_at.desc()).all()

    return render_template('admin/orders_pending.html', orders=orders)

# ORDERS AWAITING APPROVAL
@bp.route('/orders/awaiting_approval')
@login_required
@admin_required
def awaiting_approval_orders():
    orders = CustomerOrder.query.filter_by(status='awaiting_approval', is_deleted=False).order_by(CustomerOrder.created_at.desc()).all()
    return render_template('admin/orders_awaiting_approval.html', orders=orders)


# APPROVED ORDERS
@bp.route('/orders/approved')
@login_required
@admin_required
def approved_orders():
    orders = CustomerOrder.query.filter_by(status='approved', is_deleted=False).order_by(CustomerOrder.created_at.desc()).all()

    return render_template('admin/orders_approved.html', orders=orders)


# REJECTED ORDERS
@bp.route('/orders/rejected')
@login_required
@admin_required
def rejected_orders():
    orders = CustomerOrder.query.filter_by(status='rejected', is_deleted=False).order_by(CustomerOrder.created_at.desc()).all()

    return render_template('admin/orders_rejected.html', orders=orders)

# CANCELLED ORDERS
@bp.route('/orders/cancelled')
@login_required
@admin_required
def cancelled_orders():
    orders = CustomerOrder.query.filter_by(status='cancelled', is_deleted=False).order_by(CustomerOrder.created_at.desc()).all()

    return render_template('admin/orders_cancelled.html', orders=orders)


# DELETED ORDERS
@bp.route('/orders/deleted')
@login_required
@admin_required
def deleted_orders():
    orders = CustomerOrder.query.filter_by(is_deleted=True).order_by(CustomerOrder.created_at.desc()).all()
    return render_template('admin/orders_deleted.html', orders=orders)


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
    orders = CustomerOrder.query.filter(
    CustomerOrder.assigned_staff_id != None,
    CustomerOrder.is_deleted == False
).order_by(CustomerOrder.created_at.desc()).all()

    return render_template('admin/view_assignments.html', orders=orders)

# DELETE CUSTOMER
@bp.route('/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_customer(id):
    """Delete a customer by ID"""
    customer = Customer.query.get_or_404(id)

    try:
        db.session.delete(customer)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        print(f" Delete failed for customer {id}: {e}")
        return jsonify({'error': 'Delete failed'}), 500
    
# ADMIN NOTIFICATIONS
@bp.route('/admin/notifications')
@login_required
@admin_required
def admin_notifications():
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('admin/notifications.html', notifications=notes)

# MARK ALL AS READ
@bp.route('/notifications/mark_all_read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    if current_user.role not in ['staff', 'admin']:
        abort(403)

    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({Notification.is_read: True})
    db.session.commit()
    flash("All notifications marked as read.", "info")
    
    if current_user.role == 'staff':
        return redirect(url_for('auth.notifications'))
    return redirect(url_for('auth.admin_notifications'))


# Show all sold devices
@bp.route('/devices/sold')
@login_required
@admin_required
def view_sold_devices():
    sold_devices = Device.query.filter_by(status='sold').order_by(Device.id.desc()).all()
    return render_template('admin/sold_devices.html', devices=sold_devices)


# LIST OF FAILED ORDERS
@bp.route('/admin/failed_orders')
@login_required
@admin_required
def failed_orders():
    orders = CustomerOrder.query.filter_by(status='failed').all()
    return render_template('admin/failed_orders.html', orders=orders)

# DELETE NOTIFICATIONS
@bp.route('/notifications/delete/<int:notification_id>', methods=['POST'])
@login_required
def delete_notification(notification_id):
    notif = Notification.query.get_or_404(notification_id)

    # Optional: only allow user to delete their own notifications
    if notif.user_id != current_user.id:
        abort(403)

    db.session.delete(notif)
    db.session.commit()
    flash('Notification deleted.', 'success')
    return redirect(request.referrer or url_for('auth.notifications'))  # fallback

# CLEAR NOTIFICATIONS
@bp.route('/notifications/clear', methods=['POST'])
@login_required
def clear_notifications():
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All notifications cleared.', 'info')
    return redirect(request.referrer or url_for('auth.notifications'))
