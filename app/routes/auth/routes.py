from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models import User
from app.forms import LoginForm, ProfileForm, RegisterForm
from app.decorators  import admin_required
from app.routes.auth import bp

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


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

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
                         form=form)
    
    
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

@bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    form = RegisterForm()
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
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
            'role': user.role
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