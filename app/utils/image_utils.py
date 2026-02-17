# app/utils/image_utils.py

import os
import re
import logging
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import current_app

try:
    from PIL import Image, UnidentifiedImageError
    from io import BytesIO
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    from warnings import warn
    warn("Pillow not installed - image processing disabled")


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_device_image(file, subdir="devices/default", filename=None):
    """
    Save uploaded device image to a flexible directory.
    Args:
        file: Uploaded file (e.g., from WTForms).
        subdir: Folder path relative to /static/images, like 'devices/samsung'.
        filename: Optional custom filename.
    Returns:
        The saved filename.
    """
    if not allowed_file(file.filename):
        raise ValueError(f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    try:
        # Sanitize subdir and filename
        subdir = re.sub(r'[^a-zA-Z0-9/_-]', '-', subdir.strip('/\\'))
        base_dir = Path(current_app.static_folder) / 'images' / subdir
        base_dir.mkdir(parents=True, exist_ok=True)

        filename = filename or secure_filename(file.filename)
        file_path = base_dir / filename

        # Optimize image stream if possible
        file_stream = _optimize_image(file.stream)

        with open(file_path, 'wb') as f:
            f.write(file_stream.read())

        # Generate thumbnails
        if PILLOW_AVAILABLE:
            generate_thumbnails(file_path)

        return filename
    except Exception as e:
        logging.error(f"Failed to save image: {str(e)}")
        raise ValueError(f"Could not save image: {str(e)}")


def _optimize_image(stream):
    """Return optimized image stream (JPEG, RGB, compressed)"""
    if not PILLOW_AVAILABLE:
        return stream

    try:
        image = Image.open(stream)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        output = BytesIO()
        image.save(output, format='JPEG', quality=85)
        output.seek(0)
        return output
    except UnidentifiedImageError:
        raise ValueError("Uploaded file is not a valid image")


def generate_thumbnails(image_path, size=(200, 200)):
    """Create a thumbnail version of the image"""
    try:
        img = Image.open(image_path)
        img.thumbnail(size)
        thumb_path = image_path.with_name(f"{image_path.stem}_200x200{image_path.suffix}")
        img.save(thumb_path)
    except Exception as e:
        logging.warning(f"Could not generate thumbnail for {image_path}: {e}")

