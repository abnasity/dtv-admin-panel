from flask import Blueprint, request, jsonify
from app.models import User
from app import db
from app.decorators import admin_required
from werkzeug.security import generate_password_hash

bp = Blueprint('api_users', __name__, url_prefix='/api/users')

# GET USERS
@bp.route('/', methods=['GET'])
def get_users():
    """Get all users with optional filters"""
    role = request.args.get('role')
    is_active = request.args.get('is_active')

    query = User.query

    if role:
        query = query.filter_by(role=role)
    if is_active is not None:
        query = query.filter_by(is_active=(is_active.lower() == 'true'))

    users = query.all()
    return jsonify([user.to_dict() for user in users])

# GET A USER BY ID
@bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID"""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

# CREATE A USER
@bp.route('/', methods=['POST'])
def create_user():
    """Create a new user"""
    data = request.get_json() or {}
    required_fields = ['username', 'email', 'password', 'role']

    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    user = User(
        username=data['username'],
        email=data['email'],
        role=data['role'],
        is_active=True
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201

# PARTIALLY UPDATE A USER
@bp.route('/<int:user_id>', methods=['PATCH'])
def patch_user(user_id):
    """Partially update a user's fields"""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    # Handle fields one by one
    if 'username' in data:
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = data['username']

    if 'email' in data:
        existing_email = User.query.filter_by(email=data['email']).first()
        if existing_email and existing_email.id != user.id:
            return jsonify({'error': 'Email already registered'}), 400
        user.email = data['email']

    if 'role' in data:
        user.role = data['role']

    if 'is_active' in data:
        user.is_active = data['is_active']

    if 'password' in data:
        user.set_password(data['password'])

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

    return jsonify(user.to_dict())

# UPDATE A USER
@bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update an existing user with uniqueness checks"""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    # Check if username is changing and already exists for another user
    if 'username' in data and data['username'] != user.username:
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = data['username']

    # Check if email is changing and already exists for another user
    if 'email' in data and data['email'] != user.email:
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Email already registered'}), 400
        user.email = data['email']

    # Update other fields
    if 'role' in data:
        user.role = data['role']

    if 'is_active' in data:
        user.is_active = data['is_active']

    if 'password' in data:
        user.set_password(data['password'])

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

    return jsonify(user.to_dict())


# DELETE A USER
@bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)

    try:
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500

    return '', 204
