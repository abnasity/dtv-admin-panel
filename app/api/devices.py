from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import Device
from app import db
from app.decorators import admin_required
from datetime import datetime

bp = Blueprint('devices', __name__)

@bp.route('/devices', methods=['GET'])
@login_required
def get_devices():
    """Get list of all devices with optional filters"""
    # Get query parameters
    status = request.args.get('status')
    brand = request.args.get('brand')
    
    # Start with base query
    query = Device.query
    
    # Apply filters
    if status:
        query = query.filter_by(status=status)
    if brand:
        query = query.filter_by(brand=brand)
    
    # Execute query and return results
    devices = query.all()
    return jsonify([device.to_dict() for device in devices])

@bp.route('/devices/<imei>', methods=['GET'])
@login_required
def get_device(imei):
    """Get device details by IMEI"""
    device = Device.query.filter_by(imei=imei).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    return jsonify(device.to_dict())

@bp.route('/devices', methods=['POST'])
@login_required
@admin_required
def create_device():
    """Add new device to inventory"""
    data = request.get_json() or {}
    
    # Validate required fields
    required_fields = ['imei', 'brand', 'model', 'purchase_price']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check for existing IMEI
    if Device.query.filter_by(imei=data['imei']).first():
        return jsonify({'error': 'Device with this IMEI already exists'}), 400
    
    # Create new device
    device = Device(
        imei=data['imei'],
        brand=data['brand'],
        model=data['model'],
        purchase_price=data['purchase_price'],
        notes=data.get('notes', '')
    )
    
    try:
        db.session.add(device)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
    
    return jsonify(device.to_dict()), 201

@bp.route('/devices/<imei>', methods=['PUT'])
@login_required
@admin_required
def update_device(imei):
    """Update device details"""
    device = Device.query.filter_by(imei=imei).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    data = request.get_json() or {}
    
    # Update allowed fields
    for field in ['brand', 'model', 'purchase_price', 'notes']:
        if field in data:
            setattr(device, field, data[field])
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
    
    return jsonify(device.to_dict())

@bp.route('/devices/<imei>', methods=['DELETE'])
@login_required
@admin_required
def delete_device(imei):
    """Delete device from inventory"""
    device = Device.query.filter_by(imei=imei).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Check if device can be deleted
    if device.sale:
        return jsonify({'error': 'Cannot delete device with associated sale'}), 400
    
    try:
        db.session.delete(device)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500
    
    return '', 204