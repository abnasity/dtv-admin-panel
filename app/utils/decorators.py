from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from flask import abort, current_app


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if not current_user.is_admin():
            abort(403)
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
