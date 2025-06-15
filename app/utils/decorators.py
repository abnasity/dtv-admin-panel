from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    """Decorator to restrict access to admin users"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    """Decorator to ensure user is active staff member"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_active:
            flash('Your account is inactive. Please contact an administrator.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
