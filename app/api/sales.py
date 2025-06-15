from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import Sale, Device
from app import db
from datetime import datetime

bp = Blueprint('sales', __name__)

@bp.route('/sales', methods=['GET'])
@login_required
def get_sales():
    """Get list of sales with optional filters"""
    # For staff, only show their own sales
    if not current_user.is_admin():
        sales = Sale.query.filter_by(seller_id=current_user.id).all()
        return jsonify([sale.to_dict() for sale in sales])
    
    # For admin, show all sales with optional filters
    payment_type = request.args.get('payment_type')
    seller_id = request.args.get('seller_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Sale.query
    
    if payment_type:
        query = query.filter_by(payment_type=payment_type)
    if seller_id:
        query = query.filter_by(seller_id=seller_id)
    if date_from:
        query = query.filter(Sale.sale_date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Sale.sale_date <= datetime.fromisoformat(date_to))
    
    sales = query.all()
    return jsonify([sale.to_dict() for sale in sales])

@bp.route('/sales/<int:id>', methods=['GET'])
@login_required
def get_sale(id):
    """Get sale details"""
    sale = Sale.query.get_or_404(id)
    
    # Staff can only view their own sales
    if not current_user.is_admin() and sale.seller_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(sale.to_dict())

@bp.route('/sales', methods=['POST'])
@login_required
def create_sale():
    """Create new sale"""
    data = request.get_json() or {}
    
    # Validate required fields
    required_fields = ['device_imei', 'sale_price', 'payment_type', 'amount_paid']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get device by IMEI
    device = Device.query.filter_by(imei=data['device_imei']).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Check if device is available
    if not device.is_available:
        return jsonify({'error': 'Device is not available for sale'}), 400
    
    # Validate payment
    if float(data['amount_paid']) > float(data['sale_price']):
        return jsonify({'error': 'Amount paid cannot exceed sale price'}), 400
    
    # Create sale
    sale = Sale(
        device_id=device.id,
        seller_id=current_user.id,
        sale_price=data['sale_price'],
        payment_type=data['payment_type'],
        amount_paid=data['amount_paid'],
        notes=data.get('notes', '')
    )
    
    # Mark device as sold
    device.mark_as_sold()
    
    try:
        db.session.add(sale)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
    
    return jsonify(sale.to_dict()), 201

@bp.route('/sales/<int:id>/payment', methods=['POST'])
@login_required
def add_payment(id):
    """Add payment to existing sale"""
    sale = Sale.query.get_or_404(id)
    
    # Staff can only add payments to their own sales
    if not current_user.is_admin() and sale.seller_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json() or {}
    
    if 'amount' not in data:
        return jsonify({'error': 'Missing payment amount'}), 400
    
    amount = float(data['amount'])
    
    # Validate payment amount
    if amount <= 0:
        return jsonify({'error': 'Invalid payment amount'}), 400
    if amount > sale.balance_due:
        return jsonify({'error': 'Payment amount exceeds balance due'}), 400
    
    # Update amount paid
    sale.amount_paid = float(sale.amount_paid) + amount
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
    
    return jsonify(sale.to_dict())