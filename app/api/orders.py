from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import CustomerOrder, CustomerOrderItem, Device, Customer
from datetime import datetime

bp = Blueprint('orders', __name__, url_prefix='/api/orders')

# GET all orders
@bp.route('/', methods=['GET'])
def get_orders():
    orders = CustomerOrder.query.all()
    return jsonify([order.to_dict() for order in orders]), 200

# GET a single order by ID
@bp.route('/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = CustomerOrder.query.get_or_404(order_id)
    return jsonify(order.to_dict()), 200

# CREATE a new order
@bp.route('/', methods=['POST'])
def create_order():
    data = request.get_json()
    customer_id = data.get('customer_id')
    delivery_address = data.get('delivery_address')
    notes = data.get('notes', '')
    items_data = data.get('items', [])  # list of dicts: [{'device_id': x, 'unit_price': y}, ...]

    if not customer_id or not items_data:
        return jsonify({'error': 'customer_id and items are required'}), 400

    try:
        order = CustomerOrder(
            customer_id=customer_id,
            delivery_address=delivery_address,
            notes=notes
        )
        for item in items_data:
            device_id = item['device_id']
            unit_price = item['unit_price']
            order_item = CustomerOrderItem(
                device_id=device_id,
                unit_price=unit_price
            )
            order.items.append(order_item)

        db.session.add(order)
        db.session.commit()
        return jsonify(order.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# PATCH an order (e.g. status, delivery_address)
@bp.route('/<int:order_id>', methods=['PATCH'])
def patch_order(order_id):
    order = CustomerOrder.query.get_or_404(order_id)
    data = request.get_json()

    try:
        if 'status' in data:
            order.status = data['status']
            if data['status'] == 'approved':
                order.approved_by_id = data.get('approved_by_id')
                order.approved_at = datetime.utcnow()
        if 'delivery_address' in data:
            order.delivery_address = data['delivery_address']
        if 'notes' in data:
            order.notes = data['notes']

        db.session.commit()
        return jsonify(order.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# PUT to fully update order (not commonly used)
@bp.route('/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    order = CustomerOrder.query.get_or_404(order_id)
    data = request.get_json()

    try:
        order.customer_id = data['customer_id']
        order.delivery_address = data['delivery_address']
        order.notes = data.get('notes', '')
        order.status = data.get('status', 'pending')

        # Clear and replace items
        order.items.clear()
        for item in data.get('items', []):
            order_item = CustomerOrderItem(
                device_id=item['device_id'],
                unit_price=item['unit_price']
            )
            order.items.append(order_item)

        db.session.commit()
        return jsonify(order.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# DELETE an order
@bp.route('/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    order = CustomerOrder.query.get_or_404(order_id)
    try:
        db.session.delete(order)
        db.session.commit()
        return jsonify({'message': f'Order {order.id} deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
