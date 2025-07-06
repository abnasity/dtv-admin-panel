# app/utils/image_utils.py
import os
import re
import logging
from pathlib import Path
from werkzeug.utils import secure_filename

try:
    from PIL import Image, UnidentifiedImageError
    from io import BytesIO
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    from warnings import warn
    warn("Pillow not installed - image processing disabled")

def standardize_filename(manufacturer, model):
    """
    Convert device info to standardized filename format:
    manufacturer-model.jpg (all lowercase, hyphens)
    """
    def clean_string(s):
        return re.sub(r'[^a-zA-Z0-9]', '-', str(s)).lower()
    
    return f"{clean_string(manufacturer)}-{clean_string(model)}.jpg"

class DeviceImageManager:
    def __init__(self, app=None):
        self.app = app
        self.image_cache = {}
        self.thumbnail_sizes = [(200, 200), (500, 500)]  # Width, height
        self.logger = logging.getLogger(__name__)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.base_path = Path(app.static_folder) / 'images' / 'devices'
        self.allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
        self._build_image_cache()
        app.extensions['image_manager'] = self
    
    def _build_image_cache(self):
        """Build cache of device images with error handling"""
        self.image_cache = {}
        try:
            if not self.base_path.exists():
                self.base_path.mkdir(parents=True, exist_ok=True)
                return
                
            for manufacturer_dir in self.base_path.iterdir():
                if manufacturer_dir.is_dir():
                    manufacturer = manufacturer_dir.name.lower()
                    self.image_cache[manufacturer] = {}
                    
                    for image_file in manufacturer_dir.glob('*.*'):
                        if image_file.suffix.lower()[1:] not in self.allowed_extensions:
                            continue
                        
                        try:
                            model = image_file.stem.lower()
                            self.image_cache[manufacturer][model] = image_file.name
                        except Exception as e:
                            self.logger.error(f"Error processing {image_file}: {str(e)}")
                            continue
        except Exception as e:
            self.logger.critical(f"Failed to build image cache: {str(e)}")
            raise

    def _optimize_image(self, file_stream):
        """Optimize image if Pillow is available"""
        if not PILLOW_AVAILABLE:
            return file_stream
        
        try:
            img = Image.open(file_stream)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            return buffer
        except UnidentifiedImageError:
            self.logger.error("Invalid image file uploaded")
            file_stream.seek(0)
            return file_stream
        except Exception as e:
            self.logger.error(f"Image optimization failed: {str(e)}")
            file_stream.seek(0)
            return file_stream

    def find_matching_image(self, manufacturer, model):
        """Find matching image for device"""
        manufacturer = manufacturer.lower()
        model = model.lower()
        
        try:
            # Exact match
            return self.image_cache[manufacturer][model], True
        except KeyError:
            # Partial model match
            for model_key, filename in self.image_cache.get(manufacturer, {}).items():
                if model in model_key or model_key in model:
                    return filename, False
        return None, False
    
    def allowed_file(self, filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_device_image(self, manufacturer, model, file):
        """Save uploaded device image with standardized naming and optimization"""
        if not self.allowed_file(file.filename):
            raise ValueError(f"Invalid file type. Allowed: {', '.join(self.allowed_extensions)}")
        
        try:
            manufacturer_clean = re.sub(r'[^a-zA-Z0-9]', '-', manufacturer).lower()
            model_clean = re.sub(r'[^a-zA-Z0-9]', '-', model).lower()
            
            manufacturer_dir = self.base_path / manufacturer_clean
            manufacturer_dir.mkdir(exist_ok=True)
            
            filename = standardize_filename(manufacturer, model)
            filepath = manufacturer_dir / filename
            
            # Optimize if Pillow available
            file_stream = self._optimize_image(file.stream)
            
            # Save the file
            with open(filepath, 'wb') as f:
                if hasattr(file_stream, 'read'):
                    f.write(file_stream.read())
                else:
                    file.save(filepath)
            
            # Generate thumbnails
            if PILLOW_AVAILABLE:
                self.generate_thumbnails(filepath)
            
            # Update cache
            self._add_to_cache(manufacturer_clean, model_clean, filename)
            
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save image: {str(e)}")
            raise ValueError(f"Could not save image: {str(e)}")
    
    def generate_thumbnails(self, image_path):
        """Generate thumbnails with error handling"""
        if not PILLOW_AVAILABLE:
            return False
            
        try:
            img = Image.open(image_path)
            for width, height in self.thumbnail_sizes:
                thumb = img.copy()
                thumb.thumbnail((width, height))
                thumb_path = image_path.parent / f"{image_path.stem}_{width}x{height}{image_path.suffix}"
                thumb.save(thumb_path, "JPEG", quality=85)
            return True
        except UnidentifiedImageError:
            self.logger.error(f"Invalid image file: {image_path}")
            return False
        except Exception as e:
            self.logger.error(f"Thumbnail generation failed for {image_path}: {str(e)}")
            return False
    
    def _add_to_cache(self, manufacturer, model, filename):
        """Thread-safe cache update"""
        if manufacturer not in self.image_cache:
            self.image_cache[manufacturer] = {}
        self.image_cache[manufacturer][model] = filename

# Singleton pattern with error handling
try:
    image_manager = DeviceImageManager()
except Exception as e:
    logging.critical(f"Failed to initialize image manager: {str(e)}")
    raise

def init_app(app):
    """Initialize the image manager with Flask app"""
    try:
        image_manager.init_app(app)
    except Exception as e:
        app.logger.critical(f"Image manager init failed: {str(e)}")
        raise