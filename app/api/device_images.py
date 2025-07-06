# app/api/device_images.py
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest, UnsupportedMediaType
from werkzeug.utils import secure_filename
from app.utils.image_utils import image_manager
from app.models import Device
from app import db
import logging

bp = Blueprint('device_images', __name__, url_prefix='/api/device-images')
logger = logging.getLogger(__name__)

@bp.route('', methods=['GET'])
def get_device_image():
    """
    Get device image URL
    ---
    tags:
      - Device Images
    parameters:
      - name: manufacturer
        in: query
        type: string
        required: true
        example: apple
      - name: model
        in: query
        type: string
        required: true
        example: iphone-13
      - name: color
        in: query
        type: string
        required: false
        example: blue
    responses:
      200:
        description: Device image data
        schema:
          type: object
          properties:
            image_url:
              type: string
            is_exact_match:
              type: boolean
      400:
        description: Missing required parameters
      404:
        description: Image not found
    """
    try:
        manufacturer = request.args.get('manufacturer', '').strip()
        model = request.args.get('model', '').strip()
        color = request.args.get('color', '').strip() or None
        
        if not manufacturer or not model:
            logger.warning("Missing manufacturer or model parameters")
            raise BadRequest("Manufacturer and model parameters are required")
        
        image_filename, is_exact_match = image_manager.find_matching_image(
            manufacturer, model, color
        )
        
        if not image_filename:
            logger.info(f"No image found for {manufacturer} {model} (color: {color})")
            return jsonify({"error": "Image not found"}), 404
        
        manufacturer_dir = next(
            (d.name for d in image_manager.base_path.iterdir() 
             if d.is_dir() and d.name.lower() == manufacturer.lower()),
            manufacturer.lower()
        )
        
        return jsonify({
            "image_url": f"/static/images/devices/{manufacturer_dir}/{image_filename}",
            "is_exact_match": is_exact_match,
            "thumbnail_url": f"/static/images/devices/{manufacturer_dir}/{image_filename.rsplit('.', 1)[0]}_200x200.jpg"
        })
        
    except Exception as e:
        logger.error(f"Error in get_device_image: {str(e)}")
        raise

@bp.route('', methods=['POST'])
def upload_device_image():
    """
    Upload device image
    ---
    tags:
      - Device Images
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: The image file to upload
      - name: manufacturer
        in: formData
        type: string
        required: true
        example: apple
      - name: model
        in: formData
        type: string
        required: true
        example: iphone-13
      - name: color
        in: formData
        type: string
        required: false
        example: blue
      - name: device_id
        in: formData
        type: integer
        required: false
        description: Link image to specific device
    responses:
      201:
        description: Image uploaded successfully
      400:
        description: Invalid request
      415:
        description: Unsupported media type
    """
    try:
        # Validate file presence
        if 'file' not in request.files:
            logger.warning("No file part in upload request")
            raise BadRequest("No file part in request")
        
        file = request.files['file']
        if file.filename == '':
            logger.warning("Empty filename in upload request")
            raise BadRequest("No selected file")
        
        # Validate content type
        if not file.content_type.startswith('image/'):
            logger.warning(f"Invalid content type: {file.content_type}")
            raise UnsupportedMediaType("Only image files are allowed")
        
        # Get and validate parameters
        manufacturer = request.form.get('manufacturer', '').strip()
        model = request.form.get('model', '').strip()
        color = request.form.get('color', '').strip() or None
        device_id = request.form.get('device_id')
        
        if not manufacturer or not model:
            logger.warning("Missing manufacturer or model in upload request")
            raise BadRequest("Manufacturer and model are required")
        
        # Secure the filename and save image
        filename = image_manager.save_device_image(
            manufacturer, 
            model, 
            color, 
            file
        )
        
        # Optionally link to device
        if device_id:
            try:
                device = Device.query.get_or_404(device_id)
                if not device.main_image:
                    device.main_image = filename
                    db.session.commit()
                    logger.info(f"Set image {filename} as main for device {device_id}")
            except Exception as e:
                logger.error(f"Error linking image to device {device_id}: {str(e)}")
                # Continue even if device link fails
        
        logger.info(f"Successfully uploaded image: {filename}")
        return jsonify({
            "message": "Image uploaded successfully",
            "filename": filename,
            "image_url": f"/static/images/devices/{manufacturer.lower()}/{filename}"
        }), 201
        
    except ValueError as e:
        logger.error(f"Value error in upload: {str(e)}")
        raise BadRequest(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in upload: {str(e)}")
        raise

@bp.route('/<int:device_id>', methods=['GET'])
def get_device_images(device_id):
    """
    Get all images for a specific device
    ---
    tags:
      - Device Images
    parameters:
      - name: device_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Device images data
      404:
        description: Device not found
    """
    device = Device.query.get_or_404(device_id)
    variants = image_manager.get_all_device_images(device.brand, device.model)
    
    return jsonify({
        "main_image": device.image_url,
        "thumbnail": device.thumbnail_url,
        "variants": variants,
        "color_options": list(variants.keys())
    })