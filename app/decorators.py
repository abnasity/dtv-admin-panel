from functools import wraps
from flask import jsonify, current_app, request, g
from flask_login import current_user
import jwt

def admin_required(f):
    """Decorator for views that require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def verify_jwt_token(token):
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
        return None

def token_required(f):
    """Decorator for views that require valid JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'Missing authorization header',
                'message': 'Please provide a valid JWT token'
            }), 401
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                'error': 'Invalid authorization format',
                'message': 'Token must be Bearer token'
            }), 401
            
        token = parts[1]
        user_id = verify_jwt_token(token)
        
        if user_id is None:
            return jsonify({
                'error': 'Invalid or expired token',
                'message': 'Please provide a valid token or login again'
            }), 401
            
        # Store user_id in g object for route access
        g.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function
