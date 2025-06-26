from flask import Blueprint, request, jsonify, current_app
from app.models import Customer
from app import db
import logging

bp = Blueprint('api_customers', __name__, url_prefix='/api/customers')


# GET /api/customers
@bp.route('/', methods=['GET'])
def get_customers():
    """Return list of all customers"""
    customers = Customer.query.all()
    return jsonify([c.to_dict() for c in customers])


# GET /api/customers/<int:id>
@bp.route('/<int:id>', methods=['GET'])
def get_customer(id):
    """Return customer by ID"""
    customer = Customer.query.get_or_404(id)
    return jsonify(customer.to_dict())


# POST /api/customers
@bp.route('/', methods=['POST'])
def create_customer():
    """Create new customer"""
    data = request.get_json() or {}

    # Validate required fields
    required = ['email', 'full_name', 'password']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check email uniqueness
    if Customer.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400

    customer = Customer(
        email=data['email'],
        full_name=data['full_name'],
        phone_number=data.get('phone_number'),
        role='customer'
    )
    customer.set_password(data['password'])

    try:
        db.session.add(customer)
        db.session.commit()
        return jsonify(customer.to_dict()), 201
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500

# PARTIALLY UPDATE CUSTOMER
@bp.route('/<int:customer_id>', methods=['PATCH'])
def update_customer_partial(customer_id):
    """Partially update a customer (PATCH method)"""
    customer = Customer.query.get_or_404(customer_id)
    data = request.get_json() or {}

    # Update allowed fields if present in request data
    updatable_fields = ['email', 'full_name', 'phone_number', 'is_active', 'role']

    for field in updatable_fields:
        if field in data:
            setattr(customer, field, data[field])

    if 'password' in data:
        customer.set_password(data['password'])

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

    return jsonify(customer.to_dict())




# UPDATE CUSTOMER
@bp.route('/<int:id>', methods=['PUT'])
def update_customer(id):
    """Update an existing customer"""
    customer = Customer.query.get_or_404(id)
    data = request.get_json() or {}

    if 'email' in data and data['email'] != customer.email:
        if Customer.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        customer.email = data['email']

    for field in ['full_name', 'phone_number', 'role', 'is_active']:
        if field in data:
            setattr(customer, field, data[field])

    if 'password' in data:
        customer.set_password(data['password'])

    try:
        db.session.commit()
        return jsonify(customer.to_dict())
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Update failed'}), 500


# DELETE /api/customers/<int:id>
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
        current_app.logger.error(f"Delete failed for customer {id}: {e}")
        print(f"❌ Delete failed for customer {id}: {e}")
        return jsonify({'error': 'Delete failed'}), 500