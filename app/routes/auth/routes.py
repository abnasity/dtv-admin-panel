from flask import render_template, redirect, url_for, flash, request, jsonify, abort, after_this_request
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models import User, Notification, Device
from app.forms import LoginForm, ProfileForm, RegisterForm, ResetPasswordForm, RequestResetForm
from app.decorators  import admin_required
from app.utils.decorators import staff_required
from app.utils.helpers import assign_staff_to_order
from app.utils.mixins import ResetTokenMixin 
from app.routes.auth import bp
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from flask_mail import Message
from app.extensions import mail

# RESET EMAIL
def send_reset_email(user):
    token = user.get_reset_token()
    reset_url = url_for('auth.reset_token', token=token, _external=True)
    msg = Message('Password Reset Request',
                  recipients=[user.email])
    msg.body = f'''To reset your password, click the following link:
{reset_url}

If you did not make this request, simply ignore this email.
'''
    mail.send(msg)

# Route to request reset:
@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
        flash('If that email exists, a reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_request.html', form=form)

# Route to handle the token and reset password:
@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    user = ResetTokenMixin.verify_reset_token(token, User)

    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('auth.reset_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)  # Your own method or bcrypt
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_token.html', form=form, token=token)

# LOGIN
from sqlalchemy import or_
@bp.route('/', methods=['GET', 'POST'])
def login():         
    form = LoginForm()
    if form.validate_on_submit():
        # Accept identifier as either username or email
        identifier = form.identifier.data.strip()

        user = User.query.filter(
            or_(
                User.username.ilike(identifier),
                User.email.ilike(identifier)
            )
        ).first()
        
        if user and user.check_password(form.password.data):
            user.last_seen = db.func.now()
            db.session.commit()

            login_user(user, remember=form.remember_me.data)
            
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('auth.dashboard'))
            elif user.role == 'staff':
                return redirect(url_for('staff.dashboard'))
            elif user.role == 'customer':
                return redirect(url_for('customers.dashboard'))

            return redirect(url_for('auth.login'))  # Fallback
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
    return redirect(url_for('auth.login'))
 
 

# STAFF DASHBOARD
@bp.route('/notifications')
@login_required
def notifications():
    if current_user.role != 'staff':
        abort(403)
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('staff/notifications.html', notifications=notes)



# ASSIGNED ORDERS
@bp.route('/orders/assigned')
@login_required
@staff_required
def assigned_orders():

    assigned_staff_id=current_user.id


    return render_template('staff/assigned_orders.html')



# ADMIN DASHBOARD
@bp.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_devices = Device.query.filter(
    Device.status == 'available',
    Device.featured == False
).count()

  
    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_devices=total_devices,
                           )


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
    return render_template('auth/users.html',
                         users=pagination.items,
                         pagination=pagination,
                         search=search,
                         role_filter=role_filter,
                         status_filter=status_filter,
                         form=form
                         )
    


# CREATE USER
@bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    form = RegisterForm()

    if form.validate_on_submit():
        # Check for duplicate email before creating user
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('A user with this email already exists.', 'warning')
            return redirect(url_for('auth.users'))

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
            flash('Error creating user: possible duplicate or database issue', 'danger')
            print(f"[ERROR] User creation failed: {e}")
        
        return redirect(url_for('auth.users'))  

    flash('Form validation failed. Please check your inputs.', 'warning')
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

        # Notify the customer
        if order.customer and isinstance(order.customer, Customer):
            db.session.add(Notification(
                Customer_id=order.customer.id,
                message=f"Your order #{order.id} was rejected. Device(s) unavailable: {sold_names_str}",
                recipient_type='customer',
                link=notif_link_customer
            ))

        db.session.commit()
        flash(f"Order #{order.id} rejected. Device(s) already sold: {sold_names_str}", "danger")
        return redirect(url_for('auth.view_order', order_id=order.id))  # ✅ MISSING return fixed here

    # Step 1.5: Check if any device is already in another active order for a different staff
    conflicting_devices = []
    for item in order.items:
        if item.device:
            active_conflict = db.session.query(CustomerOrder).join(CustomerOrder.items).filter(
                CustomerOrder.id != order.id,
                CustomerOrder.status.in_(['pending', 'awaiting_approval', 'approved']),
                CustomerOrder.assigned_staff_id != None,
                CustomerOrder.items.any(device_id=item.device.id)
            ).first()
            if active_conflict:
                conflicting_devices.append(item.device)

    if conflicting_devices:
        conflict_names = [f"{d.brand} {d.model}" for d in conflicting_devices]
        conflict_names_str = ', '.join(conflict_names)

        order.status = 'rejected'
        order.notes = f"The following device(s) are in another sale process: {conflict_names_str}"
        order.approved_by_id = current_user.id
        order.approved_at = datetime.utcnow()

        notif_link_staff = url_for('auth.view_order_staff', order_id=order.id)
        notif_link_customer = url_for('customers.order_detail', order_id=order.id)

        # Notify assigned staff
        if order.assigned_staff_id:
            Notification.query.filter_by(user_id=order.assigned_staff_id, link=notif_link_staff).delete()
            db.session.add(Notification(
                user_id=order.assigned_staff_id,
                message=f"Order #{order.id} was rejected. Conflict: {conflict_names_str}",
                recipient_type='staff',
                link=notif_link_staff
            ))

        # Notify the customer
        if order.customer:
            db.session.add(Notification(
                customer_id=order.customer.id,
                message=f"Your order #{order.id} was rejected. Device(s) in use: {conflict_names_str}",
                recipient_type='customer',
                link=notif_link_customer
            ))

        db.session.commit()
        flash(f"Order #{order.id} rejected. Device(s) already in another sale process: {conflict_names_str}", "danger")
        return redirect(url_for('auth.view_order', order_id=order.id))

    # Step 2: Approve the order
    order.status = 'approved'
    order.approved_by_id = current_user.id
    order.approved_at = datetime.utcnow()

    for item in order.items:
        if item.device:
            item.device.status = 'available'

    # Step 3: Notify assigned staff
    notif_link_staff = url_for('auth.view_order_staff', order_id=order.id)
    if order.assigned_staff_id:
        Notification.query.filter_by(user_id=order.assigned_staff_id, link=notif_link_staff).delete()
        db.session.add(Notification(
            user_id=order.assigned_staff_id,
            message=f"Order #{order.id} has been approved and awaiting sale confirmation.",
            recipient_type='staff',
            link=notif_link_staff
        ))

    # Step 4: Notify customer
    notif_link_customer = url_for('customers.order_detail', order_id=order.id)
    if order.customer:
        db.session.add(Notification(
            customer_id=order.customer.id,
            message=f"Your order #{order.id} has been approved! You will be contacted shortly.",
            recipient_type='customer',
            link=notif_link_customer
        ))

    db.session.commit()
    flash(f"Order #{order.id} approved. Awaiting sale confirmation.", "success")
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
        flash(f"Order #{order.id} cannot be cancelled because its current status is '{order.status}'.", "warning")
        return redirect(url_for('auth.view_order', order_id=order.id))

    reason = request.form.get('cancel_reason', '').strip()
    if not reason:
        flash("Cancellation reason is required.", "danger")
        return redirect(url_for('auth.view_order', order_id=order.id))

    order.status = 'cancelled'
    order.rejection_reason = reason  # REQUIRED for display
    order.approved_by_id = current_user.id
    order.approved_at = datetime.utcnow()
    order.notes = f"{reason}"

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
            customer_id=order.customer.id,
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


# COMPLETED ORDERS
@bp.route('/orders/completed')
@login_required
@admin_required
def completed_orders():
    """Admin view: List of all completed orders"""
    orders = CustomerOrder.query.filter_by(status='completed') \
        .order_by(CustomerOrder.created_at.desc()) \
        .all()
    
    return render_template('admin/completed_orders.html', orders=orders)



# ASSIGNMENTS
@bp.route('/assignments')
@login_required
@admin_required
def view_assignments():
    return render_template('admin/view_assignments.html')

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
    notes = Notification.query.filter_by(user_id=current_user.id, recipient_type=current_user.role).order_by(Notification.created_at.desc()).all()
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
    return render_template('admin/failed_orders.html')


@bp.route('/ui')
@login_required
@admin_required
def ui():
    return render_template('UI.html')
