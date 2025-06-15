from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db, bcrypt
import jwt
from datetime import datetime, timedelta

bp = Blueprint('api_auth', __name__)

def generate_token(user):
    """Generate JWT token for user"""
    payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow()
    }
    return jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )

@bp.route('/login', methods=['POST'])
def login():
    """Login endpoint that returns JWT token"""
    data = request.get_json() or {}
    
    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if user is None or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 401
    
    # Update last seen
    user.last_seen = datetime.utcnow()
    db.session.commit()
    
    # Generate token
    token = generate_token(user)
    
    # Login user for session-based auth as well
    login_user(user)
    
    return jsonify({
        'token': token,
        'user': user.to_dict()
    })

@bp.route('/register', methods=['POST'])
def register():
    """Register new user account"""
    data = request.get_json() or {}
    
    # Validate required fields
    required_fields = ['username', 'email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check for existing user
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        role='staff'  # Default role is staff
    )
    user.set_password(data['password'])
    
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
    
    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    logout_user()
    return jsonify({'message': 'Successfully logged out'})

@bp.route('/token/refresh', methods=['POST'])
@login_required
def refresh_token():
    """Refresh JWT token"""
    token = generate_token(current_user)
    return jsonify({'token': token})