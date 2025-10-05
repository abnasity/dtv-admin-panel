from flask import render_template, redirect, url_for, flash, request, jsonify, abort, after_this_request
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf.csrf import validate_csrf, ValidationError
from app.extensions import db
from app.models import User, Notification, Device
from app.forms import LoginForm, ProfileForm, RegisterForm, ResetPasswordForm, RequestResetForm, EditUserForm
from app.decorators  import admin_required
from app.utils.decorators import staff_required
from app.utils.mixins import ResetTokenMixin 
from app.routes.auth import bp
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from flask_mail import Message
from app.extensions import mail
from sqlalchemy.exc import SQLAlchemyError
import traceback



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



@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        try:
            identifier = form.identifier.data
            user = User.query.filter(
                or_(User.email == identifier, User.username == identifier)
            ).first()

            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)

                # Role-based redirection logic
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                elif user.role == 'admin':
                    return redirect(url_for('auth.dashboard'))
                elif user.role == 'staff':
                    try:
                        return redirect(url_for('staff.dashboard'))
                    except Exception:
                        # fallback if staff dashboard route doesn't exist
                        return redirect(url_for('auth.dashboard'))
                else:
                    # fallback if role doesn't match known types
                    return redirect(url_for('auth.dashboard'))

            else:
                flash('Invalid username/email or password', 'danger')

        except SQLAlchemyError as e:
            print("SQLAlchemy error:", e)
            traceback.print_exc()
            flash('A server error occurred. Please try again later.', 'danger')
            return render_template('auth/login.html', form=form), 500

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
@bp.route('/dashboard')
@login_required
def dashboard():
    print(f"Current user: {current_user}, authenticated: {current_user.is_authenticated}")
    total_users = User.query.count()
    total_devices = Device.query.filter(
    Device.status == 'available'
).count()

  
    return render_template('auth/dashboard.html',
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
@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    form = RegisterForm()

    if form.validate_on_submit():
        # Check duplicate email
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('A user with this email already exists.', 'warning')
            return redirect(url_for('auth.users'))

        # Only require and use address for staff
        address = None
        if form.role.data == 'staff':
            address = form.address.data
            if address == '__new__':
                address = form.new_address.data

        # Only set username and address for staff
        user = User(
            username=form.username.data if form.role.data == 'staff' else None,
            email=form.email.data,
            role=form.role.data,
            address=address if form.role.data == 'staff' else None
        )
        user.set_password(form.password.data)

        db.session.add(user)
        try:
            db.session.commit()
            flash(f'User {user.username or user.email} has been created successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
            print(f"[ERROR] User creation failed: {e}")

        return redirect(url_for('auth.users'))

    # Render form
    addresses = ["Address1", "Address2"]  # optional — only relevant for staff
    return render_template('auth/create_user.html', form=form, addresses=addresses)



# TOGGLE USER STATUS
@bp.route('/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)


    if user.id == current_user.id:
        flash("You cannot deactivate yourself.", "warning")
        return redirect(url_for("auth.users", status="active"))

    user.is_active = not user.is_active
    try:
        db.session.commit()
        flash(f'User {user.username} has been {"activated" if user.is_active else "deactivated"}', "success")
        return redirect(url_for("auth.users", status="inactive" if not user.is_active else "active"))
    except Exception as e:
        db.session.rollback()
        flash("Database error occurred", "danger")
        return redirect(url_for("auth.users", status="active"))


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
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    form = EditUserForm(
        original_username=user.username,
        original_email=user.email,
        obj=user
    )

    if form.validate_on_submit():
        form.populate_obj(user)

        selected_address = request.form.get("address_select")
        if selected_address == "__new__":
            new_address = request.form.get("new_address")
            if new_address:
                user.address = new_address
        else:
            user.address = selected_address

        db.session.commit()
        flash("User updated successfully", "success")
        return redirect(url_for('auth.users'))

    return render_template(
        'auth/edit_user.html',
        form=form,
        user=user,
        addresses=["Address1", "Address2"]
    )


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
    return render_template('admin/view_assignments.html')


    
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
