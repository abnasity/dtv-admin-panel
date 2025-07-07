from flask import Blueprint, request, jsonify
from app.utils.image_utils import image_manager
from flask_login import login_required, current_user
from app.models import Device
from app import db
from app.decorators import admin_required



bp = Blueprint('devices', __name__)

@bp.route('/', methods=['GET'])
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


@bp.route('/<imei>', methods=['GET'])
def get_device(imei):
    """Get device details by IMEI"""
    device = Device.query.filter_by(imei=imei).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    return jsonify(device.to_dict())


@bp.route('/', methods=['POST'])
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
        ram=data['ram'],
        rom=data['rom'],
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

# PARTIALLY UPDATE A DEVICE
@bp.route('/<imei>', methods=['PATCH'])
def patch_device(imei):
    """Partially update a device by IMEI"""
    device = Device.query.filter_by(imei=imei).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404

    data = request.get_json() or {}

    # Update only allowed fields if provided
    allowed_fields = ['brand', 'model', 'ram', 'rom', 'purchase_price', 'notes']
    for field in allowed_fields:
        if field in data:
            setattr(device, field, data[field])

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

    return jsonify(device.to_dict())



@bp.route('/<imei>', methods=['PUT'])
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

@bp.route('/<imei>', methods=['DELETE'])
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


# app/api/devices.py
@bp.route('/<int:device_id>/images', methods=['GET'])
def get_device_images(device_id):
    device = Device.query.get_or_404(device_id)
    return jsonify({
        'primary': device.image_url,
        'thumbnail': device.thumbnail_url,
        'variants': device.get_image_variants()
    })

@bp.route('/<int:device_id>/images', methods=['POST'])
def upload_device_image(device_id):
    device = Device.query.get_or_404(device_id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        filename = image_manager.save_device_image(
            device.brand,
            device.model,
            device.color,
            file
        )
        return jsonify({
            'message': 'Image uploaded successfully',
            'image_url': f"/static/images/devices/{device.brand.lower()}/{filename}"
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400